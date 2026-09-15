import ctypes
from ctypes import c_void_p, c_ulong, c_int, byref, POINTER
from PyQt5.QtCore import Qt, QPoint, QRect
from PyQt5.QtGui import QPainter, QColor, QPen, QFont
from PyQt5.QtWidgets import QWidget
from src.config import load_config, save_config

MARGIN = 12

x11 = ctypes.cdll.LoadLibrary("libX11.so.6")
xfixes = ctypes.cdll.LoadLibrary("libXfixes.so.3")

x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
x11.XOpenDisplay.restype = c_void_p
x11.XCloseDisplay.argtypes = [c_void_p]
x11.XCloseDisplay.restype = c_int
x11.XFlush.argtypes = [c_void_p]
x11.XFlush.restype = c_int

xfixes.XFixesQueryExtension.argtypes = [c_void_p, POINTER(c_int), POINTER(c_int)]
xfixes.XFixesQueryExtension.restype = c_int
xfixes.XFixesCreateRegion.argtypes = [c_void_p, c_void_p, c_int]
xfixes.XFixesCreateRegion.restype = c_ulong
xfixes.XFixesSetWindowShapeRegion.argtypes = [c_void_p, c_ulong, c_int, c_int, c_int, c_ulong]
xfixes.XFixesSetWindowShapeRegion.restype = None
xfixes.XFixesDestroyRegion.argtypes = [c_void_p, c_ulong]
xfixes.XFixesDestroyRegion.restype = None

SHAPE_INPUT = 2


def set_window_clickthrough(win_id: int, enable: bool):
    display = x11.XOpenDisplay(None)
    if not display:
        return

    event_base = c_int()
    error_base = c_int()
    if not xfixes.XFixesQueryExtension(display, byref(event_base), byref(error_base)):
        x11.XCloseDisplay(display)
        return

    if enable:
        empty_region = xfixes.XFixesCreateRegion(display, None, 0)
        xfixes.XFixesSetWindowShapeRegion(display, c_ulong(win_id), SHAPE_INPUT, 0, 0, empty_region)
        xfixes.XFixesDestroyRegion(display, empty_region)
    else:
        xfixes.XFixesSetWindowShapeRegion(display, c_ulong(win_id), SHAPE_INPUT, 0, 0, 0)

    x11.XFlush(display)
    x11.XCloseDisplay(display)


def draw_hud_corners(painter: QPainter, rect: QRect, color: QColor):
    arm = 10
    pen = QPen(color, 2)
    painter.setPen(pen)

    painter.drawLine(rect.left(), rect.top(), rect.left() + arm, rect.top())
    painter.drawLine(rect.left(), rect.top(), rect.left(), rect.top() + arm)
    painter.drawLine(rect.right(), rect.top(), rect.right() - arm, rect.top())
    painter.drawLine(rect.right(), rect.top(), rect.right(), rect.top() + arm)
    painter.drawLine(rect.left(), rect.bottom(), rect.left() + arm, rect.bottom())
    painter.drawLine(rect.left(), rect.bottom(), rect.left(), rect.bottom() - arm)
    painter.drawLine(rect.right(), rect.bottom(), rect.right() - arm, rect.bottom())
    painter.drawLine(rect.right(), rect.bottom(), rect.right(), rect.bottom() - arm)


class ResizableWindow(QWidget):
    def __init__(self, config_key: str, min_w=160, min_h=50):
        super().__init__()
        self.config_key = config_key
        self.min_w = min_w
        self.min_h = min_h
        self._allow_close = False

        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.BypassWindowManagerHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.NoFocus)

        self.edit_mode = False
        self.resize_edge = 0
        self.drag_start_pos = QPoint()
        self.drag_start_geo = QRect()

        self.restore_geometry()

    def closeEvent(self, event):
        if self._allow_close:
            event.accept()
        else:
            event.ignore()

    def showEvent(self, event):
        super().showEvent(event)
        self.apply_clickthrough_state()

    def set_edit_mode(self, enabled: bool):
        self.edit_mode = enabled
        self.apply_clickthrough_state()
        if not enabled:
            self.setCursor(Qt.ArrowCursor)
            self.save_current_geometry()
        self.update()

    def apply_clickthrough_state(self):
        wid = int(self.winId())
        if wid > 2:
            set_window_clickthrough(wid, not self.edit_mode)

    def restore_geometry(self):
        cfg = load_config()
        geo = cfg.get(self.config_key, {})
        default_y = 550 if self.config_key == "capture_rect" else 380
        x = geo.get("x", 240)
        y = geo.get("y", default_y)
        w = geo.get("w", 800)
        h = geo.get("h", 120 if self.config_key == "capture_rect" else 140)
        self.setGeometry(x, y, w, h)

    def save_current_geometry(self):
        cfg = load_config()
        geo = self.geometry()
        cfg[self.config_key] = {
            "x": geo.x(), "y": geo.y(),
            "w": geo.width(), "h": geo.height()
        }
        save_config(cfg)

    def get_edge(self, pos: QPoint) -> int:
        edge = 0
        if pos.x() <= MARGIN: edge |= 1
        elif pos.x() >= self.width() - MARGIN: edge |= 2
        if pos.y() <= MARGIN: edge |= 4
        elif pos.y() >= self.height() - MARGIN: edge |= 8
        return edge

    def update_cursor_shape(self, edge: int):
        if not self.edit_mode:
            return
        if edge in (1 | 4, 2 | 8): self.setCursor(Qt.SizeFDiagCursor)
        elif edge in (2 | 4, 1 | 8): self.setCursor(Qt.SizeBDiagCursor)
        elif edge in (1, 2): self.setCursor(Qt.SizeHorCursor)
        elif edge in (4, 8): self.setCursor(Qt.SizeVerCursor)
        else: self.setCursor(Qt.OpenHandCursor)

    def mousePressEvent(self, event):
        if not self.edit_mode or event.button() != Qt.LeftButton:
            return
        self.drag_start_pos = event.globalPos()
        self.drag_start_geo = self.geometry()
        self.resize_edge = self.get_edge(event.pos())
        if self.resize_edge == 0:
            self.setCursor(Qt.ClosedHandCursor)
        event.accept()

    def mouseMoveEvent(self, event):
        if not self.edit_mode:
            return

        if event.buttons() & Qt.LeftButton:
            delta = event.globalPos() - self.drag_start_pos
            if self.resize_edge == 0:
                self.move(self.drag_start_geo.topLeft() + delta)
            else:
                rect = QRect(self.drag_start_geo)
                if self.resize_edge & 1:
                    nl = rect.left() + delta.x()
                    if rect.right() - nl >= self.min_w: rect.setLeft(nl)
                if self.resize_edge & 2:
                    nr = rect.right() + delta.x()
                    if nr - rect.left() >= self.min_w: rect.setRight(nr)
                if self.resize_edge & 4:
                    nt = rect.top() + delta.y()
                    if rect.bottom() - nt >= self.min_h: rect.setTop(nt)
                if self.resize_edge & 8:
                    nb = rect.bottom() + delta.y()
                    if nb - rect.top() >= self.min_h: rect.setBottom(nb)
                self.setGeometry(rect)
            event.accept()
        else:
            self.update_cursor_shape(self.get_edge(event.pos()))

    def mouseReleaseEvent(self, event):
        if self.edit_mode and event.button() == Qt.LeftButton:
            self.resize_edge = 0
            self.update_cursor_shape(self.get_edge(event.pos()))
            self.save_current_geometry()
            event.accept()


class CaptureFrame(ResizableWindow):
    def __init__(self):
        super().__init__("capture_rect", min_w=120, min_h=40)
        self.border_color = QColor("#00FF88")
        self.reload_style()

    def reload_style(self):
        cfg = load_config()
        self.border_color = QColor(cfg.get("styles", {}).get("border_color", "#00FF88"))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        draw_rect = self.rect().adjusted(1, 1, -1, -1)

        if self.edit_mode:
            fill = QColor(self.border_color)
            fill.setAlpha(15)
            painter.setBrush(fill)
            painter.setPen(QPen(self.border_color, 1.2, Qt.DashLine))
            painter.drawRoundedRect(draw_rect, 4, 4)
            draw_hud_corners(painter, draw_rect, self.border_color)
        else:
            cfg = load_config()
            if cfg.get("show_capture_border", False):
                faint = QColor(self.border_color)
                faint.setAlpha(40)
                painter.setPen(QPen(faint, 1, Qt.DotLine))
                painter.drawRoundedRect(draw_rect, 4, 4)


class TranslationFrame(ResizableWindow):
    def __init__(self):
        super().__init__("overlay_rect", min_w=180, min_h=50)
        self.current_text = "Ожидание текста..."
        self.bg_color = QColor(15, 18, 25, 215)
        self.font_size = 15
        self.reload_style()

    def reload_style(self):
        cfg = load_config()
        styles = cfg.get("styles", {})
        alpha = int(255 * (styles.get("overlay_opacity", 85) / 100))
        self.bg_color = QColor(styles.get("overlay_bg_color", "#0F1219"))
        self.bg_color.setAlpha(alpha)
        self.font_size = styles.get("font_size", 15)
        self.update()

    def set_translation(self, text: str):
        self.current_text = text
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        draw_rect = self.rect().adjusted(1, 1, -1, -1)

        painter.setBrush(self.bg_color)
        border_pen = QPen(
            QColor(0, 255, 136, 160) if self.edit_mode else QColor(255, 255, 255, 30),
            1
        )
        painter.setPen(border_pen)
        painter.drawRoundedRect(draw_rect, 6, 6)

        if self.edit_mode:
            draw_hud_corners(painter, draw_rect, QColor(0, 255, 136))

        painter.setPen(QColor(240, 246, 252))
        painter.setFont(QFont("sans-serif", self.font_size, QFont.Normal))
        text_box = self.rect().adjusted(MARGIN, 6, -MARGIN, -6)
        painter.drawText(text_box, Qt.AlignCenter | Qt.TextWordWrap, self.current_text)
