"""Client CRUD."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Client, Invoice, User
from app.schemas import ClientCreate, ClientOut

router = APIRouter(prefix="/api/clients", tags=["clients"])


def _get_owned_client(db: Session, owner: User, client_id: int) -> Client:
    client = db.get(Client, client_id)
    if client is None or client.owner_id != owner.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    return client


@router.get("", response_model=list[ClientOut])
def list_clients(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.scalars(select(Client).where(Client.owner_id == current_user.id)).all()


@router.post("", response_model=ClientOut, status_code=status.HTTP_201_CREATED)
def create_client(
    payload: ClientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Client:
    client = Client(
        owner_id=current_user.id,
        name=payload.name.strip(),
        company=payload.company.strip() if payload.company else None,
        email=payload.email.lower() if payload.email else None,
        country=payload.country.strip() if payload.country else None,
    )
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


@router.get("/{client_id}", response_model=ClientOut)
def get_client(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Client:
    return _get_owned_client(db, current_user, client_id)


@router.put("/{client_id}", response_model=ClientOut)
def update_client(
    client_id: int,
    payload: ClientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Client:
    client = _get_owned_client(db, current_user, client_id)
    client.name = payload.name.strip()
    client.company = payload.company.strip() if payload.company else None
    client.email = payload.email.lower() if payload.email else None
    client.country = payload.country.strip() if payload.country else None
    db.commit()
    db.refresh(client)
    return client


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    client = _get_owned_client(db, current_user, client_id)
    if db.scalar(select(Invoice.id).where(Invoice.client_id == client.id).limit(1)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Client has invoices — delete those first",
        )
    db.delete(client)
    db.commit()
