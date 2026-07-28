import os
import cv2
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QListWidget, QSplitter
)
from frontend.ui.helpers import bgr_to_pixmap
from frontend.widgets.drop_zone import DropZone
from frontend.widgets.widget_formatter import create_bordered_section

class TrainingTab(QWidget):
    request_process_image = Signal(str)

    def __init__(self, storage_service: object):
        super().__init__()
        # Injected backend service
        self.storage_service = storage_service
        self.pose_library = storage_service.pose_library

        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # 1. Drop Zone Widget
        self.drop_zone = DropZone()
        self.drop_zone.file_dropped.connect(self.request_process_image.emit)

        # 2. Status Indicator Label
        self.status_label = QLabel("No poses loaded yet.")
        self.status_label.setAlignment(Qt.AlignCenter)

        # 3. Horizontal Splitter Section
        self.splitter = QSplitter(Qt.Horizontal)

        # Left Pane — Loaded Poses
        self.pose_list_widget = QListWidget()
        self.pose_list_widget.setStyleSheet("border: none; background-color: transparent;")
        self.pose_list_widget.currentRowChanged.connect(self.on_pose_selected)
        left_section = create_bordered_section("Loaded Poses:", self.pose_list_widget)

        # Right Pane — Skeleton Preview
        self.preview_label = QLabel("Upload an image to see bone overlay preview")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet("background-color: #1e1e1e; color: #888; border-radius: 4px;")
        self.preview_label.setMinimumSize(320, 240)
        right_section = create_bordered_section("Detected Skeleton Preview:", self.preview_label)

        # Build Splitter Layout
        self.splitter.addWidget(left_section)
        self.splitter.addWidget(right_section)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 2)

        # Main Layout Assembly
        layout.addWidget(self.drop_zone)
        layout.addWidget(self.status_label)
        layout.addWidget(self.splitter, stretch=1)

        self.setLayout(layout)

        # Hydrate initial list from storage service
        self._load_existing_poses()

    def _load_existing_poses(self):
        """Requests existing stored poses from StorageService and updates UI."""
        loaded_entries = self.storage_service.load_existing_poses()
        if not loaded_entries:
            return

        for entry in loaded_entries:
            self.pose_list_widget.addItem(entry["display_name"])

        count = len(loaded_entries)
        self.status_label.setText(f"✓ Loaded {count} existing pose{'s' if count > 1 else ''} from disk")
        self.pose_list_widget.setCurrentRow(0)

    @Slot(int)
    def on_pose_selected(self, index: int):
        """Displays the selected pose's preview image."""
        if index < 0 or index >= len(self.pose_library):
            return

        pose_data = self.pose_library[index]
        image_path = pose_data.get("path")

        if image_path and os.path.exists(image_path):
            annotated_img = cv2.imread(image_path)
            if annotated_img is not None:
                pixmap = bgr_to_pixmap(
                    annotated_img,
                    self.preview_label.width(),
                    self.preview_label.height()
                )
                self.preview_label.setPixmap(pixmap)

    @Slot(object, object, str)
    def on_image_processed(self, annotated_img, angles, file_path: str):
        """Receives processed output from PoseService and delegates saving to StorageService."""
        if annotated_img is None:
            self.status_label.setText("⚠️ No posture detected in that image! Try another one.")
            return

        # Delegate disk writing and record registration to StorageService
        entry = self.storage_service.save_pose_image(annotated_img, angles, file_path)

        # Update UI View
        self.pose_list_widget.addItem(entry["display_name"])
        self.pose_list_widget.setCurrentRow(len(self.pose_library) - 1)
        self.status_label.setText(f"✓ Saved {entry['saved_filename']} as {entry['name']}!")