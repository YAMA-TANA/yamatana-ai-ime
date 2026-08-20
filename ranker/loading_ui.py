"""Non-activating loading indicator overlay for resident AI IME ranker.

Displays a subtle, topmost, non-activating floating pill ("AI変換中…")
exclusively while AI inference is running, ensuring keyboard focus and caret
are never stolen from the active application.
"""

from __future__ import annotations

import contextlib
import ctypes
from ctypes import wintypes
import logging
import sys
import threading
import time
from typing import Iterator, Optional

LOG = logging.getLogger("ai_ime_loading_ui")


class _Win32LoadingWindow:
    """Win32 layered, non-activating popup window."""

    WS_POPUP = 0x80000000
    WS_EX_TOPMOST = 0x00000008
    WS_EX_TOOLWINDOW = 0x00000080
    WS_EX_LAYERED = 0x00080000
    WS_EX_NOACTIVATE = 0x08000000

    SW_HIDE = 0
    SW_SHOWNOACTIVATE = 4

    WM_DESTROY = 0x0002
    WM_PAINT = 0x000F
    WM_USER = 0x0400
    WM_SHOW_INDICATOR = WM_USER + 1
    WM_HIDE_INDICATOR = WM_USER + 2
    WM_QUIT_THREAD = WM_USER + 3

    LWA_ALPHA = 0x00000002

    def __init__(self, text: str = "AI変換中…") -> None:
        self.text = text
        self.hwnd: Optional[wintypes.HWND] = None
        self._thread: Optional[threading.Thread] = None
        self._ready_event = threading.Event()
        self._is_visible = False
        self._width = 128
        self._height = 30

    def start(self) -> bool:
        if sys.platform != "win32":
            return False
        if self._thread and self._thread.is_alive():
            return True
        self._ready_event.clear()
        self._thread = threading.Thread(
            target=self._run_message_loop, daemon=True, name="LoadingUIThread"
        )
        self._thread.start()
        return self._ready_event.wait(timeout=2.0)

    def stop(self) -> None:
        if self.hwnd and sys.platform == "win32":
            ctypes.windll.user32.PostMessageW(self.hwnd, self.WM_QUIT_THREAD, 0, 0)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self.hwnd = None

    def show(self) -> None:
        if self.hwnd and sys.platform == "win32":
            ctypes.windll.user32.PostMessageW(self.hwnd, self.WM_SHOW_INDICATOR, 0, 0)
            self._is_visible = True

    def hide(self) -> None:
        if self.hwnd and sys.platform == "win32":
            ctypes.windll.user32.PostMessageW(self.hwnd, self.WM_HIDE_INDICATOR, 0, 0)
            self._is_visible = False

    def _get_target_position(self) -> tuple[int, int]:
        user32 = ctypes.windll.user32
        screen_w = user32.GetSystemMetrics(0)
        screen_h = user32.GetSystemMetrics(1)
        fallback_x = screen_w - self._width - 24
        fallback_y = screen_h - self._height - 60

        try:
            class POINT(ctypes.Structure):
                _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

            class RECT(ctypes.Structure):
                _fields_ = [
                    ("left", ctypes.c_long),
                    ("top", ctypes.c_long),
                    ("right", ctypes.c_long),
                    ("bottom", ctypes.c_long),
                ]

            class GUITHREADINFO(ctypes.Structure):
                _fields_ = [
                    ("cbSize", ctypes.c_ulong),
                    ("flags", ctypes.c_ulong),
                    ("hwndActive", wintypes.HWND),
                    ("hwndFocus", wintypes.HWND),
                    ("hwndCapture", wintypes.HWND),
                    ("hwndMenuOwner", wintypes.HWND),
                    ("hwndMoveSize", wintypes.HWND),
                    ("hwndCaret", wintypes.HWND),
                    ("rcCaret", RECT),
                ]

            hwnd_fg = user32.GetForegroundWindow()
            if hwnd_fg:
                tid = user32.GetWindowThreadProcessId(hwnd_fg, None)
                gui_info = GUITHREADINFO(cbSize=ctypes.sizeof(GUITHREADINFO))
                if user32.GetGUIThreadInfo(tid, ctypes.byref(gui_info)):
                    if gui_info.hwndCaret and (gui_info.rcCaret.right > gui_info.rcCaret.left):
                        pt = POINT(gui_info.rcCaret.left, gui_info.rcCaret.bottom + 6)
                        user32.ClientToScreen(gui_info.hwndCaret, ctypes.byref(pt))
                        if 0 <= pt.x <= screen_w - self._width and 0 <= pt.y <= screen_h - self._height:
                            return pt.x, pt.y

                cursor_pt = POINT()
                if user32.GetCursorPos(ctypes.byref(cursor_pt)):
                    target_x = cursor_pt.x + 16
                    target_y = cursor_pt.y + 16
                    target_x = max(10, min(screen_w - self._width - 10, target_x))
                    target_y = max(10, min(screen_h - self._height - 10, target_y))
                    return target_x, target_y
        except Exception as exc:
            LOG.debug("Error obtaining caret position: %s", exc)

        return fallback_x, fallback_y

    def _paint(self, hwnd: wintypes.HWND) -> None:
        user32 = ctypes.windll.user32
        gdi32 = ctypes.windll.gdi32

        class PAINTSTRUCT(ctypes.Structure):
            _fields_ = [
                ("hdc", wintypes.HDC),
                ("fErase", wintypes.BOOL),
                ("rcPaint", wintypes.RECT),
                ("fRestore", wintypes.BOOL),
                ("fIncUpdate", wintypes.BOOL),
                ("rgbReserved", ctypes.c_byte * 32),
            ]

        ps = PAINTSTRUCT()
        hdc = user32.BeginPaint(hwnd, ctypes.byref(ps))
        if not hdc:
            return

        rect = wintypes.RECT(0, 0, self._width, self._height)

        # Background rounded pill: dark sleek theme #1c1f2b (RGB 28, 31, 43)
        bg_brush = gdi32.CreateSolidBrush(0x002B1F1C)  # BGR format
        # Border pen: accent blue/purple #5c7cfa (RGB 92, 124, 250)
        border_pen = gdi32.CreatePen(0, 1, 0x00FA7C5C)  # BGR format

        old_brush = gdi32.SelectObject(hdc, bg_brush)
        old_pen = gdi32.SelectObject(hdc, border_pen)

        gdi32.RoundRect(hdc, 0, 0, self._width, self._height, 12, 12)

        # Small sparkle / dot: cyan/blue #38d9a9
        dot_brush = gdi32.CreateSolidBrush(0x00A9D938)
        gdi32.SelectObject(hdc, dot_brush)
        gdi32.RoundRect(hdc, 12, 10, 22, 20, 10, 10)
        gdi32.DeleteObject(dot_brush)

        # Text rendering
        gdi32.SetBkMode(hdc, 1)  # TRANSPARENT
        gdi32.SetTextColor(hdc, 0x00F0F0F0)  # Off-white BGR

        font = gdi32.CreateFontW(
            -13, 0, 0, 0, 600, 0, 0, 0,
            1, 0, 0, 2, 0, "Yu Gothic UI"
        )
        old_font = gdi32.SelectObject(hdc, font)

        text_rect = wintypes.RECT(28, 0, self._width - 8, self._height)
        DT_SINGLELINE = 0x00000020
        DT_VCENTER = 0x00000004
        DT_LEFT = 0x00000000
        user32.DrawTextW(
            hdc, self.text, -1, ctypes.byref(text_rect),
            DT_SINGLELINE | DT_VCENTER | DT_LEFT
        )

        # Cleanup
        gdi32.SelectObject(hdc, old_font)
        gdi32.DeleteObject(font)
        gdi32.SelectObject(hdc, old_pen)
        gdi32.DeleteObject(border_pen)
        gdi32.SelectObject(hdc, old_brush)
        gdi32.DeleteObject(bg_brush)

        user32.EndPaint(hwnd, ctypes.byref(ps))

    def _run_message_loop(self) -> None:
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        # Explicitly configure 64-bit signatures
        user32.DefWindowProcW.argtypes = [wintypes.HWND, ctypes.c_uint, wintypes.WPARAM, wintypes.LPARAM]
        user32.DefWindowProcW.restype = ctypes.c_longlong

        WNDPROC = ctypes.WINFUNCTYPE(
            ctypes.c_longlong, wintypes.HWND, ctypes.c_uint, wintypes.WPARAM, wintypes.LPARAM
        )

        def wnd_proc(hwnd: wintypes.HWND, msg: int, wparam: int, lparam: int) -> int:
            if msg == self.WM_PAINT:
                self._paint(hwnd)
                return 0
            elif msg == self.WM_SHOW_INDICATOR:
                x, y = self._get_target_position()
                SWP_NOACTIVATE = 0x0010
                SWP_SHOWWINDOW = 0x0040
                HWND_TOPMOST = -1
                user32.SetWindowPos(
                    hwnd, HWND_TOPMOST, x, y, self._width, self._height,
                    SWP_NOACTIVATE | SWP_SHOWWINDOW
                )
                user32.ShowWindow(hwnd, self.SW_SHOWNOACTIVATE)
                user32.InvalidateRect(hwnd, None, True)
                user32.UpdateWindow(hwnd)
                return 0
            elif msg == self.WM_HIDE_INDICATOR:
                user32.ShowWindow(hwnd, self.SW_HIDE)
                return 0
            elif msg == self.WM_QUIT_THREAD:
                user32.DestroyWindow(hwnd)
                return 0
            elif msg == self.WM_DESTROY:
                user32.PostQuitMessage(0)
                return 0
            return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

        self._wnd_proc_ref = WNDPROC(wnd_proc)

        class WNDCLASSEXW(ctypes.Structure):
            _fields_ = [
                ("cbSize", ctypes.c_uint),
                ("style", ctypes.c_uint),
                ("lpfnWndProc", WNDPROC),
                ("cbClsExtra", ctypes.c_int),
                ("cbWndExtra", ctypes.c_int),
                ("hInstance", wintypes.HINSTANCE),
                ("hIcon", wintypes.HICON),
                ("hCursor", wintypes.HICON),
                ("hbrBackground", wintypes.HBRUSH),
                ("lpszMenuName", wintypes.LPCWSTR),
                ("lpszClassName", wintypes.LPCWSTR),
                ("hIconSm", wintypes.HICON),
            ]

        hinst = kernel32.GetModuleHandleW(None)
        class_name = f"AiImeLoadingIndicator_{id(self)}"

        wc = WNDCLASSEXW()
        wc.cbSize = ctypes.sizeof(WNDCLASSEXW)
        wc.style = 3  # CS_HREDRAW | CS_VREDRAW
        wc.lpfnWndProc = self._wnd_proc_ref
        wc.hInstance = hinst
        wc.hCursor = user32.LoadCursorW(None, 32512)  # IDC_ARROW
        wc.lpszClassName = class_name

        atom = user32.RegisterClassExW(ctypes.byref(wc))
        if not atom:
            self._ready_event.set()
            return

        hwnd = user32.CreateWindowExW(
            self.WS_EX_TOPMOST | self.WS_EX_TOOLWINDOW | self.WS_EX_NOACTIVATE | self.WS_EX_LAYERED,
            class_name,
            "AI IME Indicator",
            self.WS_POPUP,
            -1000, -1000, self._width, self._height,
            None, None, hinst, None
        )

        if not hwnd:
            self._ready_event.set()
            return

        # Set 92% opacity (235/255)
        user32.SetLayeredWindowAttributes(hwnd, 0, 235, self.LWA_ALPHA)
        self.hwnd = hwnd
        self._ready_event.set()

        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

        user32.UnregisterClassW(class_name, hinst)
        self.hwnd = None


class LoadingIndicator:
    """Thread-safe, non-activating loading indicator controller."""

    def __init__(self, text: str = "AI変換中…", enabled: bool = True) -> None:
        self.enabled = enabled and sys.platform == "win32"
        self._window = _Win32LoadingWindow(text) if self.enabled else None

    def start(self) -> None:
        if self._window:
            self._window.start()

    def stop(self) -> None:
        if self._window:
            self._window.stop()

    def show(self) -> None:
        if self._window:
            self._window.show()

    def hide(self) -> None:
        if self._window:
            self._window.hide()

    @contextlib.contextmanager
    def active(self) -> Iterator[None]:
        if not self._window:
            yield
            return
        self.show()
        try:
            yield
        finally:
            self.hide()
