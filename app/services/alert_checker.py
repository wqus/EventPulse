import asyncio
import logging
from datetime import datetime, timedelta, timezone
from redis.asyncio import Redis
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.Event import Event
from app.models.alert import AlertRule
from app.repositories import alert as alert_repo
from app.repositories import tenant as tenant_repo
from app.services.telegram import (
    send_telegram_message,
    format_alert_message,
    format_resolved_message,
)

logger = logging.getLogger("alert_checker")

CHECK_INTERVAL_SECONDS = 30
COOLDOWN_SECONDS = 60


async def count_events_in_window(tenant_id, event_name: str, window_seconds: int, session: AsyncSession) -> int:
    since = datetime.now(timezone.utc) - timedelta(seconds=window_seconds)

    result = await session.execute(
        select(func.count())
        .select_from(Event)
        .where(Event.tenant_id == tenant_id)
        .where(Event.event_name == event_name)
        .where(Event.timestamp >= since)
    )
    return result.scalar() or 0


async def is_in_cooldown(rule_id, redis: Redis) -> bool:
    key = f"alert:cooldown:{rule_id}"
    exists = await redis.get(key)
    return exists is not None


async def set_cooldown(rule_id, redis: Redis) -> None:
    key = f"alert:cooldown:{rule_id}"
    await redis.set(key, "1", ex=COOLDOWN_SECONDS)


async def maybe_send_alert(rule: AlertRule, count: int, tenant_chat_id: str, session: AsyncSession,
                           redis: Redis) -> None:
    active = await alert_repo.get_active_alert(rule.id, session)

    if active:
        return

    await alert_repo.create_alert_history(rule.id, count, session)

    if await is_in_cooldown(rule.id, redis):
        return

    text = format_alert_message(rule.event_name, count, rule.threshold, rule.window_seconds)
    sent = await send_telegram_message(tenant_chat_id, text)

    if sent:
        await set_cooldown(rule.id, redis)
    else:
        logger.warning(f"Failed to send alert for rule {rule.id}")


async def maybe_resolve_alert(rule: AlertRule, tenant_chat_id: str, session: AsyncSession) -> None:
    active = await alert_repo.get_active_alert(rule.id, session)

    if not active:
        return

    await alert_repo.resolve_alert(active, session)

    text = format_resolved_message(rule.event_name)
    await send_telegram_message(tenant_chat_id, text)


async def check_all_rules(session: AsyncSession, redis: Redis) -> None:
    rules = await alert_repo.get_active_rules(session)

    for rule in rules:
        tenant = await tenant_repo.get_by_id(rule.tenant_id, session)

        if not tenant or not tenant.telegram_chat_id:
            continue

        count = await count_events_in_window(
            tenant.id, rule.event_name, rule.window_seconds, session
        )

        if count > rule.threshold:
            await maybe_send_alert(rule, count, tenant.telegram_chat_id, session, redis)
        else:
            await maybe_resolve_alert(rule, tenant.telegram_chat_id, session)


async def run_alert_checker(session_factory, redis: Redis) -> None:
    logger.info("Alert checker started")

    while True:
        try:
            async with session_factory() as session:
                await check_all_rules(session, redis)
        except Exception as e:
            logger.error(f"Alert checker iteration failed: {e}")

        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
