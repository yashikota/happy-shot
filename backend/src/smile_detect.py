import os
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

    # 検出された顔について処理
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


# ディレクトリ内のすべての画像を処理して笑顔の顔を保存
def process_images_in_directory(image_dir, output_dir, detector):
    os.makedirs(output_dir, exist_ok=True)

    # 画像ファイルをディレクトリから取得
    image_files = [
        f for f in os.listdir(image_dir) if f.lower().endswith(("png", "jpg", "jpeg"))
    ]
    if not image_files:
        print("指定されたディレクトリに画像がありません。")
        return

    saved_count = 0

    # すべての画像ファイルを処理
    for image_file in image_files:
        image_path = os.path.join(image_dir, image_file)
        print(f"画像 {image_path} を処理中...")

        # 画像を読み込み
        image = cv2.imread(image_path)
        if image is None:
            print(f"画像を読み込めませんでした: {image_path}")
            continue

        # 画像の処理と感情予測を実行
        prediction = process_image(image_path, detector)
        if prediction is None:
            continue

        # 感情を分析して笑顔の顔を検出
        valid_faces, smiling_faces = analyze_emotions(prediction)

        # 必要なら画像を保存
        output_path = os.path.join(output_dir, image_file)
        if save_smiling_faces(image, valid_faces, smiling_faces, output_path):
            saved_count += 1

    print(f"画像の処理が完了しました。保存した画像数: {saved_count}")


if __name__ == "__main__":
    image_dir = "./output_frames"  # 画像ファイルが入っているディレクトリのパス
    output_dir = "./output_images/"  # 保存先のフォルダ

    detector = initialize_detector()  # Detectorの初期化
    process_images_in_directory(image_dir, output_dir, detector)  # 画像の処理を実行
