import ctypes
from ctypes import (
    Structure,
    byref,
    c_int,
    c_ubyte,
    c_uint,
    c_ulong,
    c_void_p,
)
import time
from PyQt5.QtCore import QThread, pyqtSignal

x11 = ctypes.cdll.LoadLibrary("libX11.so.6")

Display_p = c_void_p
Window = c_ulong
KeyCode = c_ubyte
KeySym = c_ulong
Bool = c_int

x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
x11.XOpenDisplay.restype = Display_p
x11.XCloseDisplay.argtypes = [Display_p]
x11.XCloseDisplay.restype = c_int
x11.XDefaultRootWindow.argtypes = [Display_p]
x11.XDefaultRootWindow.restype = Window
x11.XStringToKeysym.argtypes = [ctypes.c_char_p]
x11.XStringToKeysym.restype = KeySym
x11.XKeysymToKeycode.argtypes = [Display_p, KeySym]
x11.XKeysymToKeycode.restype = KeyCode
x11.XGrabKey.argtypes = [Display_p, c_int, c_uint, Window, Bool, c_int, c_int]
x11.XGrabKey.restype = c_int
x11.XUngrabKey.argtypes = [Display_p, c_int, c_uint, Window]
x11.XUngrabKey.restype = c_int
x11.XNextEvent.argtypes = [Display_p, c_void_p]
x11.XNextEvent.restype = c_int
x11.XPending.argtypes = [Display_p]
x11.XPending.restype = c_int
x11.XFlush.argtypes = [Display_p]
x11.XFlush.restype = c_int

XErrorHandler = ctypes.CFUNCTYPE(c_int, Display_p, c_void_p)
x11.XSetErrorHandler.argtypes = [XErrorHandler]
x11.XSetErrorHandler.restype = XErrorHandler


def _err_cb(display, event):
    return 0


_c_err_handler = XErrorHandler(_err_cb)

KeyPress = 2
GrabModeAsync = 1


class XEvent(Structure):
    _fields_ = [("type", c_int), ("pad", c_ulong * 24)]


class GlobalHotkeyThread(QThread):
    activated = pyqtSignal()

    def __init__(self, key_name: str = "F8", parent=None):
        super().__init__(parent)
        self.key_name = key_name.encode("utf-8")
        self._running = True

    def run(self):
        x11.XSetErrorHandler(_c_err_handler)
        display = x11.XOpenDisplay(None)
        if not display:
            return

        root = x11.XDefaultRootWindow(display)
        keysym = x11.XStringToKeysym(self.key_name)
        keycode = x11.XKeysymToKeycode(display, keysym)
        if keycode == 0:
            x11.XCloseDisplay(display)
            return

        modifiers = [0, 0x10, 0x02, 0x12]
        for mod in modifiers:
            x11.XGrabKey(
                display, keycode, mod, root, False, GrabModeAsync, GrabModeAsync
            )
        x11.XFlush(display)

        event = XEvent()
        while self._running:
            while x11.XPending(display) > 0:
                x11.XNextEvent(display, byref(event))
                if event.type == KeyPress:
                    self.activated.emit()
            time.sleep(0.04)

        for mod in modifiers:
            x11.XUngrabKey(display, keycode, mod, root)
        x11.XFlush(display)
        x11.XCloseDisplay(display)

    def stop(self):
        self._running = False
        self.wait(500)
