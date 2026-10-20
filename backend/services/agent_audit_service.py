"""Agent audit event logging."""
import logging
from typing import Optional
from db import get_db

logger = logging.getLogger(__name__)


def log(actor_user_id: str, action: str, target_user_id: Optional[str] = None, detail: str = ""):
    try:
        with get_db() as conn:
            conn.cursor().execute(
                "INSERT INTO agent_audit_events (actor_user_id, action, target_user_id, detail) VALUES (%s,%s,%s,%s)",
                (actor_user_id, action, target_user_id, detail[:500]),
            )
    except Exception as e:
        logger.debug("audit log write failed: %s", e)
