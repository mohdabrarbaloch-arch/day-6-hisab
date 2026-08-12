"""Pydantic schemas for request/response validation."""

from __future__ import annotations

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

CURRENCIES = {"USD", "PKR", "EUR", "GBP", "AED", "SAR"}
STATUSES = {"draft", "sent", "paid", "overdue"}


class UserCreate(BaseModel):
    email: EmailStr
    name: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not re.search(r"[A-Za-z]", v) or not re.search(r"\d", v):
            raise ValueError("password must contain at least one letter and one number")
        return v


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    name: str
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ClientCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    company: str | None = Field(default=None, max_length=160)
    email: EmailStr | None = None
    country: str | None = Field(default=None, max_length=80)


class ClientOut(ClientCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    created_at: datetime


class InvoiceItemIn(BaseModel):
    description: str = Field(min_length=2, max_length=255)
    quantity: float = Field(gt=0, le=1_000_000)
    unit_price: float = Field(ge=0, le=1_000_000_000)


class InvoiceCreate(BaseModel):
    client_id: int
    currency: str = Field(default="USD", min_length=3, max_length=3)
    due_date: datetime
    notes: str | None = Field(default=None, max_length=2000)
    items: list[InvoiceItemIn] = Field(min_length=1, max_length=50)

    @field_validator("currency")
    @classmethod
    def valid_currency(cls, v: str) -> str:
        v = v.upper()
        if v not in CURRENCIES:
            raise ValueError(f"currency must be one of {sorted(CURRENCIES)}")
        return v


class InvoiceItemOut(InvoiceItemIn):
    model_config = ConfigDict(from_attributes=True)

    id: int


class InvoiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    invoice_number: str
    currency: str
    issue_date: datetime
    due_date: datetime
    status: str
    notes: str | None
    client: ClientOut
    items: list[InvoiceItemOut]
    subtotal: float
    tax: float
    total: float


class InvoiceListOut(BaseModel):
    id: int
    invoice_number: str
    currency: str
    issue_date: datetime
    due_date: datetime
    status: str
    client_name: str
    total: float


class IncomeSummary(BaseModel):
    currency: str
    usd_to_pkr: float
    total_invoiced: float
    total_paid: float
    total_overdue: float
    total_pending: float
    invoice_count: int
    paid_count: int
    overdue_count: int
    outstanding_pkr: float
