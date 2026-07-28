import os
import re
import cv2


class StorageService:
    """Handles all file system operations, disk saves, and dataset loading."""

    def __init__(self, pose_library: list, save_dir: str = "saved"):
        self.pose_library = pose_library
        self.save_dir = os.path.join(os.getcwd(), save_dir)
        os.makedirs(self.save_dir, exist_ok=True)

    def load_existing_poses(self) -> list[dict]:
        """Scans the disk directory and populates the pose library state."""
        if not os.path.exists(self.save_dir):
            return []

        files = [
            f for f in os.listdir(self.save_dir)
            if f.lower().endswith(('.png', '.jpg', '.jpeg'))
        ]
        if not files:
            return []

        def extract_number(filename: str) -> int:
            match = re.search(r'pose_(\d+)_', filename)
            return int(match.group(1)) if match else 9999

        files.sort(key=extract_number)
        loaded_entries = []

        for filename in files:
            saved_path = os.path.join(self.save_dir, filename)
            pose_index = len(self.pose_library) + 1
            pose_name = f"Pose_{pose_index}"
            display_filename = re.sub(r'^pose_\d+_', '', filename)

            entry = {
                "name": pose_name,
                "display_name": f"{pose_name} ({display_filename})",
                "angles": None,
                "path": saved_path
            }
            
            self.pose_library.append(entry)
            loaded_entries.append(entry)

        return loaded_entries

    def save_pose_image(self, annotated_img, angles: dict, original_file_path: str) -> dict:
        """Saves processed pose images to disk and registers them to memory."""
        pose_index = len(self.pose_library) + 1
        filename = os.path.basename(original_file_path)
        saved_path = os.path.join(self.save_dir, filename)

        cv2.imwrite(saved_path, annotated_img)

        pose_name = f"Pose_{pose_index}"
        entry = {
            "name": pose_name,
            "display_name": f"{filename}",
            "saved_filename": filename,
            "angles": angles,
            "path": saved_path
        }

        self.pose_library.append(entry)
        return entry