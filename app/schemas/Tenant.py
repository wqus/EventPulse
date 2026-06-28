from pydantic import BaseModel

class TenantCache(BaseModel):
    id: str
    api_key_hash: str
    is_active: bool
    plan: str
