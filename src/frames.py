from PyQt5.QtCore import Qt, QPoint, QRect
from PyQt5.QtGui import QPainter, QColor, QPen, QFont
from PyQt5.QtWidgets import QWidget, QApplication
from src.config import load_config, save_config

MARGIN = 8  # Ширина зоны у краёв для ресайза


class ResizableWindow(QWidget):
    def __init__(self, config_key: str, min_w=150, min_h=50):
        super().__init__()
        self.config_key = config_key
        self.setMinimumSize(min_w, min_h)

        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)

        self.edit_mode = True
        self.restore_geometry()

    def restore_geometry(self):
        cfg = load_config()
        geo = cfg.get(self.config_key, {})

        default_x = 240
        default_y = 550 if self.config_key == "capture_rect" else 380
        default_w = 800
        default_h = 120 if self.config_key == "capture_rect" else 140

        x = geo.get("x", geo.get("left", default_x))
        y = geo.get("y", geo.get("top", default_y))
        w = geo.get("w", geo.get("width", default_w))
        h = geo.get("h", geo.get("height", default_h))

        self.setGeometry(x, y, w, h)
        self.clamp_to_screen()

    def save_current_geometry(self):
        cfg = load_config()
        geo = self.geometry()
        cfg[self.config_key] = {
            "x": geo.x(), "y": geo.y(),
            "w": geo.width(), "h": geo.height()
        }
        save_config(cfg)

    def clamp_to_screen(self):
        screen = QApplication.primaryScreen().geometry()
        nx = max(0, min(self.x(), screen.width() - self.width()))
        ny = max(0, min(self.y(), screen.height() - self.height()))
        if nx != self.x() or ny != self.y():
            self.move(nx, ny)

    def get_edge(self, pos: QPoint) -> Qt.Edges:
        edges = Qt.Edges()
        if pos.x() <= MARGIN:
            edges |= Qt.LeftEdge
        elif pos.x() >= self.width() - MARGIN:
            edges |= Qt.RightEdge
        if pos.y() <= MARGIN:
            edges |= Qt.TopEdge
        elif pos.y() >= self.height() - MARGIN:
            edges |= Qt.BottomEdge
        return edges

    def update_cursor_shape(self, edges: Qt.Edges):
        if not self.edit_mode:
            self.setCursor(Qt.ArrowCursor)
            return

        if (edges & (Qt.TopEdge | Qt.LeftEdge)) or (edges & (Qt.BottomEdge | Qt.RightEdge)):
            self.setCursor(Qt.SizeFDiagCursor)
        elif (edges & (Qt.TopEdge | Qt.RightEdge)) or (edges & (Qt.BottomEdge | Qt.LeftEdge)):
            self.setCursor(Qt.SizeBDiagCursor)
        elif edges & (Qt.LeftEdge | Qt.RightEdge):
            self.setCursor(Qt.SizeHorCursor)
        elif edges & (Qt.TopEdge | Qt.BottomEdge):
            self.setCursor(Qt.SizeVerCursor)
        else:
            self.setCursor(Qt.OpenHandCursor)

    def mousePressEvent(self, event):
        if not self.edit_mode or event.button() != Qt.LeftButton:
            return

        edges = self.get_edge(event.pos())
        if edges:
            self.windowHandle().startSystemResize(edges)
        else:
            self.windowHandle().startSystemMove()
        event.accept()

    def mouseMoveEvent(self, event):
        if self.edit_mode:
            self.update_cursor_shape(self.get_edge(event.pos()))

    def moveEvent(self, event):
        super().moveEvent(event)
        if self.edit_mode:
            self.save_current_geometry()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.edit_mode:
            self.save_current_geometry()

    def keyPressEvent(self, event):
        if not self.edit_mode:
            return

        step = 10 if (event.modifiers() & Qt.ShiftModifier) else 1
        x, y = self.x(), self.y()

        if event.key() == Qt.Key_Left:    x -= step
        elif event.key() == Qt.Key_Right: x += step
        elif event.key() == Qt.Key_Up:    y -= step
        elif event.key() == Qt.Key_Down:  y += step
        else:
            super().keyPressEvent(event)
            return

        screen = QApplication.primaryScreen().geometry()
        clamped_x = max(0, min(x, screen.width() - self.width()))
        clamped_y = max(0, min(y, screen.height() - self.height()))

        self.move(clamped_x, clamped_y)
        event.accept()

class CaptureFrame(ResizableWindow):
    """Зеленая рамка захвата OCR"""
    def __init__(self):
        super().__init__("capture_rect", min_w=120, min_h=40)
        self.border_color = QColor("#00FF88")

    def reload_style(self):
        cfg = load_config()
        self.border_color = QColor(cfg.get("styles", {}).get("border_color", "#00FF88"))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        draw_rect = self.rect().adjusted(1, 1, -1, -1)

        fill_color = QColor(self.border_color)
        fill_color.setAlpha(25)

        painter.setPen(QPen(self.border_color, 1.5, Qt.DashLine))
        painter.setBrush(fill_color)
        painter.drawRoundedRect(draw_rect, 6, 6)

        painter.setPen(self.border_color)
        painter.setFont(QFont("sans-serif", 10, QFont.Bold))
        painter.drawText(self.rect(), Qt.AlignCenter, "[ Зона захвата текста ]")


class TranslationFrame(ResizableWindow):
    """Плавающая карточка перевода"""
    def __init__(self):
        super().__init__("overlay_rect", min_w=180, min_h=50)
        self.current_text = "Ожидание текста..."
        self.bg_color = QColor(15, 18, 25, 215)
        self.reload_style()

    def set_edit_mode(self, enabled: bool):
        self.edit_mode = enabled
        self.setAttribute(Qt.WA_TransparentForMouseEvents, not enabled)
        if not enabled:
            self.setCursor(Qt.ArrowCursor)
            self.save_current_geometry()
        self.update()

    def reload_style(self):
        cfg = load_config()
        styles = cfg.get("styles", {})
        alpha = int(255 * (styles.get("overlay_opacity", 85) / 100))
        self.bg_color = QColor(styles.get("overlay_bg_color", "#0F1219"))
        self.bg_color.setAlpha(alpha)
        self.update()

    def set_translation(self, text: str):
        self.current_text = text
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        draw_rect = self.rect().adjusted(1, 1, -1, -1)

        border_pen = QPen(QColor(255, 255, 255, 75 if self.edit_mode else 30), 1)
        painter.setPen(border_pen)
        painter.setBrush(self.bg_color)
        painter.drawRoundedRect(draw_rect, 8, 8)

        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("sans-serif", 14, QFont.Bold))
        text_area = self.rect().adjusted(MARGIN, 6, -MARGIN, -6)
        painter.drawText(text_area, Qt.AlignCenter | Qt.TextWordWrap, self.current_text)
