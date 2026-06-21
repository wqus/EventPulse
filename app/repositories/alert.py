import uuid
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.alert import AlertRule, AlertHistory


async def create_rule(
        tenant_id: uuid.UUID,
        event_name: str,
        threshold: int,
        window_seconds: int,
        session: AsyncSession) -> AlertRule:
    rule = AlertRule(
        tenant_id=tenant_id,
        event_name=event_name,
        threshold=threshold,
        window_seconds=window_seconds,
    )
    session.add(rule)
    await session.commit()
    await session.refresh(rule)
    return rule


async def get_rules_by_tenant(tenant_id: uuid.UUID, session: AsyncSession) -> list[AlertRule]:
    result = await session.execute(
        select(AlertRule).where(AlertRule.tenant_id == tenant_id)
    )
    return list(result.scalars().all())


async def get_rule_by_id(rule_id: uuid.UUID, session: AsyncSession) -> AlertRule | None:
    result = await session.execute(
        select(AlertRule).where(AlertRule.id == rule_id)
    )
    return result.scalar_one_or_none()


async def delete_rule(rule: AlertRule, session: AsyncSession) -> None:
    await session.delete(rule)
    await session.commit()


async def get_active_rules(session: AsyncSession) -> list[AlertRule]:
    result = await session.execute(
        select(AlertRule).where(AlertRule.is_active == True)
    )
    return list(result.scalars().all())


async def get_active_alert(rule_id: uuid.UUID, session: AsyncSession) -> AlertHistory | None:
    result = await session.execute(
        select(AlertHistory)
        .where(AlertHistory.rule_id == rule_id)
        .where(AlertHistory.resolved_at == None)  # noqa: E711
    )
    return result.scalar_one_or_none()


async def create_alert_history(rule_id: uuid.UUID, event_count: int, session: AsyncSession) -> AlertHistory:
    history = AlertHistory(rule_id=rule_id, event_count=event_count)
    session.add(history)
    await session.commit()
    await session.refresh(history)
    return history


async def resolve_alert(alert: AlertHistory, session: AsyncSession) -> None:
    alert.resolved_at = datetime.now(timezone.utc)
    await session.commit()
