from PyQt5.QtCore import Qt, QRect, QPoint
from PyQt5.QtGui import QPainter, QColor, QPen, QFont
from PyQt5.QtWidgets import QWidget, QApplication
from src.config import load_config, save_config

MARGIN = 10

class OverlayCanvas(QWidget):
    def __init__(self):
        super().__init__()
        # Полноэкранный прозрачный оверлей без системных рамок
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint |
            Qt.FramelessWindowHint |
            Qt.SubWindow
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setMouseTracking(True)

        self.cfg = load_config()
        self.edit_mode = False
        self.show_translation = self.cfg.get("show_overlay", True)
        self.current_text = "Ожидание текста..."

        # Загрузка геометрии блоков
        cr = self.cfg["capture_rect"]
        self.cap_rect = QRect(cr["x"], cr["y"], cr["w"], cr["h"])

        tr = self.cfg["overlay_rect"]
        self.trans_rect = QRect(tr["x"], tr["y"], tr["w"], tr["h"])

        # Состояния мыши
        self.active_box = None
        self.active_edge = 0
        self.drag_start = QPoint()
        self.rect_start = QRect()

        self.set_edit_mode(True)  # При первом старте открываем в режиме настройки

    def fit_screen(self):
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)

    def set_edit_mode(self, enabled: bool):
        self.edit_mode = enabled
        # Ключевой флаг: если НЕ режим настройки — клики уходят насквозь в игру
        self.setAttribute(Qt.WA_TransparentForMouseEvents, not enabled)
        if not enabled:
            self.setCursor(Qt.ArrowCursor)
            self.save_geometry()
        self.update()

    def toggle_translation(self, visible: bool):
        self.show_translation = visible
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
        save_config(self.cfg)

    def get_edge(self, rect: QRect, pos: QPoint):
        if not rect.contains(pos):
            return 0
        edge = 0
        if pos.x() <= rect.left() + MARGIN: edge |= 1  # Left
        elif pos.x() >= rect.right() - MARGIN: edge |= 2  # Right
        if pos.y() <= rect.top() + MARGIN: edge |= 4   # Top
        elif pos.y() >= rect.bottom() - MARGIN: edge |= 8  # Bottom
        return edge

    def mousePressEvent(self, event):
        if not self.edit_mode or event.button() != Qt.LeftButton:
            return

        pos = event.pos()
        for box_name, rect in [("trans", self.trans_rect), ("cap", self.cap_rect)]:
            if rect.contains(pos):
                self.active_box = box_name
                self.active_edge = self.get_edge(rect, pos)
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
                # Перемещение блока с ограничением экрана
                nx = max(0, min(rect.x() + delta.x(), sw - rect.width()))
                ny = max(0, min(rect.y() + delta.y(), sh - rect.height()))
                rect.moveTo(nx, ny)
            else:
                # Изменение размера
                if self.active_edge & 1: rect.setLeft(min(rect.right() - 100, max(0, rect.left() + delta.x())))
                if self.active_edge & 2: rect.setRight(max(rect.left() + 100, min(sw, rect.right() + delta.x())))
                if self.active_edge & 4: rect.setTop(min(rect.bottom() - 40, max(0, rect.top() + delta.y())))
                if self.active_edge & 8: rect.setBottom(max(rect.top() + 40, min(sh, rect.bottom() + delta.y())))

            if self.active_box == "cap":
                self.cap_rect = rect
            else:
                self.trans_rect = rect
            self.update()
            event.accept()
        else:
            # Смена курсора
            edge = self.get_edge(self.trans_rect, pos) or self.get_edge(self.cap_rect, pos)
            if edge in (1 | 4, 2 | 8): self.setCursor(Qt.SizeFDiagCursor)
            elif edge in (2 | 4, 1 | 8): self.setCursor(Qt.SizeBDiagCursor)
            elif edge in (1, 2): self.setCursor(Qt.SizeHorCursor)
            elif edge in (4, 8): self.setCursor(Qt.SizeVerCursor)
            elif self.cap_rect.contains(pos) or self.trans_rect.contains(pos):
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

        # 1. Рамка захвата OCR (видна ТОЛЬКО в режиме настройки)
        if self.edit_mode:
            painter.setPen(QPen(QColor(0, 255, 136, 220), 2, Qt.DashLine))
            painter.setBrush(QColor(0, 255, 136, 30))
            painter.drawRoundedRect(self.cap_rect, 6, 6)
            painter.setFont(QFont("sans-serif", 10, QFont.Bold))
            painter.setPen(QColor(0, 255, 136))
            painter.drawText(self.cap_rect, Qt.AlignCenter, "[ Область захвата субтитров ]")

        # 2. Карточка перевода
        if self.show_translation:
            painter.setPen(QPen(QColor(255, 255, 255, 80 if self.edit_mode else 30), 1))
            painter.setBrush(QColor(15, 18, 25, 220))
            painter.drawRoundedRect(self.trans_rect, 8, 8)

            painter.setPen(QColor(255, 255, 255))
            painter.setFont(QFont("sans-serif", 15, QFont.Bold))
            inner = self.trans_rect.adjusted(14, 10, -14, -10)
            painter.drawText(inner, Qt.AlignCenter | Qt.TextWordWrap, self.current_text)

        # 3. Подсказка сверху в режиме настройки
        if self.edit_mode:
            info_rect = QRect(self.width() // 2 - 200, 15, 400, 42)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(0, 0, 0, 200))
            painter.drawRoundedRect(info_rect, 6, 6)
            painter.setPen(QColor(255, 255, 255))
            painter.setFont(QFont("sans-serif", 10))
            painter.drawText(
                info_rect, Qt.AlignCenter,
                "РЕЖИМ НАСТРОЙКИ: перетащите рамки.\nОтключите режим в трее возле часов."
            )
