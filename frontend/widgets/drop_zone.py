from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QLabel
from frontend.theme.theme_manager import theme_manager


class DropZone(QLabel):
    file_dropped = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setText("Drag & Drop Posture Image Here\n(PNG, JPG, JPEG)")
        self.setAlignment(Qt.AlignCenter)
        self.apply_theme()

        self.setAcceptDrops(True)

    def apply_theme(self):
        colors = theme_manager.get_colors()
        self.setStyleSheet(f"""
            QLabel {{
                border: 2px dashed {colors['border']};
                border-radius: 10px;
                font-size: 15px;
                color: {colors['text_secondary']};
                background-color: {colors['bg_dropzone']};
                padding: 20px;
            }}
            QLabel:hover {{
                border-color: {colors['border_accent']};
                background-color: {colors['bg_dropzone_hover']};
            }}
        """)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.lower().endswith(('.png', '.jpg', '.jpeg')):
                self.file_dropped.emit(path)