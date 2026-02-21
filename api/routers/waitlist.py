"""
Waitlist router — public email capture endpoint.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func

from api.database import Base, get_db, engine

router = APIRouter(prefix='/api/waitlist', tags=['waitlist'])


class WaitlistEntry(Base):
    __tablename__ = 'waitlist_entries'
    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(100))
    source = Column(String(50), default='landing')   # 'landing', 'waitlist_page', etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# Create table on import (safe — IF NOT EXISTS)
WaitlistEntry.__table__.create(bind=engine, checkfirst=True)


class JoinRequest(BaseModel):
    email: EmailStr
    name: str | None = None
    source: str | None = 'landing'


class JoinResponse(BaseModel):
    success: bool
    message: str
    count: int


@router.post('', response_model=JoinResponse)
def join_waitlist(body: JoinRequest, db: Session = Depends(get_db)):
    existing = db.query(WaitlistEntry).filter(WaitlistEntry.email == body.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="You're already on the waitlist!")

    entry = WaitlistEntry(
        email=body.email,
        name=body.name,
        source=body.source or 'landing',
    )
    db.add(entry)
    db.commit()

    count = db.query(WaitlistEntry).count()
    return JoinResponse(
        success=True,
        message="You're on the list! We'll be in touch.",
        count=count,
    )


@router.get('/count')
def get_waitlist_count(db: Session = Depends(get_db)):
    count = db.query(WaitlistEntry).count()
    return {'count': count}
