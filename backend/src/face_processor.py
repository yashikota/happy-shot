import cv2
import dlib
import numpy as np
import imutils
import matplotlib.pyplot as plt
from imutils import face_utils
from scipy.ndimage import gaussian_filter1d
from smile_detect import EmotionDetector
import requests


class FaceInstance:
    def __init__(self, face_id):
        self.face_id = face_id
        self.frames = []
        self.scores = []


class FaceProcessor:
    def __init__(
        self,
        video_source,
        job_id,
        predictor_path="src/shape_predictor_68_face_landmarks.dat",
    ):
        self.detector = dlib.get_frontal_face_detector()
        self.predictor = dlib.shape_predictor(predictor_path)
        self.video_source = video_source
        self.face_instances = []
        self.capture = cv2.VideoCapture(video_source)
        self.job_id = job_id
        self.smile_detector = EmotionDetector()
        self.id = job_id

    def calculate_eye_aspect_ratio(self, eye):
        A = np.linalg.norm(eye[1] - eye[5])
        B = np.linalg.norm(eye[2] - eye[4])
        C = np.linalg.norm(eye[0] - eye[3])
        return (A + B) / (2.0 * C)

    def estimate_head_pose(self, shape, frame):
        size = frame.shape
        focal_length = size[1]
        center = (size[1] // 2, size[0] // 2)
        camera_matrix = np.array(
            [[focal_length, 0, center[0]], [0, focal_length, center[1]], [0, 0, 1]],
            dtype="double",
        )
        dist_coeffs = np.zeros((4, 1))
        model_points = np.array(
            [
                (0.0, 0.0, 0.0),
                (-30.0, -125.0, -30.0),
                (30.0, -125.0, -30.0),
                (-60.0, -70.0, -60.0),
                (60.0, -70.0, -60.0),
                (-40.0, 40.0, -50.0),
                (40.0, 40.0, -50.0),
            ]
        )
        image_points = np.array(
            [
                tuple(shape[30]),
                tuple(shape[21]),
                tuple(shape[22]),
                tuple(shape[39]),
                tuple(shape[42]),
                tuple(shape[31]),
                tuple(shape[35]),
            ],
            dtype="double",
        )
        success, rotation_vector, translation_vector = cv2.solvePnP(
            model_points,
            image_points,
            camera_matrix,
            dist_coeffs,
            flags=cv2.SOLVEPNP_ITERATIVE,
        )
        if success:
            rotation_matrix, _ = cv2.Rodrigues(rotation_vector)
            angles = cv2.decomposeProjectionMatrix(
                np.hstack((rotation_matrix, np.zeros((3, 1))))
            )[6]
            return angles[1], angles[0], angles[2]
        return 0, 0, 0

    def calculate_face_score(self, yaw, pitch):
        return max(0, 100 - (abs(yaw) + abs(pitch)))

    def calculate_avg_values(self):
        avg_scores = {}
        for face in self.face_instances:
            for i, frame in enumerate(face.frames):
                avg_scores.setdefault(frame, []).append(face.scores[i])
        avg_frames = sorted(avg_scores.keys())
        avg_values = [np.mean(avg_scores[frame]) for frame in avg_frames]
        return avg_values, avg_frames

    def plot_face_scores(self):
        plt.figure()
        avg_scores = {}
        for face in self.face_instances:
            plt.plot(face.frames, face.scores, label=f"Face {face.face_id}")
            for i, frame in enumerate(face.frames):
                avg_scores.setdefault(frame, []).append(face.scores[i])

        avg_values, avg_frames = self.calculate_avg_values()
        avg_values = [
            v for v in avg_values if isinstance(v, (int, float))
        ]  # 数値のみを抽出
        avg_values = np.array(avg_values, dtype=np.float64)
        smoothed_avg_values = gaussian_filter1d(avg_values, sigma=2)

        diff = np.diff(smoothed_avg_values)
        peak_frames = [
            avg_frames[i]
            for i in range(1, len(diff))
            if diff[i - 1] > 0 and diff[i] < 0
        ]
        peak_scores = {f: smoothed_avg_values[avg_frames.index(f)] for f in peak_frames}
        peak_frames = sorted(peak_scores, key=lambda x: peak_scores[x], reverse=True)
        peak_frames = peak_frames[: int(len(peak_frames) * 0.7)]
        print("上に凸の頂点となるフレーム番号:", peak_frames)

        avg_ratios = []
        for frame_no in peak_frames:
            self.capture.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
            ret, frame = self.capture.read()
            if not ret:
                continue
            avg_ratio = self.calculate_eye_aspect_ratio(frame)
            avg_ratios.append((frame_no, avg_ratio))
            print(f"Frame {frame_no}: Average Eye Aspect Ratio = {avg_ratio}")

        avg_ratios = sorted(avg_ratios, key=lambda x: x[1])
        avg_ratios = avg_ratios[: int(len(avg_ratios) * 0.7)]

        for frame_no, _ in avg_ratios:
            self.capture.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
            ret, frame = self.capture.read()

            # 笑顔判定
            if not self.smile_detector.process_single_image2(frame):
                continue

            if ret:
                # 画像を保存する
                frame_filename = f"src/processed_images/frame_{frame_no}.jpg"
                # cv2.imwrite(frame_filename, frame)

                # 画像をアップロード
                upload_url = f"https://app-122ab23f-3126-4106-9d44-988a8bd962de.ingress.apprun.sakura.ne.jp/upload?bucket={self.id}"
                files = {"file": open(frame_filename, "rb")}

                # POSTリクエストで画像をアップロード
                response = requests.post(upload_url, files=files)
                files.close()

                # レスポンスを表示（任意）
                if response.status_code == 200:
                    print(f"Successfully uploaded frame {frame_no}")
                else:
                    print(
                        f"Failed to upload frame {frame_no}, status code: {response.status_code}"
                    )

        plt.plot(
            avg_frames,
            smoothed_avg_values,
            label="Smoothed Average Score",
            linestyle="dashed",
            color="black",
        )
        plt.xlabel("Frame Number")
        plt.ylabel("Face Score")
        plt.legend()
        plt.show()

    def process_video(self):
        while True:
            ret, frame = self.capture.read()
            if not ret:
                print("動画の読み込み終了またはエラー発生")
                break

            frame = imutils.resize(frame, width=1000)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            rects = self.detector(gray, 0)

            model_points = np.array(
                [
                    (0.0, 0.0, 0.0),
                    (-30.0, -125.0, -30.0),
                    (30.0, -125.0, -30.0),
                    (-60.0, -70.0, -60.0),
                    (60.0, -70.0, -60.0),
                    (-40.0, 40.0, -50.0),
                    (40.0, 40.0, -50.0),
                ]
            )
            size = frame.shape
            focal_length = size[1]
            center = (size[1] // 2, size[0] // 2)
            camera_matrix = np.array(
                [[focal_length, 0, center[0]], [0, focal_length, center[1]], [0, 0, 1]],
                dtype="double",
            )
            dist_coeffs = np.zeros((4, 1))

            for rect in rects:
                shape = self.predictor(gray, rect)
                shape = face_utils.shape_to_np(shape)
                image_points = np.array(
                    [
                        tuple(shape[30]),
                        tuple(shape[21]),
                        tuple(shape[22]),
                        tuple(shape[39]),
                        tuple(shape[42]),
                        tuple(shape[31]),
                        tuple(shape[35]),
                    ],
                    dtype="double",
                )
                shape = self.predictor(gray, rect)
                shape = face_utils.shape_to_np(shape)
                yaw, pitch, roll = self.estimate_head_pose(shape, frame)
                face_id = len(self.face_instances)
                face = FaceInstance(face_id)
                face.frames.append(self.capture.get(cv2.CAP_PROP_POS_FRAMES))
                face.scores.append(self.calculate_face_score(yaw, pitch))
                self.face_instances.append(face)

                for x, y in shape:
                    cv2.circle(frame, (x, y), 1, (255, 255, 255), -1)

                success, rotation_vector, translation_vector = cv2.solvePnP(
                    model_points,
                    image_points,
                    camera_matrix,
                    dist_coeffs,
                    flags=cv2.SOLVEPNP_ITERATIVE,
                )

                nose_end_point2D, _ = cv2.projectPoints(
                    np.array([(0.0, 0.0, 500.0)]),
                    rotation_vector,
                    translation_vector,
                    camera_matrix,
                    dist_coeffs,
                )

                p1 = (int(image_points[0][0]), int(image_points[0][1]))
                p2 = (
                    int(nose_end_point2D[0][0][0]),
                    int(nose_end_point2D[0][0][1]),
                )

                cv2.arrowedLine(frame, p1, p2, (255, 0, 0), 2)

            print(f"Frame {self.capture.get(cv2.CAP_PROP_POS_FRAMES)}")
            # cv2.imshow("Processed Image", frame)
            # if cv2.waitKey(1) & 0xFF == ord("q"):
            #     break

        self.plot_face_scores()


if __name__ == "__main__":
    processor = FaceProcessor(video_source="src/video.mp4", job_id="test")
    processor.process_video()
