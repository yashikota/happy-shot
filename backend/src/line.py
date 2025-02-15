import asyncio
import os
import aiohttp
import logging
from fastapi import APIRouter, Request, HTTPException
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent, VideoMessageContent
from dotenv import load_dotenv

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

    # まず受信確認のメッセージを送信
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[
                    TextMessage(text="動画を受信しました。保存処理を開始します...")
                ],
            )
        )

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
