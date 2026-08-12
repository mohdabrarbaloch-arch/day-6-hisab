"""Dashboard stats: income summary + recent invoices + counts."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Invoice, User
from app.schemas import IncomeSummary
from app.services.invoice_service import count_overdue, get_income_summary, paid_within_30_days

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("/summary", response_model=IncomeSummary)
def summary(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return get_income_summary(db, current_user)


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    summary_data = get_income_summary(db, current_user)
    recent = db.scalars(
        select(Invoice)
        .where(Invoice.owner_id == current_user.id)
        .order_by(Invoice.created_at.desc())
        .limit(5)
    ).all()
    from app.routers.invoices import _to_out

    return {
        "summary": summary_data.model_dump(),
        "paid_30d": paid_within_30_days(db, current_user.id),
        "overdue_count": count_overdue(db, current_user.id),
        "recent_invoices": [_to_out(i).model_dump() for i in recent],
    }
