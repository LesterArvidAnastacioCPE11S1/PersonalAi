import ctypes
import ctypes.wintypes
import os
import subprocess
import time
import webbrowser

from pathlib import Path

CHROMIUM = {
    "chrome.exe",
    "msedge.exe",
    "brave.exe",
    "vivaldi.exe",
    "opera.exe"
}

BROWSER_SUFFIXES = (
    " - google chrome",
    " - microsoft edge",
    " - brave",
    " - vivaldi",
    " - opera",
    " - mozilla firefox",
    "\u2014 mozilla firefox"
)

VK_MENU = 0x12
VK_KEYUP = 0x0002
SW_RESTORE = 9


def _browser_path():

    try:

        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\Shell\Associations"
            r"\UrlAssociations\http\UserChoice"
        ) as key:

            prog_id = winreg.QueryValueEx(key, "ProgId")[0]

        with winreg.OpenKey(
            winreg.HKEY_CLASSES_ROOT,
            f"{prog_id}\\shell\\open\\command"
        ) as key:

            command = winreg.QueryValueEx(key, "")[0]

    except OSError:

        return None

    if not command.startswith('"'):

        return None

    end = command.find('"', 1)

    if end <= 0:

        return None

    path = Path(command[1:end])

    return path if path.exists() else None


def _title(hwnd):

    user32 = ctypes.windll.user32
    length = user32.GetWindowTextLengthW(hwnd)

    if not length:

        return ""

    buffer = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buffer, length + 1)

    return buffer.value.strip()


def _foreground_title():

    return _title(ctypes.windll.user32.GetForegroundWindow())


def _matches(title, title_part):

    lowered = title.lower()
    wanted = title_part.lower()

    if lowered == wanted:

        return True

    if lowered.endswith(BROWSER_SUFFIXES):

        return False

    return wanted in lowered


def _process_name(pid):

    kernel32 = ctypes.windll.kernel32
    kernel32.OpenProcess.restype = ctypes.wintypes.HANDLE
    kernel32.OpenProcess.argtypes = (
        ctypes.wintypes.DWORD,
        ctypes.wintypes.BOOL,
        ctypes.wintypes.DWORD
    )
    kernel32.CloseHandle.argtypes = (ctypes.wintypes.HANDLE,)
    handle = kernel32.OpenProcess(0x1000, False, pid)

    if not handle:

        return ""

    try:

        size = ctypes.wintypes.DWORD(1024)
        buffer = ctypes.create_unicode_buffer(size.value)

        if not kernel32.QueryFullProcessImageNameW(
            handle,
            0,
            buffer,
            ctypes.byref(size)
        ):

            return ""

        return Path(buffer.value).name.lower()

    finally:

        kernel32.CloseHandle(handle)


def _find_window(title_part):

    user32 = ctypes.windll.user32
    exact = []
    matches = []
    callback_type = ctypes.WINFUNCTYPE(
        ctypes.c_bool,
        ctypes.wintypes.HWND,
        ctypes.wintypes.LPARAM
    )

    def visit(hwnd, _):

        if not user32.IsWindowVisible(hwnd):

            return True

        title = _title(hwnd)

        if not title or not _matches(title, title_part):

            return True

        pid = ctypes.wintypes.DWORD()
        user32.GetWindowThreadProcessId(
            hwnd,
            ctypes.byref(pid)
        )

        if _process_name(pid.value) not in CHROMIUM:

            return True

        if title.lower() == title_part.lower():

            exact.append(hwnd)

        else:

            matches.append(hwnd)

        return True

    user32.EnumWindows(callback_type(visit), 0)

    targets = exact or matches

    return targets[0] if targets else None


def _tap_alt():

    user32 = ctypes.windll.user32
    user32.keybd_event(VK_MENU, 0, 0, 0)
    user32.keybd_event(VK_MENU, 0, VK_KEYUP, 0)


def _activate(hwnd):

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    kernel32.GetCurrentThreadId.restype = ctypes.wintypes.DWORD
    user32.GetWindowThreadProcessId.restype = ctypes.wintypes.DWORD
    user32.ShowWindow(hwnd, SW_RESTORE)
    _tap_alt()

    current = kernel32.GetCurrentThreadId()
    foreground = user32.GetWindowThreadProcessId(
        user32.GetForegroundWindow(),
        None
    )

    attached = False

    if foreground and foreground != current:

        attached = bool(
            user32.AttachThreadInput(foreground, current, True)
        )

    user32.BringWindowToTop(hwnd)
    user32.SetForegroundWindow(hwnd)
    user32.SetFocus(hwnd)

    if attached:

        user32.AttachThreadInput(foreground, current, False)


def focus_window(title_part, attempts=6):

    for _ in range(attempts):

        hwnd = _find_window(title_part)

        if hwnd is None:

            return False

        _activate(hwnd)
        time.sleep(0.3)

        if _matches(_foreground_title(), title_part):

            return True

    return False


def _profile_dir():

    base = os.environ.get("LOCALAPPDATA")

    if not base:

        return None

    return Path(base) / "PersonalAI" / "browser"


def _launch(path, url):

    arguments = [
        str(path),
        f"--app={url}",
        "--no-first-run",
        "--no-default-browser-check",
        "--window-size=1280,820"
    ]

    profile = _profile_dir()

    if profile is not None:

        profile.mkdir(parents=True, exist_ok=True)
        arguments.insert(1, f"--user-data-dir={profile}")

    subprocess.Popen(arguments)


def _wait_for_window():

    for _ in range(20):

        time.sleep(0.25)

        if _find_window("PersonalAI") is not None:

            return focus_window("PersonalAI")

    return False


def open_ui(url):

    if focus_window("PersonalAI"):

        return True

    path = _browser_path()

    if path is not None and path.name.lower() in CHROMIUM:

        _launch(path, url)

        if _wait_for_window():

            return True

        time.sleep(1.0)
        _launch(path, url)

        if _wait_for_window():

            return True

    webbrowser.open(url)

    return True
