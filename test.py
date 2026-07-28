import sys
import cv2
import random
import numpy as np
import mediapipe as mp

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QImage, QPixmap, QDragEnterEvent, QDropEvent
from PySide6.QtMultimedia import QMediaDevices
from PySide6.QtWidgets import (
    QApplication, QLabel, QMainWindow, QVBoxLayout, QHBoxLayout, 
    QWidget, QTabWidget, QPushButton, QListWidget, QComboBox
)

# --- MATH HELPER ---
def calculate_angle(a, b, c):
    a = np.array([a.x, a.y])
    b = np.array([b.x, b.y])
    c = np.array([c.x, c.y])

    radians = np.arctan2(c[1] - b[1], c[0] - b[0]) - np.arctan2(a[1] - b[1], a[0] - b[0])
    angle = np.abs(radians * 180.0 / np.pi)
    if angle > 180.0:
        angle = 360 - angle
    return angle

# --- CAMERA DISCOVERY ---
def get_available_cameras():
    cameras = []
    try:
        devices = QMediaDevices.videoInputs()
        for i, dev in enumerate(devices):
            name = dev.description() if dev.description() else f"Camera {i}"
            cameras.append((i, name))
    except Exception:
        pass
    
    if not cameras:
        cameras.append((0, "Camera 0"))
    return cameras


# --- DRAG AND DROP ZONE ---
class DropZoneLabel(QLabel):
    def __init__(self, parent_tab):
        super().__init__()
        self.parent_tab = parent_tab
        self.setText("Drag & Drop Posture Image Here\n(PNG, JPG, JPEG)")
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("""
            QLabel {
                border: 2px dashed #aaa;
                border-radius: 10px;
                font-size: 15px;
                color: #555;
                background-color: #f9f9f9;
                padding: 30px;
            }
            QLabel:hover {
                border-color: #007acc;
                background-color: #f0f8ff;
            }
        """)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.lower().endswith(('.png', '.jpg', '.jpeg')):
                self.parent_tab.process_and_add_pose(file_path)


# --- TAB 1: TRAINING TAB WITH SKELETON PREVIEW ---
class TrainingTab(QWidget):
    def __init__(self, get_static_detector_fn, pose_library, update_callback):
        super().__init__()
        self.get_static_detector = get_static_detector_fn
        self.pose_library = pose_library
        self.update_callback = update_callback
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_pose = mp.solutions.pose

        main_layout = QVBoxLayout()
        self.drop_zone = DropZoneLabel(self)
        self.status_label = QLabel("No poses loaded yet.")
        self.status_label.setAlignment(Qt.AlignCenter)

        content_layout = QHBoxLayout()

        # Left Column: Loaded Pose List
        left_box = QVBoxLayout()
        left_box.addWidget(QLabel("Loaded Poses:"))
        self.pose_list_widget = QListWidget()
        left_box.addWidget(self.pose_list_widget)

        # Right Column: Visual Preview Box
        right_box = QVBoxLayout()
        right_box.addWidget(QLabel("Detected Skeleton Preview:"))
        self.preview_label = QLabel("Upload an image to see bone overlay preview")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet("border: 1px solid #ccc; background-color: #1e1e1e; color: #888;")
        self.preview_label.setMinimumSize(320, 240)
        right_box.addWidget(self.preview_label)

        content_layout.addLayout(left_box, stretch=1)
        content_layout.addLayout(right_box, stretch=2)

        main_layout.addWidget(self.drop_zone)
        main_layout.addWidget(self.status_label)
        main_layout.addLayout(content_layout)
        self.setLayout(main_layout)

    def process_and_add_pose(self, file_path):
        img = cv2.imread(file_path)
        if img is None:
            self.status_label.setText("Error reading image!")
            return

        rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # Use static mode detector so image state doesn't leak into subsequent uploads
        detector = self.get_static_detector()
        results = detector.process(rgb_img)

        if not results.pose_landmarks:
            self.status_label.setText("⚠️ No posture detected in that image! Try another one.")
            return

        # Draw skeleton lines on image preview
        annotated_img = img.copy()
        self.mp_drawing.draw_landmarks(
            annotated_img, results.pose_landmarks, self.mp_pose.POSE_CONNECTIONS
        )

        h, w, ch = annotated_img.shape
        bytes_per_line = ch * w
        q_img = QImage(annotated_img.data, w, h, bytes_per_line, QImage.Format_BGR888)
        pixmap = QPixmap.fromImage(q_img).scaled(
            self.preview_label.width(), self.preview_label.height(), 
            Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.preview_label.setPixmap(pixmap)

        # Calculate pose angles
        lm = results.pose_landmarks.landmark
        mp_p = self.mp_pose.PoseLandmark

        angles = {
            "l_elbow": calculate_angle(lm[mp_p.LEFT_SHOULDER], lm[mp_p.LEFT_ELBOW], lm[mp_p.LEFT_WRIST]),
            "r_elbow": calculate_angle(lm[mp_p.RIGHT_SHOULDER], lm[mp_p.RIGHT_ELBOW], lm[mp_p.RIGHT_WRIST]),
            "l_knee": calculate_angle(lm[mp_p.LEFT_HIP], lm[mp_p.LEFT_KNEE], lm[mp_p.LEFT_ANKLE]),
            "r_knee": calculate_angle(lm[mp_p.RIGHT_HIP], lm[mp_p.RIGHT_KNEE], lm[mp_p.RIGHT_ANKLE]),
        }

        pose_name = f"Pose_{len(self.pose_library) + 1}"
        self.pose_library.append({"name": pose_name, "angles": angles, "path": file_path})
        
        self.pose_list_widget.addItem(f"{pose_name} ({file_path.split('/')[-1]})")
        self.status_label.setText(f"✓ Successfully processed and added {pose_name}!")
        self.update_callback()


# --- TAB 2: GAME TAB ---
class GameTab(QWidget):
    def __init__(self, get_stream_detector_fn, pose_library):
        super().__init__()
        self.get_stream_detector = get_stream_detector_fn
        self.pose_library = pose_library
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_pose = mp.solutions.pose

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
        self.timer.timeout.connect(self.update_game_frame)

    def populate_cameras(self):
        if self.cameras_populated:
            return
        available = get_available_cameras()
        self.camera_selector.blockSignals(True)
        for idx, name in available:
            self.camera_selector.addItem(f"📷 {name}", userData=idx)
        self.camera_selector.blockSignals(False)
        self.cameras_populated = True

    def change_camera(self, combo_index):
        new_cam_idx = self.camera_selector.itemData(combo_index)
        if new_cam_idx is not None and new_cam_idx != self.current_camera_index:
            self.current_camera_index = new_cam_idx
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

    def update_game_frame(self):
        if self.cap is None or not self.cap.isOpened():
            return

        ret, frame = self.cap.read()
        if not ret or frame is None:
            return

        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        detector = self.get_stream_detector()
        results = detector.process(rgb_frame)

        if results.pose_landmarks:
            self.mp_drawing.draw_landmarks(
                frame, results.pose_landmarks, self.mp_pose.POSE_CONNECTIONS
            )

            if self.current_target:
                lm = results.pose_landmarks.landmark
                mp_p = self.mp_pose.PoseLandmark

                curr_angles = {
                    "l_elbow": calculate_angle(lm[mp_p.LEFT_SHOULDER], lm[mp_p.LEFT_ELBOW], lm[mp_p.LEFT_WRIST]),
                    "r_elbow": calculate_angle(lm[mp_p.RIGHT_SHOULDER], lm[mp_p.RIGHT_ELBOW], lm[mp_p.RIGHT_WRIST]),
                    "l_knee": calculate_angle(lm[mp_p.LEFT_HIP], lm[mp_p.LEFT_KNEE], lm[mp_p.LEFT_ANKLE]),
                    "r_knee": calculate_angle(lm[mp_p.RIGHT_HIP], lm[mp_p.RIGHT_KNEE], lm[mp_p.RIGHT_ANKLE]),
                }

                target_angles = self.current_target["angles"]
                tolerance = 20.0
                
                is_match = all(
                    abs(curr_angles[joint] - target_angles[joint]) < tolerance
                    for joint in target_angles
                )

                if is_match:
                    cv2.putText(frame, "MATCH DETECTED!", (50, 60), 
                                cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)
                    if not self.match_cooldown:
                        self.score += 1
                        self.score_label.setText(f"Score: {self.score}")
                        self.match_cooldown = True
                        QTimer.singleShot(1500, self.pick_random_pose)

        h, w, ch = frame.shape
        bytes_per_line = ch * w
        q_img = QImage(frame.data, w, h, bytes_per_line, QImage.Format_BGR888)
        self.camera_label.setPixmap(QPixmap.fromImage(q_img))


# --- MAIN APPLICATION WINDOW ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pose Matching Game")
        self.resize(1000, 750)

        self.pose_library = []
        self._static_pose_detector = None
        self._stream_pose_detector = None
        self.mp_pose = mp.solutions.pose

        self.tabs = QTabWidget()
        self.training_tab = TrainingTab(self.get_static_detector, self.pose_library, self.on_poses_updated)
        self.game_tab = GameTab(self.get_stream_detector, self.pose_library)

        self.tabs.addTab(self.training_tab, "1. Training (Upload Poses)")
        self.tabs.addTab(self.game_tab, "2. Game (Play)")

        self.tabs.currentChanged.connect(self.handle_tab_change)
        self.setCentralWidget(self.tabs)

    def get_static_detector(self):
        """Dedicated detector for static image uploads (static_image_mode=True)."""
        if self._static_pose_detector is None:
            self._static_pose_detector = self.mp_pose.Pose(
                static_image_mode=True,
                model_complexity=1,
                min_detection_confidence=0.5
            )
        return self._static_pose_detector

    def get_stream_detector(self):
        """Dedicated detector for live webcam stream (static_image_mode=False)."""
        if self._stream_pose_detector is None:
            self._stream_pose_detector = self.mp_pose.Pose(
                static_image_mode=False,
                model_complexity=1,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )
        return self._stream_pose_detector

    def on_poses_updated(self):
        if len(self.pose_library) == 1 and self.game_tab.current_target is None:
            self.game_tab.pick_random_pose()

    def handle_tab_change(self, index):
        if index == 1:
            self.game_tab.start_camera()
        else:
            self.game_tab.stop_camera()

    def closeEvent(self, event):
        self.game_tab.stop_camera()
        if self._static_pose_detector:
            self._static_pose_detector.close()
        if self._stream_pose_detector:
            self._stream_pose_detector.close()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())