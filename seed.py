"""Seed a demo user + sample clients/invoices for local testing."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.models import Client, Invoice, InvoiceItem, User
from app.security import hash_password

Base.metadata.create_all(bind=engine)

db = SessionLocal()
try:
    if db.scalar(select(User).where(User.email == "demo@hisab.pk")):
        print("Demo user already exists — nothing to do.")
        raise SystemExit(0)

    user = User(
        email="demo@hisab.pk",
        name="Abrar Demo",
        hashed_password=hash_password("demo1234"),
    )
    db.add(user)
    db.flush()

    now = datetime.now(UTC)
    clients = [
        Client(
            owner_id=user.id,
            name="Upwork Client",
            company="PixelWorks LLC",
            email="pixel@example.com",
            country="United States",
        ),
        Client(owner_id=user.id, name="Fiverr Buyer", company="Studio Nine", country="UAE"),
        Client(owner_id=user.id, name="Local Startup", company="Karachi Labs", country="Pakistan"),
    ]
    db.add_all(clients)
    db.flush()

    invoices = [
        Invoice(
            owner_id=user.id,
            client_id=clients[0].id,
            invoice_number="INV-0001",
            currency="USD",
            due_date=now + timedelta(days=10),
            status="sent",
        ),
        Invoice(
            owner_id=user.id,
            client_id=clients[1].id,
            invoice_number="INV-0002",
            currency="USD",
            due_date=now - timedelta(days=5),
            status="overdue",
        ),
        Invoice(
            owner_id=user.id,
            client_id=clients[2].id,
            invoice_number="INV-0003",
            currency="PKR",
            due_date=now + timedelta(days=20),
            status="paid",
        ),
    ]
    db.add_all(invoices)
    db.flush()

    items = [
        InvoiceItem(
            invoice_id=invoices[0].id,
            description="Landing page design",
            quantity=1,
            unit_price=1200,
        ),
        InvoiceItem(
            invoice_id=invoices[0].id, description="UI/UX revisions", quantity=2, unit_price=150
        ),
        InvoiceItem(
            invoice_id=invoices[1].id, description="Mobile app screens", quantity=5, unit_price=90
        ),
        InvoiceItem(
            invoice_id=invoices[2].id, description="SEO audit", quantity=1, unit_price=45000
        ),
    ]
    db.add_all(items)
    db.commit()
    print("Seed complete — demo@hisab.pk / demo1234")
finally:
    db.close()
