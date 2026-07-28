import random
import cv2
from PySide6.QtCore import QTimer, Qt, Signal, Slot
from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QComboBox, QPushButton
)
from frontend.ui.helpers import bgr_to_pixmap, get_available_cameras


class GameTab(QWidget):
    request_frame_process = Signal(object, object)  # Emits (bgr_frame, target_angles)

    def __init__(self, pose_library):
        super().__init__()
        self.pose_library = pose_library
        self.cap = None
        self.score = 0
        self.current_target = None
        self.match_cooldown = False
        self.current_camera_index = 0
        self.cameras_populated = False

        layout = QVBoxLayout()
        top_bar = QHBoxLayout()

        self.score_label = QLabel("Score: 0")
        self.score_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #2e7d32;")
        
        self.target_name_label = QLabel("Target: Add poses in Training tab!")
        self.target_name_label.setStyleSheet("font-size: 14px;")

        self.camera_selector = QComboBox()
        self.camera_selector.currentIndexChanged.connect(self.change_camera)

        self.next_btn = QPushButton("Next Pose / Start")
        self.next_btn.clicked.connect(self.pick_random_pose)

        top_bar.addWidget(self.score_label)
        top_bar.addWidget(self.target_name_label)
        top_bar.addWidget(QLabel("Camera:"))
        top_bar.addWidget(self.camera_selector)
        top_bar.addWidget(self.next_btn)

        self.camera_label = QLabel()
        self.camera_label.setAlignment(Qt.AlignCenter)

        layout.addLayout(top_bar)
        layout.addWidget(self.camera_label)
        self.setLayout(layout)

        self.timer = QTimer()
        self.timer.timeout.connect(self.read_camera_frame)

    def populate_cameras(self):
        if self.cameras_populated:
            return
        self.camera_selector.blockSignals(True)
        for idx, name in get_available_cameras():
            self.camera_selector.addItem(f"📷 {name}", userData=idx)
        self.camera_selector.blockSignals(False)
        self.cameras_populated = True

    def change_camera(self, combo_index):
        idx = self.camera_selector.itemData(combo_index)
        if idx is not None and idx != self.current_camera_index:
            self.current_camera_index = idx
            if self.cap and self.cap.isOpened():
                self.cap.release()
                self.cap = None
            if self.timer.isActive():
                self.cap = cv2.VideoCapture(self.current_camera_index)

    def start_camera(self):
        self.populate_cameras()
        if self.cap is None or not self.cap.isOpened():
            self.cap = cv2.VideoCapture(self.current_camera_index)
        if not self.timer.isActive():
            self.timer.start(30)

    def stop_camera(self):
        if self.timer.isActive():
            self.timer.stop()
        if self.cap and self.cap.isOpened():
            self.cap.release()
            self.cap = None

    def pick_random_pose(self):
        if not self.pose_library:
            self.target_name_label.setText("Target: Add poses in Training tab first!")
            return
        self.current_target = random.choice(self.pose_library)
        self.target_name_label.setText(f"Target: {self.current_target['name']}")
        self.match_cooldown = False

    def read_camera_frame(self):
        if self.cap is None or not self.cap.isOpened():
            return
        ret, frame = self.cap.read()
        if not ret or frame is None:
            return

        target_angles = self.current_target["angles"] if self.current_target else None
        self.request_frame_process.emit(frame, target_angles)

    @Slot(object, bool)
    def on_frame_processed(self, processed_frame, is_match):
        if is_match:
            cv2.putText(processed_frame, "MATCH DETECTED!", (50, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)
            if not self.match_cooldown:
                self.score += 1
                self.score_label.setText(f"Score: {self.score}")
                self.match_cooldown = True
                QTimer.singleShot(1500, self.pick_random_pose)

        pixmap = bgr_to_pixmap(processed_frame, processed_frame.shape[1], processed_frame.shape[0])
        self.camera_label.setPixmap(pixmap)