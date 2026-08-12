"""Invoice endpoints: CRUD + status transitions + list/summary."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Invoice, User
from app.schemas import InvoiceCreate, InvoiceListOut, InvoiceOut
from app.services.invoice_service import (
    InvoiceError,
    apply_status_refresh,
    compute_totals,
    create_invoice,
    refresh_status,
)

router = APIRouter(prefix="/api/invoices", tags=["invoices"])


def _get_owned_invoice(db: Session, owner: User, invoice_id: int) -> Invoice:
    invoice = db.get(Invoice, invoice_id)
    if invoice is None or invoice.owner_id != owner.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    return invoice


def _to_out(invoice: Invoice) -> InvoiceOut:
    subtotal, tax, total = compute_totals(invoice.items)
    return InvoiceOut(
        id=invoice.id,
        invoice_number=invoice.invoice_number,
        currency=invoice.currency,
        issue_date=invoice.issue_date,
        due_date=invoice.due_date,
        status=invoice.status,
        notes=invoice.notes,
        client=invoice.client,
        items=invoice.items,
        subtotal=subtotal,
        tax=tax,
        total=total,
    )


@router.get("", response_model=list[InvoiceListOut])
def list_invoices(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    status_filter: str | None = Query(default=None, alias="status"),
):
    apply_status_refresh(db, current_user.id)
    stmt = select(Invoice).where(Invoice.owner_id == current_user.id)
    if status_filter:
        stmt = stmt.where(Invoice.status == status_filter)
    invoices = db.scalars(stmt).all()
    return [
        InvoiceListOut(
            id=i.id,
            invoice_number=i.invoice_number,
            currency=i.currency,
            issue_date=i.issue_date,
            due_date=i.due_date,
            status=i.status,
            client_name=i.client.name,
            total=compute_totals(i.items)[2],
        )
        for i in invoices
    ]


@router.post("", response_model=InvoiceOut, status_code=status.HTTP_201_CREATED)
def create(
    payload: InvoiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        invoice = create_invoice(db, current_user, payload)
    except InvoiceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _to_out(invoice)


@router.get("/{invoice_id}", response_model=InvoiceOut)
def get(
    invoice_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    invoice = _get_owned_invoice(db, current_user, invoice_id)
    invoice.status = refresh_status(invoice)
    db.commit()
    db.refresh(invoice)
    return _to_out(invoice)


@router.post("/{invoice_id}/send", response_model=InvoiceOut)
def mark_sent(
    invoice_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    invoice = _get_owned_invoice(db, current_user, invoice_id)
    if invoice.status == "paid":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Paid invoice cannot be re-sent"
        )
    invoice.status = "sent"
    db.commit()
    db.refresh(invoice)
    return _to_out(invoice)


@router.post("/{invoice_id}/pay", response_model=InvoiceOut)
def mark_paid(
    invoice_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    invoice = _get_owned_invoice(db, current_user, invoice_id)
    invoice.status = "paid"
    db.commit()
    db.refresh(invoice)
    return _to_out(invoice)


@router.delete("/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(
    invoice_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> None:
    invoice = _get_owned_invoice(db, current_user, invoice_id)
    db.delete(invoice)
    db.commit()
