import logging
import httpx
from datetime import datetime, timezone
from app.core.config import settings

logger = logging.getLogger("telegram")

TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"


async def send_telegram_message(chat_id: str, text: str) -> bool:
    url = TELEGRAM_API_URL.format(token=settings.TELEGRAM_BOT_TOKEN)

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                url,
                json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
            )
            response.raise_for_status()
            return True
    except httpx.HTTPStatusError as e:
        logger.warning(f"Telegram API error for chat {chat_id}: {e.response.status_code}")
        return False
    except httpx.RequestError as e:
        logger.error(f"Telegram request failed: {e}")
        return False


def format_alert_message(event_name: str, count: int, threshold: int, window_seconds: int) -> str:
    minutes = window_seconds // 60
    return (
        f"<b>EventPulse Alert</b>\n"
        f"Event: <code>{event_name}</code>\n"
        f"Count: {count} за последние {minutes} мин\n"
        f"Threshold: {threshold}"
    )


def format_resolved_message(event_name: str) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    return (
        f"<b>EventPulse Resolved</b>\n"
        f"Event: <code>{event_name}</code>\n"
        f"Incident closed at: {now}"
    )