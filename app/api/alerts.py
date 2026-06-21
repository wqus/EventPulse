import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_tenant_by_api_key
from app.core.database import get_session
from app.models.Tenant import Tenant
from app.schemas.AlertRule import AlertRuleCreate, AlertRuleResponse
from app.repositories import alert as alert_repo

router = APIRouter()


@router.post("/alerts", response_model=AlertRuleResponse)
async def create_alert(data: AlertRuleCreate,tenant: Tenant = Depends(get_tenant_by_api_key),session: AsyncSession = Depends(get_session),):
    if not tenant.telegram_chat_id:
        raise HTTPException(
            status_code=400,
            detail="Telegram not linked. Send /start <api_key> to the bot first."
        )

    rule = await alert_repo.create_rule(
        tenant_id=tenant.id,
        event_name=data.event_name,
        threshold=data.threshold,
        window_seconds=data.window_seconds,
        session=session,
    )
    return rule


@router.get("/alerts", response_model=list[AlertRuleResponse])
async def list_alerts(tenant: Tenant = Depends(get_tenant_by_api_key),session: AsyncSession = Depends(get_session),):
    return await alert_repo.get_rules_by_tenant(tenant.id, session)


@router.delete("/alerts/{rule_id}")
async def delete_alert(rule_id: uuid.UUID, tenant: Tenant = Depends(get_tenant_by_api_key),session: AsyncSession = Depends(get_session), ):
    rule = await alert_repo.get_rule_by_id(rule_id, session)

    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    if rule.tenant_id != tenant.id:
        raise HTTPException(status_code=403, detail="Not your rule")

    await alert_repo.delete_rule(rule, session)
    return {"status": "deleted"}
