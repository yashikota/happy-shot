import cv2
import torch
import tempfile
import os
from feat import Detector
from PIL import Image
import numpy as np


class EmotionDetector:
    def __init__(self, device=None):
        self.device = (
            device if device else ("cuda" if torch.cuda.is_available() else "cpu")
        )
        self.detector = self._initialize_detector()

    def _initialize_detector(self):
        detector = Detector(
            face_model="retinaface",
            landmark_model="mobilefacenet",
            au_model="svm",
            emotion_model="resmasknet",
            device=self.device,
        )

        if self.device == "cuda":
            print("CUDAが利用可能です！")
            print(f"使用中のGPU: {torch.cuda.get_device_name(0)}")
        else:
            print("CUDAは利用できません。CPUを使用します。")

        return detector

    def process_image(self, image):
        try:
            if isinstance(image, np.ndarray):
                image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
            elif not isinstance(image, Image.Image):
                raise ValueError(
                    "画像の形式がサポートされていません。PIL.ImageまたはNumPy配列を使用してください。"
                )

            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
                image_path = temp_file.name
                image.save(image_path)

            prediction = self.detector.detect_image(
                image_path, face_identity_threshold=0.8
            )
            os.remove(image_path)
        except Exception as e:
            print(f"画像処理中にエラーが発生しました: {e}")
            return None
        return prediction

    def analyze_emotions(self, prediction, smile_label="happiness"):
        valid_faces = 0
        smiling_faces = 0

        for idx, row in prediction.iterrows():
            valid_faces += 1
            emotions = prediction.emotions.iloc[idx]
            if emotions.idxmax() == smile_label:
                smiling_faces += 1

        return valid_faces, smiling_faces

    def save_smiling_faces(self, image, valid_faces, smiling_faces, output_path):
        if valid_faces > 0 and smiling_faces / valid_faces >= 0.7:
            if isinstance(image, Image.Image):
                image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            cv2.imwrite(output_path, image)
            print(f"画像を保存しました: {output_path}")
            return True
        return False

    def process_single_image(self, image, output_path):
        print("画像を処理中...")
        if image is None:
            print("画像が無効です。")
            return

        prediction = self.process_image(image)
        if prediction is None:
            return

        valid_faces, smiling_faces = self.analyze_emotions(prediction)

        if self.save_smiling_faces(image, valid_faces, smiling_faces, output_path):
            print(f"笑顔の画像が保存されました: {output_path}")
        else:
            print("笑顔の閾値を満たさなかったため、画像は保存されませんでした。")

    def process_single_image2(self, image):
        if image is None:
            print("画像が無効です。")
            return False

        prediction = self.process_image(image)
        if prediction is None:
            return False

        valid_faces, smiling_faces = self.analyze_emotions(prediction)

        return valid_faces > 0 and smiling_faces / valid_faces >= 0.7


if __name__ == "__main__":
    image_path = "src/output_frames/frame_000740.png"
    output_path = "src/output_images/smiling_face.png"

    detector = EmotionDetector()
    image = cv2.imread(image_path)
    detector.process_single_image(image, output_path)
