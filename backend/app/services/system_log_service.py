from sqlalchemy.orm import Session

from app.models.system_log import SystemLog


def system_log_to_dict(log: SystemLog) -> dict:
    return {
        "id": log.id,
        "email_id": log.email_id,
        "action_type": log.action_type,
        "action_detail": log.action_detail,
        "actor": log.actor,
        "status": log.status,
        "extra_data": log.extra_data,
        "created_at": log.created_at.isoformat() if log.created_at else None,
    }


def create_system_log(
    db: Session,
    action_type: str,
    email_id: int | None = None,
    action_detail: str | None = None,
    actor: str = "system",
    status: str = "success",
    extra_data: dict | None = None,
) -> dict:
    log = SystemLog(
        email_id=email_id,
        action_type=action_type,
        action_detail=action_detail,
        actor=actor,
        status=status,
        extra_data=extra_data,
    )

    db.add(log)
    db.commit()
    db.refresh(log)

    return system_log_to_dict(log)


def get_all_system_logs(db: Session, limit: int = 100) -> list[dict]:
    logs = (
        db.query(SystemLog)
        .order_by(SystemLog.created_at.desc())
        .limit(limit)
        .all()
    )

    return [system_log_to_dict(log) for log in logs]


def get_system_logs_by_email_id(db: Session, email_id: int) -> list[dict]:
    logs = (
        db.query(SystemLog)
        .filter(SystemLog.email_id == email_id)
        .order_by(SystemLog.created_at.desc())
        .all()
    )

    return [system_log_to_dict(log) for log in logs]