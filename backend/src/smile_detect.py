import cv2
import torch
from feat import Detector


# Detectorの初期化（GPUが利用可能か確認）
def initialize_detector():
    detector = Detector(
        face_model="retinaface",
        landmark_model="mobilefacenet",
        au_model="svm",
        emotion_model="resmasknet",
        device="cuda",
    )

    if torch.cuda.is_available():
        print("CUDAが利用可能です！")
        print(f"使用中のGPU: {torch.cuda.get_device_name(0)}")
    else:
        print("CUDAは利用できません。CPUを使用します。")

    return detector


# 画像の処理と感情予測を行う
def process_image(image, detector):
    try:
        # 画像を直接メモリ上で処理
        prediction = detector.detect_image(image, face_identity_threshold=0.8)
    except Exception as e:
        print(f"画像処理中にエラーが発生しました: {e}")
        return None

    return prediction


# 感情を分析して笑顔を検出
def analyze_emotions(prediction, smile_label="happiness"):
    valid_faces = 0
    smiling_faces = 0

    for idx, row in prediction.iterrows():
        valid_faces += 1
        emotions = prediction.emotions.iloc[idx]
        if emotions.idxmax() == smile_label:
            smiling_faces += 1

    return valid_faces, smiling_faces


# 笑顔の顔が検出された画像を保存
def save_smiling_faces(image, valid_faces, smiling_faces, output_path):
    if valid_faces > 0 and smiling_faces / valid_faces >= 0.7:
        cv2.imwrite(output_path, image)
        print(f"画像を保存しました: {output_path}")
        return True
    return False


# **1枚の画像を処理する関数**
def process_single_image(image_path, output_path, detector):
    print(f"画像 {image_path} を処理中...")

    # 画像を読み込み
    image = cv2.imread(image_path)
    if image is None:
        print(f"画像を読み込めませんでした: {image_path}")
        return

    # 画像の処理と感情予測を実行
    prediction = process_image(image_path, detector)
    if prediction is None:
        return

    # 感情を分析して笑顔の顔を検出
    valid_faces, smiling_faces = analyze_emotions(prediction)

    # 必要なら画像を保存
    if save_smiling_faces(image, valid_faces, smiling_faces, output_path):
        print(f"笑顔の画像が保存されました: {output_path}")
    else:
        print("笑顔の閾値を満たさなかったため、画像は保存されませんでした。")


if __name__ == "__main__":
    image_path = "./output_frames/frame_000740.png"  # **処理したい画像のパス**
    output_path = (
        "./output_images/falkfjalkjdf:ajlgjalgja.png"  # **保存する画像のパス**
    )

    detector = initialize_detector()  # Detectorの初期化
    process_single_image(image_path, output_path, detector)  # **1枚の画像を処理**
