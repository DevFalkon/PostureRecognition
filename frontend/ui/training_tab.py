from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QListWidget
)
from frontend.ui.helpers import bgr_to_pixmap


class DropZoneLabel(QLabel):
    file_dropped = Signal(str)

    def __init__(self):
        super().__init__()
        self.setText("Drag & Drop Posture Image Here\n(PNG, JPG, JPEG)")
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("""
            QLabel {
                border: 2px dashed #aaa; border-radius: 10px;
                font-size: 15px; color: #555; background-color: #f9f9f9; padding: 30px;
            }
            QLabel:hover { border-color: #007acc; background-color: #f0f8ff; }
        """)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.lower().endswith(('.png', '.jpg', '.jpeg')):
                self.file_dropped.emit(path)


class TrainingTab(QWidget):
    request_process_image = Signal(str)  # Emits image file_path to backend

    def __init__(self, pose_library):
        super().__init__()
        self.pose_library = pose_library

        layout = QVBoxLayout()
        self.drop_zone = DropZoneLabel()
        self.drop_zone.file_dropped.connect(self.request_process_image.emit)

        self.status_label = QLabel("No poses loaded yet.")
        self.status_label.setAlignment(Qt.AlignCenter)

        content_layout = QHBoxLayout()
        left_box = QVBoxLayout()
        left_box.addWidget(QLabel("Loaded Poses:"))
        self.pose_list_widget = QListWidget()
        left_box.addWidget(self.pose_list_widget)

        right_box = QVBoxLayout()
        right_box.addWidget(QLabel("Detected Skeleton Preview:"))
        self.preview_label = QLabel("Upload an image to see bone overlay preview")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet("border: 1px solid #ccc; background-color: #1e1e1e; color: #888;")
        self.preview_label.setMinimumSize(320, 240)
        right_box.addWidget(self.preview_label)

        content_layout.addLayout(left_box, stretch=1)
        content_layout.addLayout(right_box, stretch=2)

        layout.addWidget(self.drop_zone)
        layout.addWidget(self.status_label)
        layout.addLayout(content_layout)
        self.setLayout(layout)

    @Slot(object, object, str)
    def on_image_processed(self, annotated_img, angles, file_path):
        if annotated_img is None:
            self.status_label.setText("⚠️ No posture detected in that image! Try another one.")
            return

        pixmap = bgr_to_pixmap(annotated_img, self.preview_label.width(), self.preview_label.height())
        self.preview_label.setPixmap(pixmap)

        pose_name = f"Pose_{len(self.pose_library) + 1}"
        self.pose_library.append({"name": pose_name, "angles": angles, "path": file_path})
        self.pose_list_widget.addItem(f"{pose_name} ({file_path.split('/')[-1]})")
        self.status_label.setText(f"✓ Successfully processed and added {pose_name}!")