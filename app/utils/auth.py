import jwt
import datetime
from typing import Dict, Optional

class AuthManager:
    def __init__(self, secret_key: str):
        self.secret_key = secret_key
        self.role_permissions = {
            "Admin": ["read_all", "write_all", "manage_tenants"],
            "Recruiter": ["read_tenant", "write_tenant"],
            "Client": ["read_matches"]
        }

    def generate_token(self, user_id: str, tenant_id: str, role: str) -> str:
        payload = {
            "user_id": user_id,
            "tenant_id": tenant_id,
            "role": role,
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        }
        return jwt.encode(payload, self.secret_key, algorithm="HS256")

    def verify_token(self, token: str) -> Optional[Dict]:
        try:
            return jwt.decode(token, self.secret_key, algorithms=["HS256"])
        except Exception:
            return None

    def check_permission(self, role: str, required_permission: str) -> bool:
        return required_permission in self.role_permissions.get(role, [])
