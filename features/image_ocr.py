from io import BytesIO
from threading import Lock

import numpy as np

from PIL import Image, ImageOps


MAX_IMAGE_EDGE = 3000
_ENGINE = None
_ENGINE_LOCK = Lock()


class ImageOCRError(RuntimeError):
    pass


def extract_text(data: bytes) -> str:
    try:
        with Image.open(BytesIO(data)) as source:
            source.seek(0)
            image = ImageOps.exif_transpose(source).convert("RGB")
            image.thumbnail(
                (MAX_IMAGE_EDGE, MAX_IMAGE_EDGE),
                Image.Resampling.LANCZOS
            )
            pixels = np.asarray(image)

        with _ENGINE_LOCK:
            global _ENGINE
            if _ENGINE is None:
                from rapidocr import RapidOCR

                _ENGINE = RapidOCR()
            result = _ENGINE(pixels)

        texts = getattr(result, "txts", None) or ()
        return "\n".join(
            text.strip()
            for text in texts
            if isinstance(text, str) and text.strip()
        )
    except Exception as error:
        raise ImageOCRError(
            f"Local OCR could not read this image: {error}"
        ) from error
