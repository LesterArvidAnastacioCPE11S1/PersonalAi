import fnmatch
import os

from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent.parent

SENSITIVE_NAMES = (
    ".env",
    ".env.*",
    "*.pem",
    "*.key",
    "*.pfx",
    "*.p12",
    "*.kdbx",
    "id_rsa*",
    "id_ed25519*",
    "id_ecdsa*",
    "credentials.json",
    "secrets.json",
    "*.env"
)

SENSITIVE_PARTS = {
    ".ssh",
    ".aws",
    ".azure",
    ".gnupg",
    ".config"
}

DENY_PREFIXES = (
    "c:\\windows",
    "c:\\program files",
    "c:\\program files (x86)",
    "c:\\programdata",
    "c:\\$recycle.bin",
    "c:\\system volume information"
)


class ToolError(RuntimeError):
    pass


def _norm(value):

    return os.path.normcase(str(value))


def _clean_root(value):

    text = os.path.expandvars(str(value or "").strip())
    path = Path(os.path.expanduser(text))

    if not path.is_absolute():

        path = ROOT / path

    try:

        return path.resolve()

    except OSError:

        return path.absolute()


class PathPolicy:

    def __init__(self, config):

        self.config = config
        self.roots = []

        for value in config.roots:

            path = _clean_root(value)

            if path not in self.roots:

                self.roots.append(path)

        if not self.roots:

            self.roots.append(ROOT)

        self._root_keys = [_norm(item) for item in self.roots]

        self._root_prefixes = [
            key.rstrip(os.sep) + os.sep
            for key in self._root_keys
        ]

    def describe(self):

        return [str(item) for item in self.roots]

    def resolve(self, value="", must_exist=False):

        if value is None:

            value = ""

        text = os.path.expandvars(str(value).strip())

        if len(text) == 2 and text[1] == ":" and text[0].isalpha():

            text += os.sep

        path = Path(os.path.expanduser(text))

        if not text:

            path = self.roots[0]

        elif not path.is_absolute():

            path = self.roots[0] / path

        try:

            path = path.resolve()

        except OSError:

            path = path.absolute()

        key = _norm(path)

        for prefix in DENY_PREFIXES:

            if key == prefix or key.startswith(prefix + os.sep):

                raise ToolError(
                    f"Access to system folders is blocked: {path}"
                )

        for index, root in enumerate(self.roots):

            root_key = self._root_keys[index]
            prefix = self._root_prefixes[index]

            if key == root_key or key.startswith(prefix):

                break

        else:

            raise ToolError(
                "Path is outside the allowed folders. Allowed: "
                + "; ".join(self.describe())
            )

        if must_exist and not path.exists():

            raise ToolError(f"Path does not exist: {path}")

        return path

    def check_sensitive(self, path):

        if not self.config.block_sensitive:

            return

        name = path.name.lower()

        for pattern in SENSITIVE_NAMES:

            if fnmatch.fnmatch(name, pattern):

                raise ToolError(
                    f"Access to protected files is blocked: {path.name}"
                )

        parts = {part.lower() for part in path.parts}

        for item in SENSITIVE_PARTS:

            if item in parts:

                raise ToolError(
                    f"Access to protected folders is blocked: {item}"
                )
