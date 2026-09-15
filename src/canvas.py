from PyQt5.QtCore import Qt, QRect, QPoint, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QPen, QFont, QRegion
from PyQt5.QtWidgets import (
    QWidget, QApplication, QVBoxLayout, QHBoxLayout,
    QLabel, QSlider, QPushButton, QColorDialog
)
from src.config import load_config, save_config

MARGIN = 10

class SettingsWidget(QWidget):
    """Виджет настроек, встроенный в рамку"""
    def __init__(self, canvas):
        super().__init__(canvas)
        self.canvas = canvas
        self.styles = self.canvas.cfg.get("styles", {})

        self.setStyleSheet("""
            QLabel { color: #ECECEC; font-size: 11px; font-weight: bold; background: transparent; }
            QPushButton {
                background-color: rgba(255, 255, 255, 25);
                color: #FFFFFF;
                border: 1px solid rgba(255, 255, 255, 50);
                border-radius: 4px;
                padding: 4px;
                font-size: 11px;
            }
            QPushButton:hover { background-color: rgba(255, 255, 255, 45); }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 30, 10, 10)
        layout.setSpacing(6)

        layout.addWidget(QLabel("Прозрачность перевода:"))
        op_layout = QHBoxLayout()
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(10, 100)
        val = self.styles.get("overlay_opacity", 85)
        self.slider.setValue(val)
        self.slider_lbl = QLabel(f"{val}%")
        self.slider.valueChanged.connect(self.on_opacity_change)
        op_layout.addWidget(self.slider)
        op_layout.addWidget(self.slider_lbl)
        layout.addLayout(op_layout)

        btn_bg = QPushButton("Цвет фона перевода")
        btn_bg.clicked.connect(self.choose_bg)
        layout.addWidget(btn_bg)

        btn_border = QPushButton("Цвет рамки захвата")
        btn_border.clicked.connect(self.choose_border)
        layout.addWidget(btn_border)

        btn_done = QPushButton("Готово (скрыть рамки)")
        btn_done.setStyleSheet("background-color: #008855; font-weight: bold;")
        btn_done.clicked.connect(lambda: self.canvas.set_edit_mode(False))
        layout.addWidget(btn_done)

    def on_opacity_change(self, val):
        self.slider_lbl.setText(f"{val}%")
        self.styles["overlay_opacity"] = val
        self.save_styles()

    def choose_bg(self):
        color = QColorDialog.getColor(QColor(self.styles.get("overlay_bg_color", "#0F1219")), self)
        if color.isValid():
            self.styles["overlay_bg_color"] = color.name()
            self.save_styles()

    def choose_border(self):
        color = QColorDialog.getColor(QColor(self.styles.get("border_color", "#00FF88")), self)
        if color.isValid():
            self.styles["border_color"] = color.name()
            self.save_styles()

    def save_styles(self):
        self.canvas.cfg["styles"] = self.styles
        save_config(self.canvas.cfg)
        self.canvas.reload_styles()


class OverlayCanvas(QWidget):
    mode_changed = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        # Tool скрывает окно с панели задач KDE, Frameless убирает заголовки
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setMouseTracking(True)

        self.cfg = load_config()
        self.edit_mode = False
        self.current_text = "Ожидание текста..."

        cr = self.cfg.get("capture_rect", {"x": 240, "y": 550, "w": 800, "h": 120})
        self.cap_rect = QRect(cr["x"], cr["y"], cr["w"], cr["h"])

        tr = self.cfg.get("overlay_rect", {"x": 240, "y": 380, "w": 800, "h": 140})
        self.trans_rect = QRect(tr["x"], tr["y"], tr["w"], tr["h"])

        sr = self.cfg.get("settings_rect", {"x": 980, "y": 40, "w": 260, "h": 220})
        self.settings_rect = QRect(sr["x"], sr["y"], sr["w"], sr["h"])

        self.active_box = None
        self.active_edge = 0
        self.drag_start = QPoint()
        self.rect_start = QRect()

        self.settings_widget = SettingsWidget(self)

        self.reload_styles()
        self.set_edit_mode(True)

    def fit_screen(self):
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)
        self.settings_widget.setGeometry(self.settings_rect)
        self.apply_mask()

    def apply_mask(self):
        """Аппаратно пропускает клики сквозь прозрачные участки"""
        if self.edit_mode:
            # В режиме настройки доступен весь экран
            self.clearMask()
        else:
            # В игровом режиме кликабелен только прямоугольник с переводом (если нужно),
            # либо пустой QRegion(), чтобы мышь на 100% улетала в игру
            self.setMask(QRegion())

    def reload_styles(self):
        self.cfg = load_config()
        styles = self.cfg.get("styles", {})

        opacity_pct = styles.get("overlay_opacity", 85)
        alpha = int(255 * (opacity_pct / 100))

        bg_hex = styles.get("overlay_bg_color", "#0F1219")
        self.bg_qcolor = QColor(bg_hex)
        self.bg_qcolor.setAlpha(alpha)

        border_hex = styles.get("border_color", "#00FF88")
        self.accent_color = QColor(border_hex)
        self.update()

    def set_edit_mode(self, enabled: bool):
        self.edit_mode = enabled
        if enabled:
            self.settings_widget.show()
            self.settings_widget.raise_()
        else:
            self.settings_widget.hide()
            self.setCursor(Qt.ArrowCursor)
            self.save_geometry()

        self.apply_mask()
        self.mode_changed.emit(enabled)
        self.update()

    def set_translation(self, text: str):
        self.current_text = text
        self.update()

    def save_geometry(self):
        self.cfg["capture_rect"] = {
            "x": self.cap_rect.x(), "y": self.cap_rect.y(),
            "w": self.cap_rect.width(), "h": self.cap_rect.height()
        }
        self.cfg["overlay_rect"] = {
            "x": self.trans_rect.x(), "y": self.trans_rect.y(),
            "w": self.trans_rect.width(), "h": self.trans_rect.height()
        }
        self.cfg["settings_rect"] = {
            "x": self.settings_rect.x(), "y": self.settings_rect.y(),
            "w": self.settings_rect.width(), "h": self.settings_rect.height()
        }
        save_config(self.cfg)

    def get_edge(self, rect: QRect, pos: QPoint):
        if not rect.contains(pos): return 0
        edge = 0
        if pos.x() <= rect.left() + MARGIN: edge |= 1
        elif pos.x() >= rect.right() - MARGIN: edge |= 2
        if pos.y() <= rect.top() + MARGIN: edge |= 4
        elif pos.y() >= rect.bottom() - MARGIN: edge |= 8
        return edge

    def mousePressEvent(self, event):
        if not self.edit_mode or event.button() != Qt.LeftButton:
            return

        pos = event.pos()
        boxes = [("settings", self.settings_rect), ("trans", self.trans_rect), ("cap", self.cap_rect)]
        for box_name, rect in boxes:
            if rect.contains(pos):
                self.active_box = box_name
                self.active_edge = 0 if box_name == "settings" else self.get_edge(rect, pos)
                self.drag_start = event.globalPos()
                self.rect_start = QRect(rect)
                event.accept()
                return

    def mouseMoveEvent(self, event):
        if not self.edit_mode:
            return

        pos = event.pos()
        if event.buttons() & Qt.LeftButton and self.active_box:
            delta = event.globalPos() - self.drag_start
            rect = QRect(self.rect_start)
            sw, sh = self.width(), self.height()

            if self.active_edge == 0:
                nx = max(0, min(rect.x() + delta.x(), sw - rect.width()))
                ny = max(0, min(rect.y() + delta.y(), sh - rect.height()))
                rect.moveTo(nx, ny)
            else:
                if self.active_edge & 1: rect.setLeft(min(rect.right() - 100, max(0, rect.left() + delta.x())))
                if self.active_edge & 2: rect.setRight(max(rect.left() + 100, min(sw, rect.right() + delta.x())))
                if self.active_edge & 4: rect.setTop(min(rect.bottom() - 40, max(0, rect.top() + delta.y())))
                if self.active_edge & 8: rect.setBottom(max(rect.top() + 40, min(sh, rect.bottom() + delta.y())))

            if self.active_box == "cap": self.cap_rect = rect
            elif self.active_box == "trans": self.trans_rect = rect
            elif self.active_box == "settings":
                self.settings_rect = rect
                self.settings_widget.setGeometry(self.settings_rect)

            self.update()
            event.accept()
        else:
            edge = self.get_edge(self.trans_rect, pos) or self.get_edge(self.cap_rect, pos)
            if edge in (1 | 4, 2 | 8): self.setCursor(Qt.SizeFDiagCursor)
            elif edge in (2 | 4, 1 | 8): self.setCursor(Qt.SizeBDiagCursor)
            elif edge in (1, 2): self.setCursor(Qt.SizeHorCursor)
            elif edge in (4, 8): self.setCursor(Qt.SizeVerCursor)
            elif self.cap_rect.contains(pos) or self.trans_rect.contains(pos) or self.settings_rect.contains(pos):
                self.setCursor(Qt.SizeAllCursor)
            else:
                self.setCursor(Qt.ArrowCursor)

    def mouseReleaseEvent(self, event):
        if self.edit_mode and self.active_box:
            self.active_box = None
            self.active_edge = 0
            self.save_geometry()
            event.accept()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 1. Рамка захвата (только в режиме настройки)
        if self.edit_mode:
            accent_fill = QColor(self.accent_color)
            accent_fill.setAlpha(35)
            painter.setPen(QPen(self.accent_color, 2, Qt.DashLine))
            painter.setBrush(accent_fill)
            painter.drawRoundedRect(self.cap_rect, 6, 6)
            painter.setFont(QFont("sans-serif", 10, QFont.Bold))
            painter.setPen(self.accent_color)
            painter.drawText(self.cap_rect, Qt.AlignCenter, "[ Область захвата субтитров ]")

        # 2. Карточка перевода
        border_c = QColor(255, 255, 255, 80 if self.edit_mode else 30)
        painter.setPen(QPen(border_c, 1))
        painter.setBrush(self.bg_qcolor)
        painter.drawRoundedRect(self.trans_rect, 8, 8)

        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("sans-serif", 15, QFont.Bold))
        inner = self.trans_rect.adjusted(14, 10, -14, -10)
        painter.drawText(inner, Qt.AlignCenter | Qt.TextWordWrap, self.current_text)

        # 3. Фон и заголовок настроек
        if self.edit_mode:
            painter.setPen(QPen(QColor(255, 255, 255, 60), 1))
            painter.setBrush(QColor(20, 24, 33, 245))
            painter.drawRoundedRect(self.settings_rect, 8, 8)

            painter.setPen(QColor(0, 255, 136))
            painter.setFont(QFont("sans-serif", 9, QFont.Bold))
            painter.drawText(self.settings_rect.adjusted(10, 8, -10, 0), Qt.AlignTop | Qt.AlignLeft, "≡ Настройки (перетащить)")
