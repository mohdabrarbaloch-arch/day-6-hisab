"""Invoice business logic: totals, numbering, status transitions, income summary."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Client, Invoice, InvoiceItem, User
from app.schemas import IncomeSummary, InvoiceCreate


class InvoiceError(ValueError):
    """Raised for business-rule violations."""


def compute_totals(items: list[InvoiceItem]) -> tuple[float, float, float]:
    subtotal = round(sum((i.quantity or 0) * (i.unit_price or 0) for i in items), 2)
    tax = round(subtotal * 0.05, 2)  # 5% sales tax, configurable later
    return subtotal, tax, round(subtotal + tax, 2)


def next_invoice_number(db: Session, owner_id: int) -> str:
    """Generate the next invoice number like INV-0007, scoped per user."""
    prefix = "INV"
    last = db.scalar(
        select(Invoice.invoice_number)
        .where(Invoice.owner_id == owner_id)
        .order_by(Invoice.invoice_number.desc())
        .limit(1)
    )
    if last is None:
        return f"{prefix}-0001"
    try:
        seq = int(last.split("-")[1]) + 1
    except (IndexError, ValueError):
        seq = 1
    return f"{prefix}-{seq:04d}"


def refresh_status(invoice: Invoice) -> str:
    """Paid stays paid; overdue once past due date; otherwise keep sent/draft."""
    if invoice.status == "paid":
        return "paid"
    now = datetime.now(UTC)
    if invoice.due_date.tzinfo is None:
        due = invoice.due_date.replace(tzinfo=UTC)
    else:
        due = invoice.due_date
    if now > due and invoice.status in {"sent", "draft"}:
        return "overdue"
    return invoice.status


def apply_status_refresh(db: Session, owner_id: int) -> None:
    """Mark any sent invoices past due as overdue (cheap sweep on reads)."""
    now = datetime.now(UTC)
    rows = db.scalars(
        select(Invoice).where(
            Invoice.owner_id == owner_id,
            Invoice.status == "sent",
            Invoice.due_date < now,
        )
    )
    for inv in rows:
        inv.status = "overdue"
    db.commit()


def create_invoice(db: Session, owner: User, data: InvoiceCreate) -> Invoice:
    client = db.get(Client, data.client_id)
    if client is None or client.owner_id != owner.id:
        raise InvoiceError("client not found")
    if data.due_date.tzinfo is None:
        due = data.due_date.replace(tzinfo=UTC)
    else:
        due = data.due_date.astimezone(UTC)
    invoice = Invoice(
        owner_id=owner.id,
        client_id=client.id,
        invoice_number=next_invoice_number(db, owner.id),
        currency=data.currency,
        due_date=due,
        status="draft",
        notes=data.notes,
    )
    db.add(invoice)
    db.flush()
    for item in data.items:
        db.add(
            InvoiceItem(
                invoice_id=invoice.id,
                description=item.description.strip(),
                quantity=item.quantity,
                unit_price=item.unit_price,
            )
        )
    db.commit()
    db.refresh(invoice)
    return invoice


def get_income_summary(db: Session, owner: User) -> IncomeSummary:
    invoices = db.scalars(select(Invoice).where(Invoice.owner_id == owner.id)).all()
    rows = [(inv, compute_totals(inv.items)[2]) for inv in invoices]

    def money(statuses: set[str]) -> float:
        return round(sum(t for inv, t in rows if inv.status in statuses), 2)

    paid = money({"paid"})
    overdue = money({"overdue"})
    pending = money({"sent"})
    invoiced = round(paid + overdue + pending, 2)
    rate = settings.default_usd_to_pkr
    return IncomeSummary(
        currency="USD",
        usd_to_pkr=rate,
        total_invoiced=invoiced,
        total_paid=paid,
        total_overdue=overdue,
        total_pending=pending,
        invoice_count=len(invoices),
        paid_count=sum(1 for i in invoices if i.status == "paid"),
        overdue_count=sum(1 for i in invoices if i.status == "overdue"),
        outstanding_pkr=round((overdue + pending) * rate, 2),
    )


def paid_within_30_days(db: Session, owner_id: int) -> float:
    """Sum of invoices marked paid in the last 30 days (income-report helper)."""
    cutoff = datetime.now(UTC) - timedelta(days=30)
    rows = db.scalars(
        select(Invoice).where(
            Invoice.owner_id == owner_id,
            Invoice.status == "paid",
            Invoice.created_at >= cutoff,
        )
    ).all()
    return round(sum(compute_totals(i.items)[2] for i in rows), 2)


def count_overdue(db: Session, owner_id: int) -> int:
    return (
        db.scalar(
            select(func.count(Invoice.id)).where(
                Invoice.owner_id == owner_id,
                Invoice.status == "overdue",
            )
        )
        or 0
    )
