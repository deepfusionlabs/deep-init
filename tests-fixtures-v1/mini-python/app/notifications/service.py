from app.tasks.service import list_tasks
from sqlalchemy.orm import Session
import hashlib

# IP: Email sending via SMTP (simulated)
# BR: Notification deduplication — same task+user combo only notified once per day
_sent_today = set()

def send_task_reminder(db: Session, owner_id: str):
    """Send reminders for pending tasks. Deduplicated per day."""
    tasks = list_tasks(db, owner_id)
    pending = [t for t in tasks if t.status == "pending"]
    sent_count = 0
    for task in pending:
        dedup_key = hashlib.md5(f"{task.id}:{owner_id}:{__today()}".encode()).hexdigest()
        if dedup_key in _sent_today:
            continue
        _send_email(owner_id, f"Reminder: {task.title} is still pending")
        _sent_today.add(dedup_key)
        sent_count += 1
    return {"sent": sent_count, "pending_tasks": len(pending)}

def _send_email(to: str, subject: str):
    # TODO: Implement real SMTP sending
    print(f"[EMAIL] To: {to} | Subject: {subject}")

def _today():
    from datetime import date
    return date.today().isoformat()

def __today():
    from datetime import date
    return date.today().isoformat()
