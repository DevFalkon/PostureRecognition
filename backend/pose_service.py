import cv2
import numpy as np
import mediapipe as mp


def calculate_angle(a, b, c) -> float:
    """Calculates 2D angle (in degrees) formed at joint 'b' by endpoints 'a' and 'c'."""
    a_arr = np.array([a.x, a.y])
    b_arr = np.array([b.x, b.y])
    c_arr = np.array([c.x, c.y])

    radians = np.arctan2(c_arr[1] - b_arr[1], c_arr[0] - b_arr[0]) - np.arctan2(a_arr[1] - b_arr[1], a_arr[0] - b_arr[0])
    angle = np.abs(radians * 180.0 / np.pi)
    if angle > 180.0:
        angle = 360.0 - angle
    return angle


class PoseService:
    """Handles MediaPipe detection, skeletal rendering, and angle calculations."""

    def __init__(self):
        self.mp_pose = mp.solutions.pose
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles
        self._static_detector = None
        self._stream_detector = None

        # Build custom landmark drawing specs that hide facial points (0 to 10)
        self.body_landmark_spec = {}
        for landmark_id in self.mp_pose.PoseLandmark:
            if landmark_id.value <= 10:
                # Face landmarks: circle_radius=0 hides the dots
                self.body_landmark_spec[landmark_id.value] = self.mp_drawing.DrawingSpec(
                    color=(0, 0, 0), thickness=0, circle_radius=0
                )
            else:
                # Body landmarks: standard green dots
                self.body_landmark_spec[landmark_id.value] = self.mp_drawing.DrawingSpec(
                    color=(0, 255, 0), thickness=2, circle_radius=3
                )

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

    def extract_angles(self, landmarks) -> dict:
        """Extracts key joint and body orientation angles from detected landmarks."""
        lm = landmarks.landmark
        mp_p = self.mp_pose.PoseLandmark
        return {
            # 1. Limb Bends (Are arms/legs bent or straight?)
            "l_elbow": calculate_angle(lm[mp_p.LEFT_SHOULDER], lm[mp_p.LEFT_ELBOW], lm[mp_p.LEFT_WRIST]),
            "r_elbow": calculate_angle(lm[mp_p.RIGHT_SHOULDER], lm[mp_p.RIGHT_ELBOW], lm[mp_p.RIGHT_WRIST]),
            "l_knee": calculate_angle(lm[mp_p.LEFT_HIP], lm[mp_p.LEFT_KNEE], lm[mp_p.LEFT_ANKLE]),
            "r_knee": calculate_angle(lm[mp_p.RIGHT_HIP], lm[mp_p.RIGHT_KNEE], lm[mp_p.RIGHT_ANKLE]),

            # 2. Limb Positions relative to Torso (Are arms raised, spread, or down? Are hips bent/crouching?)
            "l_shoulder": calculate_angle(lm[mp_p.LEFT_HIP], lm[mp_p.LEFT_SHOULDER], lm[mp_p.LEFT_ELBOW]),
            "r_shoulder": calculate_angle(lm[mp_p.RIGHT_HIP], lm[mp_p.RIGHT_SHOULDER], lm[mp_p.RIGHT_ELBOW]),
            "l_hip": calculate_angle(lm[mp_p.LEFT_SHOULDER], lm[mp_p.LEFT_HIP], lm[mp_p.LEFT_KNEE]),
            "r_hip": calculate_angle(lm[mp_p.RIGHT_SHOULDER], lm[mp_p.RIGHT_HIP], lm[mp_p.RIGHT_KNEE]),
        }

    def process_static_image(self, file_path: str):
        """Processes a static image. Returns (raw_img, annotated_img, angles) or (None, None, None)."""
        img = cv2.imread(file_path)
        if img is None:
            return None, None, None

        rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        detector = self._get_static_detector()
        results = detector.process(rgb_img)

        if not results.pose_landmarks:
            return None, None, None

        annotated_img = img.copy()
        
        # Render using custom body-only spec
        self.mp_drawing.draw_landmarks(
            annotated_img,
            results.pose_landmarks,
            self.mp_pose.POSE_CONNECTIONS,
            landmark_drawing_spec=self.body_landmark_spec,
        )
        angles = self.extract_angles(results.pose_landmarks)
        
        return img, annotated_img, angles

    def process_stream_frame(
        self, frame, target_angles: dict = None, match_threshold: float = 80.0
    ):
        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        detector = self._get_stream_detector()
        results = detector.process(rgb_frame)

        is_match = False
        similarity_score = 0.0

        if results.pose_landmarks:
            # Render using custom body-only spec
            self.mp_drawing.draw_landmarks(
                frame,
                results.pose_landmarks,
                self.mp_pose.POSE_CONNECTIONS,
                landmark_drawing_spec=self.body_landmark_spec,
            )

            if target_angles:
                curr_angles = self.extract_angles(results.pose_landmarks)

                diffs = []
                for j, target_deg in target_angles.items():
                    if j in curr_angles:
                        # 1. Calculate proper angular error on circle path
                        error = abs(curr_angles[j] - target_deg)
                        error = min(error, 360.0 - error)

                        # 2. Smooth linear scale: 0 deg error = 100%, 90 deg error = 0%
                        joint_score = max(0.0, 100.0 - (error / 90.0) * 100.0)
                        diffs.append(joint_score)

                if diffs:
                    similarity_score = round(sum(diffs) / len(diffs), 1)
                    is_match = similarity_score >= match_threshold

        return frame, is_match, similarity_score

    def close(self):
        """Releases active MediaPipe resources."""
        if self._static_detector:
            self._static_detector.close()
        if self._stream_detector:
            self._stream_detector.close()