import asyncio
import logging
import os
import uuid

import aiohttp
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Request
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (ApiClient, Configuration, MessagingApi,
                                  PushMessageRequest, ReplyMessageRequest,
                                  TextMessage)
from linebot.v3.webhooks import (MessageEvent, TextMessageContent,
                                 VideoMessageContent)

# ロガーの取得
logger = logging.getLogger(__name__)

# LINE Bot設定
load_dotenv()
configuration = Configuration(access_token=os.getenv("ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("CHANNEL_SECRET"))

# ルーターの設定
router = APIRouter(
    prefix="/line",
    tags=["line"],
    responses={404: {"description": "Not found"}},
)


async def send_line_notification(message: str, user_id: str):
    """LINEにプッシュメッセージを送信する"""
    if not user_id:
        logger.error("user_idが設定されていません")
        return

    retry_key = str(uuid.uuid4())
    try:
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            response = line_bot_api.push_message(
                PushMessageRequest(
                    to=user_id,
                    messages=[TextMessage(text=message)],
                ),
                _headers={"X-Line-Retry-Key": retry_key},
            )
            logger.info(f"プッシュメッセージを送信しました: {message}")
            return response
    except Exception as e:
        logger.error(f"プッシュメッセージの送信に失敗しました: {str(e)}")
        return None


async def check_video_status(message_id: str) -> bool:
    """動画の取得準備状況を確認する"""
    url = f"https://api-data.line.me/v2/bot/message/{message_id}/content/transcoding"
    headers = {"Authorization": f"Bearer {os.getenv('ACCESS_TOKEN')}"}

    logger.info(f"動画の取得準備状況を確認中... (message_id: {message_id})")
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                status = data["status"]
                logger.info(f"動画の取得準備状況: {status}")
                return status == "succeeded"
            logger.error(f"動画の取得準備状況の確認に失敗: {response.status}")
            return False


async def download_video(message_id: str, save_path: str) -> bool:
    """動画コンテンツを取得して保存する"""
    url = f"https://api-data.line.me/v2/bot/message/{message_id}/content"
    headers = {"Authorization": f"Bearer {os.getenv('ACCESS_TOKEN')}"}

    # 動画保存用のディレクトリを作成
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    logger.info(f"動画のダウンロードを開始... (message_id: {message_id})")

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                with open(save_path, "wb") as f:
                    total_size = 0
                    while True:
                        chunk = await response.content.read(8192)
                        if not chunk:
                            break
                        f.write(chunk)
                        total_size += len(chunk)
                logger.info(
                    f"動画のダウンロードが完了しました。サイズ: {total_size / 1024 / 1024:.2f}MB"
                )
                return True
            logger.error(f"動画のダウンロードに失敗: {response.status}")
            return False


@router.post("/callback")
async def callback(request: Request):
    # get X-Line-Signature header value
    signature = request.headers.get("X-Line-Signature")
    if signature is None:
        logger.error("X-Line-Signatureヘッダーが見つかりません")
        raise HTTPException(status_code=400, detail="X-Line-Signature header missing")

    # get request body as text
    body = await request.body()
    body = body.decode("utf-8")

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        logger.error("署名が無効です")
        raise HTTPException(
            status_code=400,
            detail="Invalid signature. Please check your channel access token/channel secret.",
        )

    return "OK"


@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    logger.info(f"テキストメッセージを受信: {event.message.text}")
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=event.message.text)],
            )
        )


@handler.add(MessageEvent, message=VideoMessageContent)
def handle_video_message(event):
    asyncio.create_task(_handle_video_message(event))


async def _handle_video_message(event):
    message_id = event.message.id
    logger.info(f"動画メッセージを受信しました。message_id: {message_id}")

    user_id = event.source.user_id
    if not user_id:
        logger.error("ユーザーIDが取得できません")
        return
    logger.info(f"ユーザーID: {user_id}")

    # まず受信確認のメッセージを送信
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        try:
            line_bot_api.reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[
                        TextMessage(text="動画を受信しました。処理を開始します...")
                    ],
                )
            )
        except Exception as e:
            logger.error(f"初回返信の送信に失敗しました: {str(e)}")

    # 動画の保存パス
    save_dir = "uploaded_videos"
    save_path = os.path.join(save_dir, f"{message_id}.mp4")

    # 動画の取得準備が完了するまで待機（最大30秒）
    logger.info("動画の取得準備の完了を待機中...")
    for i in range(30):
        if await check_video_status(message_id):
            logger.info(f"動画の取得準備が完了しました（{i + 1}秒）")
            break
        await asyncio.sleep(1)
        if i == 29:
            logger.error("動画の取得準備がタイムアウトしました")

    # 動画をダウンロードして保存
    success = await download_video(message_id, save_path)

    # 処理結果をログに記録
    if success:
        logger.info(f"動画の保存が完了しました: {save_path}")
    else:
        logger.error("動画の保存に失敗しました")

    # 抽出処理およびアップロード処理
    process_id = None
    async with aiohttp.ClientSession() as session:
        url = "https://happy-shot.yashikota.com/upload"
        form = aiohttp.FormData()
        try:
            with open(save_path, "rb") as f:
                form.add_field(
                    "file", f, filename=f"{message_id}.mp4", content_type="video/mp4"
                )
                async with session.post(url, data=form) as response:
                    if not response.ok:
                        logger.error(f"アップロードに失敗しました: {response.status}")
                        await send_line_notification(
                            "動画のアップロードに失敗しました。", user_id
                        )
                    else:
                        data = await response.json()
                        process_id = data.get("process_id")
                        if process_id:
                            logger.info(
                                f"アップロード処理が完了しました: {process_id=}"
                            )
                            await send_line_notification(
                                f"アルバムの作成が完了しました！\nhttps://happy-shot.vercel.app/{process_id}",
                                user_id,
                            )
                        else:
                            logger.error("アップロードレスポンスにIDが含まれていません")
                            await send_line_notification(
                                "アップロード処理中にエラーが発生しました。", user_id
                            )
        except Exception as e:
            logger.error(f"アップロード処理でエラーが発生しました: {str(e)}")
            await send_line_notification(
                "アップロード処理中にエラーが発生しました。", user_id
            )
