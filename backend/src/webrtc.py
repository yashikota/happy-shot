import asyncio
import logging
from ulid import ULID
import cv2
import time
from aiortc import (
    RTCPeerConnection,
    RTCSessionDescription,
    RTCRtpSender,
    RTCConfiguration,
    RTCIceServer,
)  # type: ignore
from aiortc.contrib.media import MediaRelay  # type: ignore
from fastapi import FastAPI, Request  # type: ignore
from fastapi.responses import JSONResponse  # type: ignore
from fastapi.middleware.cors import CORSMiddleware  # CORS対応

# FastAPIアプリの初期化
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ロギング設定
logger = logging.getLogger("webrtc_server")
logger.setLevel(logging.DEBUG)  # より詳細なログを有効化
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logger.addHandler(handler)

# WebRTC関連の管理変数
pcs = set()
relay = MediaRelay()


async def capture_frames(track, pc_id):
    """映像フレームを継続的に取得して保存する"""
    frame_count = 0
    start_time = time.time()
    last_frame_time = start_time

    try:
        logger.info(f"{pc_id} Starting frame capture")
        logger.info(f"{pc_id} Track info: kind={track.kind}, id={track.id}")

        while True:
            try:
                # フレーム取得
                frame = await track.recv()
                current_time = time.time()
                frame_interval = current_time - last_frame_time
                last_frame_time = current_time

                # フレームレート計算
                fps = 1 / frame_interval if frame_interval > 0 else 0
                logger.debug(f"{pc_id} Current FPS: {fps:.2f}")

                # フレーム情報
                img = frame.to_ndarray(format="bgr24")  # OpenCV形式に変換
                height, width = img.shape[:2]
                logger.debug(f"{pc_id} Frame size: {width}x{height}")

                # 絶対パスを使用してフレームを保存
                filename = os.path.join(
                    app.state.frames_dir, f"{pc_id}_{frame_count:04d}.jpg"
                )
                success = cv2.imwrite(filename, img)
                logger.debug(f"保存先: {filename}")

                if success:
                    logger.info(f"{pc_id} Saved frame {frame_count} ({width}x{height})")
                    frame_count += 1
                else:
                    logger.error(f"{pc_id} Failed to save frame {frame_count}")

                # 10フレームごとに詳細情報を出力
                if frame_count % 10 == 0:
                    elapsed_time = current_time - start_time
                    avg_fps = frame_count / elapsed_time if elapsed_time > 0 else 0
                    logger.info(
                        f"{pc_id} Capture stats: frames={frame_count}, "
                        f"elapsed={elapsed_time:.1f}s, avg_fps={avg_fps:.1f}"
                    )

                # フレームレート調整（約10FPS）
                await asyncio.sleep(0.1)

            except asyncio.CancelledError:
                logger.info(f"{pc_id} Frame capture task cancelled")
                raise

            except Exception as e:
                logger.error(f"{pc_id} Error processing frame: {str(e)}")
                await asyncio.sleep(1)  # エラー時は1秒待機してリトライ

    except Exception as e:
        logger.error(f"{pc_id} Fatal error in capture_frames: {str(e)}")
        raise

    finally:
        logger.info(f"{pc_id} Frame capture ended. Total frames: {frame_count}")


@app.post("/offer")
async def offer(request: Request):
    params = await request.json()
    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

    pc_id = f"PeerConnection({str(ULID())})"
    logger.info(f"Creating new connection: {pc_id}")

    pc = RTCPeerConnection(
        configuration=RTCConfiguration(
            iceServers=[
                RTCIceServer(
                    urls=[
                        "stun:stun.l.google.com:19302",
                        "stun:stun1.l.google.com:19302",
                    ]
                )
            ]
        )
    )
    pcs.add(pc)

    # Create a data channel for sending the ULID
    channel = pc.createDataChannel("ulid")
    logger.info(f"{pc_id} データチャネルを作成しました")

    @channel.on("open")
    def on_open():
        try:
            # Send the ULID when the channel opens
            channel.send(pc_id)
            logger.info(f"{pc_id} ULIDをデータチャネル経由で送信しました")
        except Exception as e:
            logger.error(f"{pc_id} ULID送信中にエラーが発生しました: {str(e)}")

    @channel.on("close")
    def on_close():
        logger.warning(f"{pc_id} データチャネルが閉じられました")

    @channel.on("error")
    def on_error(error):
        logger.error(f"{pc_id} データチャネルでエラーが発生: {str(error)}")

    # Configure transceivers before processing the offer
    transceiver = pc.addTransceiver("video", direction="recvonly")
    codecs = RTCRtpSender.getCapabilities("video").codecs
    preferred_codecs = [
        codec
        for codec in codecs
        if codec.name in ["H264", "VP8"] and not codec.name.startswith("rtx")
    ]
    transceiver.setCodecPreferences(preferred_codecs)

    # ICE candidate のログ出力を強化
    @pc.on("icecandidate")
    def on_icecandidate(event):
        if event.candidate:
            logger.info(
                f"{pc_id} New ICE candidate: type={event.candidate.type}, "
                f"protocol={event.candidate.protocol}, "
                f"address={event.candidate.address}, "
                f"port={event.candidate.port}, "
                f"foundation={event.candidate.foundation}"
            )
        else:
            logger.info(f"{pc_id} ICE gathering completed")

    logger.info(f"{pc_id} Created PeerConnection with enhanced ICE configuration")

    @pc.on("iceconnectionstatechange")
    async def on_iceconnectionstatechange():
        logger.info(f"{pc_id} ICE Connection state changed to: {pc.iceConnectionState}")
        if pc.iceConnectionState == "failed":
            logger.error(f"{pc_id} ICE Connection failed")

    @pc.on("icegatheringstatechange")
    def on_icegatheringstatechange():
        logger.info(f"{pc_id} ICE gathering state changed to: {pc.iceGatheringState}")

    @pc.on("track")
    def on_track(track):
        try:
            logger.info(f"{pc_id} Received track: kind={track.kind}, id={track.id}")

            if track.kind == "video":
                # トラックの詳細情報をログ出力
                logger.info(f"{pc_id} Video track details:")
                logger.info(f"  - ID: {track.id}")
                logger.info(f"  - Settings: {track.settings}")
                logger.info(f"  - Ready state: {track.readyState}")

                # トラックの設定を最適化
                transceiver = next(
                    (t for t in pc.getTransceivers() if t.receiver.track == track), None
                )
                if transceiver:
                    transceiver.direction = "sendrecv"
                    logger.info(f"{pc_id} Transceiver configured:")
                    logger.info(f"  - Direction: {transceiver.direction}")
                    logger.info(
                        f"  - Current direction: {transceiver.currentDirection}"
                    )

                # フレームの継続的なキャプチャを開始
                asyncio.create_task(capture_frames(track, pc_id))
                logger.info(f"{pc_id} Started frame capture task")

            # トラックイベントハンドラー
            @track.on("ended")
            async def on_ended():
                logger.warning(f"{pc_id} Track {track.kind} ended")
                try:
                    track.stop()
                    logger.info(f"{pc_id} Stopped track after end event")
                except Exception as e:
                    logger.error(f"{pc_id} Error cleaning up track: {e}")

            @track.on("mute")
            async def on_mute():
                logger.warning(f"{pc_id} Track {track.kind} muted")
                logger.info(f"{pc_id} Track mute state: {track.muted}")

            @track.on("unmute")
            async def on_unmute():
                logger.info(f"{pc_id} Track {track.kind} unmuted")
                logger.info(f"{pc_id} Track mute state: {track.muted}")

        except Exception as e:
            logger.error(f"{pc_id} Error in track handling: {str(e)}")

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        logger.info(f"{pc_id} Connection state: {pc.connectionState}")

        if pc.connectionState in ["disconnected", "failed"]:
            logger.warning(f"{pc_id} Connection lost, retrying in 10 seconds...")
            await asyncio.sleep(10)  # 10秒待機してリカバリー
            if pc.connectionState == "failed":
                await pc.close()
                pcs.discard(pc)

    # オファーを処理
    await pc.setRemoteDescription(offer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    return JSONResponse(
        {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}
    )


@app.on_event("shutdown")
async def on_shutdown():
    coros = [pc.close() for pc in pcs]
    await asyncio.gather(*coros)
    pcs.clear()


if __name__ == "__main__":
    import uvicorn
    import os

    # 画像保存用フォルダの作成（絶対パスを使用）
    frames_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frames")
    os.makedirs(frames_dir, exist_ok=True)
    logger.info(f"画像保存ディレクトリを作成しました: {frames_dir}")

    # グローバルに保存ディレクトリを設定
    app.state.frames_dir = frames_dir

    uvicorn.run(app, host="0.0.0.0", port=5000)
