"""Service-layer unit tests: totals, numbering, status sweep, summary."""

from datetime import UTC, datetime, timedelta

from app.models import Invoice, InvoiceItem, User
from app.services.invoice_service import (
    compute_totals,
    get_income_summary,
    next_invoice_number,
    refresh_status,
)


def make_items():
    return [
        InvoiceItem(description="A", quantity=2, unit_price=50),
        InvoiceItem(description="B", quantity=1, unit_price=100),
    ]


def test_compute_totals_rounding():
    items = [InvoiceItem(description="A", quantity=3, unit_price=10.333)]
    subtotal, tax, total = compute_totals(items)
    assert subtotal == 31.0
    assert tax == round(31.0 * 0.05, 2)
    assert total == round(subtotal + tax, 2)


def test_compute_totals_zero_items():
    subtotal, tax, total = compute_totals([])
    assert (subtotal, tax, total) == (0.0, 0.0, 0.0)


def test_compute_totals_simple():
    subtotal, tax, total = compute_totals(make_items())
    assert subtotal == 200.0
    assert tax == 10.0
    assert total == 210.0


def test_next_invoice_number_starts_at_one(db):
    user = User(email="x@y.com", name="T", hashed_password="h")
    db.add(user)
    db.commit()
    assert next_invoice_number(db, user.id) == "INV-0001"


def test_next_invoice_number_increments(db):
    user = User(email="x@y.com", name="T", hashed_password="h")
    db.add(user)
    db.commit()
    db.add(
        Invoice(
            owner_id=user.id,
            client_id=0,
            invoice_number="INV-0003",
            due_date=datetime.now(UTC),
            status="draft",
        )
    )
    db.commit()
    assert next_invoice_number(db, user.id) == "INV-0004"


def test_refresh_status_paid_stays_paid():
    inv = Invoice(status="paid", due_date=datetime.now(UTC) - timedelta(days=5))
    assert refresh_status(inv) == "paid"


def test_refresh_status_becomes_overdue():
    inv = Invoice(status="sent", due_date=datetime.now(UTC) - timedelta(days=1))
    assert refresh_status(inv) == "overdue"


def test_refresh_status_future_due_stays_sent():
    inv = Invoice(status="sent", due_date=datetime.now(UTC) + timedelta(days=7))
    assert refresh_status(inv) == "sent"


def test_income_summary_empty(db):
    user = User(email="x@y.com", name="T", hashed_password="h")
    db.add(user)
    db.commit()
    s = get_income_summary(db, user)
    assert s.total_invoiced == 0.0
    assert s.invoice_count == 0


def test_income_summary_counts(db):
    user = User(email="x@y.com", name="T", hashed_password="h")
    db.add(user)
    db.commit()
    now = datetime.now(UTC)
    for status, price in [("paid", 100), ("overdue", 200), ("sent", 300)]:
        inv = Invoice(
            owner_id=user.id,
            client_id=0,
            invoice_number=f"INV-{status}",
            due_date=now,
            status=status,
        )
        db.add(inv)
        db.flush()
        db.add(InvoiceItem(invoice_id=inv.id, description=status, quantity=1, unit_price=price))
    db.commit()
    s = get_income_summary(db, user)
    # totals include 5% tax: 100 → 105, 200 → 210, 300 → 315
    assert s.total_paid == 105.0
    assert s.total_overdue == 210.0
    assert s.total_pending == 315.0
    assert s.total_invoiced == 630.0
    assert s.overdue_count == 1
    assert s.paid_count == 1
    assert s.outstanding_pkr == round(525.0 * 280.0, 2)
