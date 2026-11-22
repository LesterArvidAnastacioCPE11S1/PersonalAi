"""
Parser for Roblox place and model files so they can be used as
model context.

Supported formats:

- Binary places and models: .rbxl and .rbxm
- XML places and models: .rbxlx and .rbxmx

The binary format is documented in the rbx-dom project:

https://github.com/rojo-rbx/rbx-dom/blob/master/docs/binary.md

The output of `extract_text` is a plain text summary of the file:

- A short header with file information.
- The complete script sources (Script, LocalScript, ModuleScript),
  since those are the most useful for coding questions.
- The instance tree with the most useful properties of each instance.

Large binary blobs such as mesh data are skipped, so that the model
receives structure and code instead of unusable bytes.
"""

import re
import struct

from xml.etree import ElementTree as ElementTree


try:

    import lz4.block as LZ4_BLOCK

except ImportError:

    LZ4_BLOCK = None

try:

    import zstandard as ZSTD

except ImportError:

    ZSTD = None


MAX_SOURCE_CHARS = 100_000
MAX_PREVIEW_STRING = 160
MAX_TREE_LINES = 30_000
MAX_PROP_STRING = 240

SCRIPT_CLASSES = {
    "Script",
    "LocalScript",
    "ModuleScript"
}

# Properties that hold binary blobs and are useless as text context.
BLOB_PROPS = {
    "AttributesSerialize",
    "BinaryString",
    "CollisionGroups",
    "DataMesh",
    "MeshData",
    "PhysicalConfigData",
    "ScriptGuid",
    "SourceAssetId",
    "TerrainSmoothGrid",
    "VoxelGridAssetContentMap"
}

# Special-case CFrame rotations, from the format documentation.
# Values are (Y, X, Z) angles in degrees.
CFRAME_SPECIAL_ROTATIONS = {
    0x02: (0, 0, 0),
    0x03: (90, 0, 0),
    0x05: (0, 180, 180),
    0x06: (-90, 0, 0),
    0x07: (0, 180, 90),
    0x09: (0, 90, 90),
    0x0A: (0, 0, 90),
    0x0C: (0, -90, 90),
    0x0D: (-90, -90, 0),
    0x0E: (0, -90, 0),
    0x10: (90, -90, 0),
    0x11: (0, 90, 180),
    0x14: (0, 180, 0),
    0x15: (-90, -180, 0),
    0x17: (0, 0, 180),
    0x18: (90, 180, 0),
    0x19: (0, 0, -90),
    0x1B: (0, -90, -90),
    0x1C: (0, -180, -90),
    0x1E: (0, 90, -90),
    0x1F: (90, 90, 0),
    0x20: (0, 90, 0),
    0x22: (-90, 90, 0),
    0x23: (0, -90, 180)
}

BINARY_MAGIC = b"<roblox!"


class RobloxFileError(Exception):
    pass


# =====================================================================
# LOW LEVEL READERS
# =====================================================================


class _Reader:

    def __init__(self, data):

        self.data = data
        self.pos = 0

    def remaining(self):

        return len(self.data) - self.pos

    def read(self, count):

        if self.pos + count > len(self.data):

            raise RobloxFileError(
                "Unexpected end of file while reading chunk data."
            )

        data = self.data[self.pos : self.pos + count]
        self.pos += count

        return data

    def u8(self):

        return self.read(1)[0]

    def u16(self):

        return struct.unpack("<H", self.read(2))[0]

    def u32(self):

        return struct.unpack("<I", self.read(4))[0]

    def i32(self):

        return struct.unpack("<i", self.read(4))[0]

    def i64(self):

        return struct.unpack("<q", self.read(8))[0]

    def f32(self):

        return struct.unpack("<f", self.read(4))[0]

    def f64(self):

        return struct.unpack("<d", self.read(8))[0]

    def string(self):

        length = self.u32()

        return self.read(length)


def _untransform_i32(value):

    value &= 0xFFFFFFFF

    if value & 1:
        return -((value + 1) // 2)

    return value // 2


def _untransform_i64(value):

    value &= 0xFFFFFFFFFFFFFFFF

    if value & 1:
        return -((value + 1) // 2)

    return value // 2


def _deinterleave(data, count, width):

    """
    Undo byte interleaving: value i, byte j is stored at
    data[j * count + i].
    """

    if count * width != len(data):

        raise RobloxFileError("Interleaved array has the wrong size.")

    return [
        data[i + j * count]
        for i in range(count)
        for j in range(width)
    ]


def _read_interleaved_i32s(data, count, accumulate=False):

    bytes_list = _deinterleave(data, count, 4)

    values = []

    total = 0

    for index in range(count):

        raw = int.from_bytes(
            bytes_list[index * 4 : index * 4 + 4],
            "big"
        )

        value = _untransform_i32(raw)

        if accumulate:

            total = (total + value) & 0xFFFFFFFF
            value = total

        values.append(value)

    return values


def _read_interleaved_i64s(data, count):

    bytes_list = _deinterleave(data, count, 8)

    values = []

    for index in range(count):

        raw = int.from_bytes(
            bytes_list[index * 8 : index * 8 + 8],
            "big"
        )

        values.append(_untransform_i64(raw))

    return values


def _roblox_float_from_u32(raw):

    """
    Convert a big-endian u32 in Roblox float layout
    (eeeeeeee mmmmmmmm mmmmmmmm mmmmmmms) to a Python float.
    """

    ieee = ((raw & 1) << 31) | (raw >> 1)

    return struct.unpack(">f", ieee.to_bytes(4, "big"))[0]


def _read_interleaved_f32s(data, count):

    bytes_list = _deinterleave(data, count, 4)

    values = []

    for index in range(count):

        raw = int.from_bytes(
            bytes_list[index * 4 : index * 4 + 4],
            "big"
        )

        values.append(_roblox_float_from_u32(raw))

    return values


def _read_interleaved_u32s(data, count):

    bytes_list = _deinterleave(data, count, 4)

    return [
        int.from_bytes(
            bytes_list[index * 4 : index * 4 + 4],
            "big"
        )
        for index in range(count)
    ]


# =====================================================================
# VALUE DECODERS
# =====================================================================


def _decode_string_array(reader, count):

    return [
        reader.string()
        for _ in range(count)
    ]


def _decode_bool_array(reader, count):

    return [
        bool(reader.u8())
        for _ in range(count)
    ]


def _decode_i32_array(reader, count):

    return _read_interleaved_i32s(
        reader.read(count * 4),
        count
    )


def _decode_f32_array(reader, count):

    return _read_interleaved_f32s(
        reader.read(count * 4),
        count
    )


def _decode_f64_array(reader, count):

    return [
        reader.f64()
        for _ in range(count)
    ]


def _decode_vector3_array(reader, count):

    x = _read_interleaved_f32s(
        reader.read(count * 4),
        count
    )
    y = _read_interleaved_f32s(
        reader.read(count * 4),
        count
    )
    z = _read_interleaved_f32s(
        reader.read(count * 4),
        count
    )

    return [
        (x[i], y[i], z[i])
        for i in range(count)
    ]


def _decode_udim_array(reader, count):

    scale = _read_interleaved_f32s(
        reader.read(count * 4),
        count
    )
    offset = _read_interleaved_i32s(
        reader.read(count * 4),
        count
    )

    return [
        (scale[i], offset[i])
        for i in range(count)
    ]


def _decode_rect_array(reader, count):

    min_x = _read_interleaved_f32s(
        reader.read(count * 4),
        count
    )
    min_y = _read_interleaved_f32s(
        reader.read(count * 4),
        count
    )
    max_x = _read_interleaved_f32s(
        reader.read(count * 4),
        count
    )
    max_y = _read_interleaved_f32s(
        reader.read(count * 4),
        count
    )

    return [
        (min_x[i], min_y[i], max_x[i], max_y[i])
        for i in range(count)
    ]


def _decode_udim2_array(reader, count):

    x_scale = _read_interleaved_f32s(
        reader.read(count * 4),
        count
    )
    y_scale = _read_interleaved_f32s(
        reader.read(count * 4),
        count
    )
    x_offset = _read_interleaved_i32s(
        reader.read(count * 4),
        count
    )
    y_offset = _read_interleaved_i32s(
        reader.read(count * 4),
        count
    )

    return [
        (x_scale[i], x_offset[i], y_scale[i], y_offset[i])
        for i in range(count)
    ]


def _decode_cframe_array(reader, count):

    ids = []
    rotations = []

    for _ in range(count):

        identifier = reader.u8()

        ids.append(identifier)

        if identifier == 0:

            rotation = struct.unpack(
                "<9f",
                reader.read(36)
            )

            rotations.append(rotation)

        else:

            rotations.append(None)

    positions = _decode_vector3_array(reader, count)

    values = []

    for index in range(count):

        identifier = ids[index]
        position = positions[index]

        if identifier == 0:

            values.append((position, "matrix"))

        else:

            angles = CFRAME_SPECIAL_ROTATIONS.get(identifier)

            if angles is None:

                values.append((position, f"id {identifier:#04x}"))

            else:

                values.append(
                    (position, "rot " + ",".join(str(a) for a in angles))
                )

    return values


def _decode_referent_array(reader, count):

    return _read_interleaved_i32s(
        reader.read(count * 4),
        count,
        accumulate=True
    )


def _decode_number_sequence_array(reader, count):

    values = []

    for _ in range(count):

        keypoint_count = reader.u32()
        keypoints = []

        for _ in range(keypoint_count):

            time = reader.f32()
            value = reader.f32()
            envelope = reader.f32()

            keypoints.append((time, value, envelope))

        values.append(keypoints)

    return values


def _decode_color_sequence_array(reader, count):

    values = []

    for _ in range(count):

        keypoint_count = reader.u32()
        keypoints = []

        for _ in range(keypoint_count):

            time = reader.f32()
            red = reader.f32()
            green = reader.f32()
            blue = reader.f32()
            reader.f32()

            keypoints.append((time, red, green, blue))

        values.append(keypoints)

    return values


def _decode_physical_properties_array(reader, count):

    values = []

    for _ in range(count):

        flags = reader.u8()

        if flags & 1:

            density = reader.f32()
            friction = reader.f32()
            elasticity = reader.f32()
            friction_weight = reader.f32()
            elasticity_weight = reader.f32()

            if flags & 2:

                reader.f32()

            values.append(
                (density, friction, elasticity)
            )

        else:

            values.append(None)

    return values


def _decode_font_array(reader, count):

    values = []

    for _ in range(count):

        family = reader.string()
        reader.read(3)
        cached = reader.string()

        values.append(family)

    return values


def _decode_content_array(reader, count):

    source_types = _read_interleaved_u32s(
        reader.read(count * 4),
        count
    )

    uri_count = reader.u32()
    uris = [
        reader.string()
        for _ in range(uri_count)
    ]

    object_count = reader.u32()

    if object_count:

        _read_interleaved_i32s(
            reader.read(object_count * 4),
            object_count,
            accumulate=True
        )

    external_count = reader.u32()

    if external_count:

        _read_interleaved_i32s(
            reader.read(external_count * 4),
            external_count,
            accumulate=True
        )

    values = []
    uri_index = 0

    for source_type in source_types:

        if source_type == 1 and uri_index < len(uris):

            values.append(uris[uri_index])
            uri_index += 1

        else:

            values.append(None)

    return values


def _decode_asset_content_map_array(reader, count):

    for _ in range(count):

        flags = reader.u8()

        if flags & 1:

            reader.string()

        if flags & 2:

            entry_count = struct.unpack("<q", reader.read(8))[0]

            for _ in range(entry_count):

                reader.string()
                reader.string()

    return [None] * count


def _decode_values(reader, type_id, count):

    if type_id == 0x01:
        return _decode_string_array(reader, count)

    if type_id == 0x02:
        return _decode_bool_array(reader, count)

    if type_id == 0x03:
        return _decode_i32_array(reader, count)

    if type_id == 0x04:
        return _decode_f32_array(reader, count)

    if type_id == 0x05:
        return _decode_f64_array(reader, count)

    if type_id == 0x06:
        return _decode_udim_array(reader, count)

    if type_id == 0x07:
        return _decode_udim2_array(reader, count)

    if type_id == 0x08:
        return [
            tuple(reader.f32() for _ in range(6))
            for _ in range(count)
        ]

    if type_id in (0x09, 0x0A):
        return [
            reader.u8()
            for _ in range(count)
        ]

    if type_id == 0x0B:
        return _read_interleaved_u32s(
            reader.read(count * 4),
            count
        )

    if type_id == 0x0C:
        return _decode_vector3_array(reader, count)

    if type_id == 0x0D:
        x = _decode_f32_array(reader, count)
        y = _decode_f32_array(reader, count)
        return [
            (x[i], y[i])
            for i in range(count)
        ]

    if type_id == 0x0E:
        return _decode_vector3_array(reader, count)

    if type_id == 0x10:
        return _decode_cframe_array(reader, count)

    if type_id == 0x12:
        return _read_interleaved_u32s(
            reader.read(count * 4),
            count
        )

    if type_id == 0x13:
        return _decode_referent_array(reader, count)

    if type_id == 0x14:
        return [
            struct.unpack("<3h", reader.read(6))
            for _ in range(count)
        ]

    if type_id == 0x15:
        return _decode_number_sequence_array(reader, count)

    if type_id == 0x16:
        return _decode_color_sequence_array(reader, count)

    if type_id == 0x17:
        return [
            (reader.f32(), reader.f32())
            for _ in range(count)
        ]

    if type_id == 0x18:
        return _decode_rect_array(reader, count)

    if type_id == 0x19:
        return _decode_physical_properties_array(reader, count)

    if type_id == 0x1A:
        red = reader.read(count)
        green = reader.read(count)
        blue = reader.read(count)
        return [
            (red[i], green[i], blue[i])
            for i in range(count)
        ]

    if type_id == 0x1B:
        return _read_interleaved_i64s(
            reader.read(count * 8),
            count
        )

    if type_id == 0x21:

        # SecurityCapabilities is stored like Int64 (interleaved,
        # transformed u64s). It is not in the public format
        # documentation yet.

        return _read_interleaved_i64s(
            reader.read(count * 8),
            count
        )

    if type_id == 0x1C:
        return _read_interleaved_u32s(
            reader.read(count * 4),
            count
        )

    if type_id == 0x1D:
        return _decode_string_array(reader, count)

    if type_id == 0x1E:
        reader.u8()
        frames = _decode_cframe_array(reader, count)
        reader.u8()
        reader.read(count)
        return frames

    if type_id == 0x1F:
        reader.read(count * 16)
        return [None] * count

    if type_id == 0x20:
        return _decode_font_array(reader, count)

    if type_id == 0x22:
        return _decode_content_array(reader, count)

    if type_id == 0x23:
        return _decode_asset_content_map_array(reader, count)

    raise RobloxFileError(
        f"Unknown property type id {type_id:#04x}."
    )


# =====================================================================
# BINARY FORMAT PARSER
# =====================================================================


class _Instance:

    def __init__(self, ref, class_name):

        self.ref = ref
        self.class_name = class_name
        self.name = None
        self.source = None
        self.props = []
        self.children = []
        self.parent = None


def _decompress_chunk(body, compressed_length, uncompressed_length):

    if compressed_length == 0:

        return body

    if body[:4] == b"\x28\xb5\x2f\xfd":

        if ZSTD is None:

            raise RobloxFileError(
                "The zstandard package is needed for this file."
            )

        return ZSTD.ZstdDecompressor().decompress(
            body,
            max_output_size=uncompressed_length
        )

    if LZ4_BLOCK is None:

        raise RobloxFileError(
            "The lz4 package is needed for this file."
        )

    return LZ4_BLOCK.decompress(
        body,
        uncompressed_size=uncompressed_length
    )


def _parse_binary(data):

    reader = _Reader(data)

    magic = reader.read(8)

    if magic != BINARY_MAGIC:

        raise RobloxFileError("Not a binary Roblox file.")

    signature = reader.read(6)

    if signature != b"\x89\xff\x0d\x0a\x1a\x0a":

        raise RobloxFileError("Bad file signature.")

    version = reader.u16()
    class_count = reader.i32()
    instance_count = reader.i32()
    reader.read(8)

    meta = {}
    classes = {}
    instances = {}
    skipped_chunks = 0

    while reader.remaining() >= 16:

        raw_name = reader.read(4)
        chunk_name = raw_name.rstrip(b"\x00").decode("ascii", "replace")
        compressed_length = reader.u32()
        uncompressed_length = reader.u32()
        reader.read(4)

        body = reader.read(compressed_length or uncompressed_length)

        if chunk_name == "END":

            break

        try:

            body = _decompress_chunk(
                body,
                compressed_length,
                uncompressed_length
            )

        except RobloxFileError:

            raise

        except Exception as error:

            raise RobloxFileError(
                f"Could not decompress {chunk_name} chunk: {error}"
            ) from error

        chunk = _Reader(body)

        try:

            if chunk_name == "META":

                _parse_meta(chunk, meta)

            elif chunk_name == "INST":

                _parse_inst(
                    chunk,
                    classes,
                    instances,
                    instance_count
                )

            elif chunk_name == "PROP":

                _parse_prop(chunk, classes, instances)

            elif chunk_name == "PRNT":

                _parse_prnt(chunk, instances)

        except RobloxFileError:

            # One bad chunk must not kill the whole file; every
            # chunk is framed, so the outer reader is already
            # positioned at the next chunk.

            skipped_chunks += 1

            continue

    return {
        "version": version,
        "class_count": class_count,
        "instance_count": instance_count,
        "meta": meta,
        "instances": instances,
        "skipped_chunks": skipped_chunks
    }


def _parse_meta(chunk, meta):

    for _ in range(chunk.u32()):

        key = chunk.string().decode("utf-8", "replace")
        value = chunk.string().decode("utf-8", "replace")

        meta[key] = value


def _parse_inst(chunk, classes, instances, instance_count):

    class_id = chunk.u32()
    class_name = chunk.string().decode("utf-8", "replace")
    is_service = chunk.u8()
    count = chunk.u32()

    if count > instance_count:

        raise RobloxFileError(
            "Class claims more instances than the file contains."
        )

    refs = _read_interleaved_i32s(
        chunk.read(count * 4),
        count,
        accumulate=True
    )

    if is_service:

        chunk.read(count)

    classes[class_id] = (class_name, refs)

    for ref in refs:

        instances[ref] = _Instance(ref, class_name)


def _parse_prop(chunk, classes, instances):

    class_id = chunk.u32()
    prop_name = chunk.string().decode("utf-8", "replace")
    type_id = chunk.u8()

    entry = classes.get(class_id)

    if entry is None:

        return

    class_name, refs = entry

    if not refs:

        return

    try:

        values = _decode_values(
            chunk,
            type_id,
            len(refs)
        )

    except RobloxFileError:

        raise

    except Exception as error:

        raise RobloxFileError(
            f"Could not read property {prop_name!r} of {class_name}: "
            f"{error}"
        ) from error

    if prop_name in BLOB_PROPS:

        return

    for ref, value in zip(refs, values):

        instance = instances.get(ref)

        if instance is None:

            continue

        if prop_name == "Name" and type_id == 0x01:

            instance.name = value.decode("utf-8", "replace")

            continue

        if (
            prop_name == "Source"
            and type_id == 0x01
            and class_name in SCRIPT_CLASSES
        ):

            instance.source = value.decode("utf-8", "replace")

            continue

        if type_id in (0x1C, 0x1D):

            # SharedString indexes and Luau bytecode are not
            # useful as text context.

            return

        if type_id == 0x13:

            # Referents point at other instances; resolve names.

            target = instances.get(value)

            if target is None or value < 0:

                instance.props.append((prop_name, "none"))

            else:

                instance.props.append(
                    (
                        prop_name,
                        target.name or target.class_name
                    )
                )

            continue

        if type_id in (0x10, 0x1E):

            instance.props.append(
                (prop_name, _format_cframe(value))
            )

            continue

        if type_id == 0x01:

            if len(value) > 20_000:

                # Very large strings are binary blobs (mesh data,
                # terrain, etc.) and are useless as text context.

                continue

            text = value.decode("utf-8", "replace")

            if len(text) > MAX_PREVIEW_STRING:

                text = text[:MAX_PREVIEW_STRING] + "…"

            instance.props.append((prop_name, text))

            continue

        formatted = _format_value(prop_name, value)

        if formatted is not None:

            instance.props.append((prop_name, formatted))


def _parse_prnt(chunk, instances):

    version = chunk.u8()

    if version != 0:

        raise RobloxFileError(
            f"Unsupported PRNT chunk version {version}."
        )

    count = chunk.u32()

    children = _read_interleaved_i32s(
        chunk.read(count * 4),
        count,
        accumulate=True
    )
    parents = _read_interleaved_i32s(
        chunk.read(count * 4),
        count,
        accumulate=True
    )

    for child_ref, parent_ref in zip(children, parents):

        child = instances.get(child_ref)

        if child is None:

            continue

        parent = instances.get(parent_ref)

        child.parent = parent

        if parent is not None:

            parent.children.append(child)


# =====================================================================
# XML FORMAT PARSER
# =====================================================================


def _parse_xml(data):

    try:

        root = ElementTree.fromstring(data)

    except ElementTree.ParseError as error:

        raise RobloxFileError(
            f"Not a valid XML Roblox file: {error}"
        ) from error

    instances = {}
    roots = []
    counter = [0]

    def read_item(item, parent):

        counter[0] += 1
        ref = counter[0]

        instance = _Instance(
            ref,
            item.attrib.get("class", "?")
        )

        instances[ref] = instance

        instance.parent = parent

        if parent is None:

            roots.append(instance)

        else:

            parent.children.append(instance)

        properties = item.find("Properties")

        if properties is not None:

            for prop in properties:

                tag = prop.tag
                name = prop.attrib.get("name", "")

                if name == "Name":

                    instance.name = (prop.text or "").strip()

                    continue

                if (
                    name == "Source"
                    and instance.class_name in SCRIPT_CLASSES
                ):

                    instance.source = prop.text or ""

                    continue

                text = _xml_prop_text(prop)

                if text:

                    instance.props.append((name, text))

        for child_item in item.findall("Item"):

            read_item(child_item, instance)

    for item in root.findall("Item"):

        read_item(item, None)

    return {
        "meta": {},
        "instances": instances,
        "roots": roots
    }


def _xml_prop_text(prop):

    parts = []

    for child in prop.iter():

        if child is prop:

            text = child.text or ""

        else:

            text = child.text or ""

        text = text.strip()

        if text:
            parts.append(text)

    text = ", ".join(parts)

    if len(text) > MAX_PREVIEW_STRING:

        text = text[:MAX_PREVIEW_STRING] + "…"

    return text


# =====================================================================
# RENDERING
# =====================================================================


def _fmt_float(value):

    if value != value or value in (float("inf"), float("-inf")):

        return "0"

    text = f"{value:.4g}"

    return text


def _fmt_vector(values):

    parts = []

    for value in values:

        if isinstance(value, (int, float)):
            parts.append(_fmt_float(value))

        else:
            parts.append(str(value))

    return "(" + ", ".join(parts) + ")"


def _format_value(prop_name, value):

    if value is None:

        return None

    if isinstance(value, bool):
        return "true" if value else "false"

    if isinstance(value, int):
        return str(value)

    if isinstance(value, float):
        return _fmt_float(value)

    if isinstance(value, str):
        return '"' + value.replace("\n", " ") + '"'

    if isinstance(value, bytes):
        return None

    if isinstance(value, tuple):

        if len(value) == 3 and all(
            isinstance(v, (int, float)) for v in value
        ):
            return _fmt_vector(value)

        if len(value) == 2:
            return _fmt_vector(value)

        if len(value) == 4:
            return _fmt_vector(value)

        if len(value) == 6:
            return _fmt_vector(value)

        if len(value) == 9:
            return None

        return _fmt_vector(value)

    return None


def _format_cframe(value):

    position, rotation = value

    if isinstance(rotation, str) and rotation == "matrix":

        return _fmt_vector(position)

    if isinstance(rotation, str) and rotation.startswith("rot "):

        return _fmt_vector(position) + " " + rotation

    return _fmt_vector(position)


def _instance_line(instance):

    name = instance.name or instance.class_name
    name = name.replace("\n", " ")

    props = []

    for prop_name, text in instance.props:

        if prop_name in ("Name", "Source"):
            continue

        if prop_name in ("Position", "CFrame"):
            props.append(f"Position={text}")
            continue

        props.append(f"{prop_name}={text}")

    line = f'{instance.class_name} "{name}"'

    if props:

        line += " (" + ", ".join(props[:12]) + ")"

    return line


def _path_of(instance):

    parts = []
    current = instance

    while current is not None:

        parts.append(current.name or current.class_name)
        current = current.parent

    return "/".join(reversed(parts))


def _render(instances, roots, meta, header_lines):

    lines = list(header_lines)

    if meta:

        meta_text = ", ".join(
            f"{key}={value}"
            for key, value in sorted(meta.items())
        )

        lines.append(f"Metadata: {meta_text}")

    class_counts = {}

    for instance in instances.values():

        class_counts[instance.class_name] = (
            class_counts.get(instance.class_name, 0) + 1
        )

    summary = ", ".join(
        f"{name} ({count})"
        for name, count in sorted(class_counts.items())
    )

    lines.append(f"Instances: {summary}")

    script_lines = []

    for instance in sorted(
        instances.values(),
        key=lambda item: _path_of(item)
    ):

        if instance.source is None:

            continue

        source = instance.source

        if len(source) > MAX_SOURCE_CHARS:

            source = (
                source[:MAX_SOURCE_CHARS]
                + "\n-- [source truncated]"
            )

        script_lines.append(
            f"\n--- {_path_of(instance)} "
            f"({instance.class_name}) ---\n"
            f"{source}"
        )

    if script_lines:

        lines.append("\n=== Script sources ===")
        lines.extend(script_lines)

    lines.append("\n=== Instance tree ===")

    tree_lines = 0

    def render_instance(instance, depth):

        nonlocal tree_lines

        if tree_lines >= MAX_TREE_LINES:

            return

        indent = "  " * depth
        line = _instance_line(instance)

        if instance.source is not None:

            line_count = len(instance.source.splitlines())
            line += f" [Lua source: {line_count} lines]"

        lines.append(indent + line)
        tree_lines += 1

        for child in instance.children:

            render_instance(child, depth + 1)

    for root in roots:

        render_instance(root, 0)

    if tree_lines >= MAX_TREE_LINES:

        lines.append("[instance tree truncated]")

    return "\n".join(lines)


def _roots_from_parents(instances):

    roots = []

    for instance in instances.values():

        if instance.parent is None:

            roots.append(instance)

    return roots


def extract_text(data, filename=""):

    if not data:

        raise RobloxFileError("The file is empty.")

    if data[:8] == BINARY_MAGIC:

        parsed = _parse_binary(data)

        header = (
            f"[Roblox file: {filename or 'model'} — binary format "
            f"(version {parsed['version']})]"
        )

        if parsed.get("skipped_chunks"):

            header += (
                f" — {parsed['skipped_chunks']} chunk(s) could not "
                "be decoded and were skipped"
            )

        roots = _roots_from_parents(parsed["instances"])

        return _render(
            parsed["instances"],
            roots,
            parsed["meta"],
            [header]
        )

    head = data[:4096].lstrip()

    if head[:7] == b"<roblox":

        parsed = _parse_xml(data)

        header = (
            f"[Roblox file: {filename or 'model'} — XML format]"
        )

        return _render(
            parsed["instances"],
            parsed["roots"],
            parsed["meta"],
            [header]
        )

    raise RobloxFileError(
        "Not a recognized Roblox file (expected binary or XML format)."
    )
