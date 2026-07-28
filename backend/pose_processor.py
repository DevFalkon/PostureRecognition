import cv2
import numpy as np
import mediapipe as mp

def calculate_angle(a, b, c):
    a = np.array([a.x, a.y])
    b = np.array([b.x, b.y])
    c = np.array([c.x, c.y])

    radians = np.arctan2(c[1] - b[1], c[0] - b[0]) - np.arctan2(a[1] - b[1], a[0] - b[0])
    angle = np.abs(radians * 180.0 / np.pi)
    if angle > 180.0:
        angle = 360 - angle
    return angle


class PoseProcessor:
    def __init__(self):
        self.mp_pose = mp.solutions.pose
        self.mp_drawing = mp.solutions.drawing_utils
        self._static_detector = None
        self._stream_detector = None

    def _get_static_detector(self):
        if self._static_detector is None:
            self._static_detector = self.mp_pose.Pose(
                static_image_mode=True,
                model_complexity=1,
                min_detection_confidence=0.5
            )
        return self._static_detector

    def _get_stream_detector(self):
        if self._stream_detector is None:
            self._stream_detector = self.mp_pose.Pose(
                static_image_mode=False,
                model_complexity=1,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )
        return self._stream_detector

    def extract_angles(self, landmarks):
        lm = landmarks.landmark
        mp_p = self.mp_pose.PoseLandmark
        return {
            "l_elbow": calculate_angle(lm[mp_p.LEFT_SHOULDER], lm[mp_p.LEFT_ELBOW], lm[mp_p.LEFT_WRIST]),
            "r_elbow": calculate_angle(lm[mp_p.RIGHT_SHOULDER], lm[mp_p.RIGHT_ELBOW], lm[mp_p.RIGHT_WRIST]),
            "l_knee": calculate_angle(lm[mp_p.LEFT_HIP], lm[mp_p.LEFT_KNEE], lm[mp_p.LEFT_ANKLE]),
            "r_knee": calculate_angle(lm[mp_p.RIGHT_HIP], lm[mp_p.RIGHT_KNEE], lm[mp_p.RIGHT_ANKLE]),
        }

    def process_static_image(self, file_path):
        """Processes an uploaded file. Returns (annotated_bgr_img, angles_dict) or (None, None)."""
        img = cv2.imread(file_path)
        if img is None:
            return None, None

        rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        detector = self._get_static_detector()
        results = detector.process(rgb_img)

        if not results.pose_landmarks:
            return None, None

        annotated_img = img.copy()
        self.mp_drawing.draw_landmarks(
            annotated_img, results.pose_landmarks, self.mp_pose.POSE_CONNECTIONS
        )
        angles = self.extract_angles(results.pose_landmarks)
        return annotated_img, angles

    def process_stream_frame(self, frame, target_angles=None, tolerance=20.0):
        """Processes live camera frame. Returns (annotated_bgr_frame, is_match)."""
        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        detector = self._get_stream_detector()
        results = detector.process(rgb_frame)

        is_match = False
        if results.pose_landmarks:
            self.mp_drawing.draw_landmarks(
                frame, results.pose_landmarks, self.mp_pose.POSE_CONNECTIONS
            )
            if target_angles:
                curr_angles = self.extract_angles(results.pose_landmarks)
                is_match = all(
                    abs(curr_angles[j] - target_angles[j]) < tolerance
                    for j in target_angles
                )

        return frame, is_match

    def close(self):
        if self._static_detector:
            self._static_detector.close()
        if self._stream_detector:
            self._stream_detector.close()