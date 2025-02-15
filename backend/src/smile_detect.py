import os
import cv2
import torch
import tempfile
from feat import Detector

# Detectorの初期化（GPU使用）
detector = Detector(
    face_model="retinaface",
    landmark_model="mobilefacenet",
    au_model='svm',
    emotion_model="resmasknet", 
    device="cuda"
)

# CUDAが使用可能かどうかを確認
if torch.cuda.is_available():
    print("CUDA is available!")
    print(f"Using GPU: {torch.cuda.get_device_name(0)}")
else:
    print("CUDA is not available. Using CPU.")

# 動画ファイルのパスと出力フォルダの設定
video_path = "./video3.mp4"  # 動画ファイルのパスを指定
output_dir = "./output_frames5/"
os.makedirs(output_dir, exist_ok=True)

# 動画の読み込み
cap = cv2.VideoCapture(video_path)

frame_idx = 0
saved_count = 0
smile_label = "happiness"

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    frame_idx += 1

    # 10フレームごとに処理を適用
    if frame_idx % 10 != 0:
        continue

    print(f"Processing frame {frame_idx}...")  # フレーム番号の表示

    try:
        # フレーム (NumPy配列) を PNG 形式にエンコード
        ret2, encoded_img = cv2.imencode('.png', frame)
        if not ret2:
            raise ValueError("Failed to encode frame")
        
        # 一時ファイルに保存して、そのパスを渡す
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
            tmp_file.write(encoded_img.tobytes())
            tmp_path = tmp_file.name

        # 一時ファイルのパスを使って顔検出・感情認識を実施
        prediction = detector.detect_image(tmp_path, face_identity_threshold = 0.8)
    except Exception as e:
        print(f"Error processing frame {frame_idx}: {e}")
        # 一時ファイルが残っている可能性があるので削除
        if 'tmp_path' in locals() and os.path.exists(tmp_path):
            os.remove(tmp_path)
        continue
    finally:
        # 常に一時ファイルを削除
        if 'tmp_path' in locals() and os.path.exists(tmp_path):
            os.remove(tmp_path)

    valid_faces = 0
    smiling_faces = 0

    # 各検出された顔についてループ
    for idx, row in prediction.iterrows():
        valid_faces += 1

        emotions = prediction.emotions.iloc[idx]
        if emotions.idxmax() == smile_label:
            smiling_faces += 1

    # 全ての有効な顔が笑顔の場合、フレームを保存
    if valid_faces > 0 and smiling_faces / valid_faces >= 0.7:
        output_path = os.path.join(output_dir, f"frame_{frame_idx:06d}.png")
        cv2.imwrite(output_path, frame)
        saved_count += 1
        print(f"Saved frame {frame_idx} with {valid_faces} faces (all smiling).")

cap.release()
print(f"Finished processing video. Total frames saved: {saved_count}")
