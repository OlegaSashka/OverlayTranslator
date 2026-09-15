import sys
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QPixmap, QColor, QPainter
from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QAction
from src.canvas import OverlayCanvas

def create_tray_icon():
    # Создаем простую пиксельную иконку для трея «T»
    pixmap = QPixmap(32, 32)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setBrush(QColor(0, 255, 136))
    painter.setPen(Qt.NoPen)
    painter.drawRoundedRect(0, 0, 32, 32, 6, 6)
    painter.setPen(QColor(0, 0, 0))
    painter.drawText(pixmap.rect(), Qt.AlignCenter, "TR")
    painter.end()
    return QIcon(pixmap)

def main():
    app = QApplication(sys.argv)
    # Окно не должно закрываться при скрытии диалогов
    app.setQuitOnLastWindowClosed(False)

    canvas = OverlayCanvas()
    canvas.fit_screen()
    canvas.show()

    # Настройка системного лотка (возле часов)
    tray = QSystemTrayIcon(create_tray_icon(), app)
    tray.setToolTip("Steam Deck Overlay Translator")

    menu = QMenu()

    # Тумблер режима настройки
    action_edit = QAction("Режим настройки (двигать рамки)", menu, checkable=True)
    action_edit.setChecked(True)
    action_edit.toggled.connect(canvas.set_edit_mode)
    menu.addAction(action_edit)

    # Тумблер показа перевода
    action_trans = QAction("Показывать перевод", menu, checkable=True)
    action_trans.setChecked(True)
    action_trans.toggled.connect(canvas.toggle_translation)
    menu.addAction(action_trans)

    menu.addSeparator()

    # Выход
    action_quit = QAction("Выход", menu)
    action_quit.triggered.connect(app.quit)
    menu.addAction(action_quit)

    tray.setContextMenu(menu)
    tray.show()

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
