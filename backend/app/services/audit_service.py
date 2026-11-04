"""后台操作日志：记录关键写操作的审计信息。

只 add 不 commit，随调用方的业务事务一起提交，避免日志与业务数据不一致。
"""

import json
from typing import Any

from sqlalchemy.orm import Session

from app.models import admin_operation_log
from app.repositories import log_admin_repo


def record(
    db: Session,
    admin_id: int,
    module: str,
    action: str,
    target_type: str = "",
    target_id: int | None = None,
    target_name: str = "",
    before: Any = None,
    after: Any = None,
) -> None:
    log_admin_repo.add(
        db,
        admin_operation_log(
            admin_user_id=admin_id,
            module=module,
            action=action,
            target_type=target_type,
            target_id=target_id,
            target_name=(target_name or "")[:255],
            detail_before=json.dumps(before, ensure_ascii=False) if before else None,
            detail_after=json.dumps(after, ensure_ascii=False) if after else None,
        ),
    )
