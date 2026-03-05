import logging
import os
from datetime import datetime

class AuditLogger:
    def __init__(self, log_dir="headhunting_engine/logs/audit"):
        os.makedirs(log_dir, exist_ok=True)
        self.log_path = os.path.join(log_dir, f"audit_{datetime.now().strftime('%Y%m')}.log")
        
        logging.basicConfig(
            filename=self.log_path,
            level=logging.INFO,
            format='%(asctime)s | %(levelname)s | [%(tenant_id)s] | %(user_id)s | %(action)s | %(status)s'
        )
        self.logger = logging.getLogger("AuditLogger")

    def log_event(self, tenant_id: str, user_id: str, action: str, status: str = "SUCCESS"):
        self.logger.info(
            f"Action performed",
            extra={
                "tenant_id": tenant_id,
                "user_id": user_id,
                "action": action,
                "status": status
            }
        )
