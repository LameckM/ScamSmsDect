"""
Database models. Four tables, matching the "Data Layer" section of the
project proposal:
  - reporters      -> reporter trust database
  - phone_numbers   -> the flagged/monitored numbers themselves
  - reports         -> reports database
  - scam_patterns   -> scam pattern database (grows as moderators confirm scams)
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, Text, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Reporter(Base):
    """
    A person/device that submits reports. Identified by an anonymized
    device_id rather than a phone number or account, per the proposal's
    privacy considerations — the reporter's identity is not tied to their
    real-world contact details.
    """
    __tablename__ = "reporters"

    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)

    # 0.0-1.0. Starts at 1.0 (full trust) for new reporters. A moderator or
    # future automated process can lower this for reporters whose past
    # reports were dismissed as false, which is the system's main defense
    # against coordinated false-flagging campaigns.
    trust_score: Mapped[float] = mapped_column(Float, default=1.0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    reports: Mapped[list["Report"]] = relationship(back_populates="reporter")


class PhoneNumber(Base):
    """A reported number and its current aggregate risk state."""
    __tablename__ = "phone_numbers"

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(String(32), unique=True, index=True)

    # "monitoring" | "flagged" | "escalated" | "cleared"
    status: Mapped[str] = mapped_column(String(20), default="monitoring")
    aggregate_score: Mapped[float] = mapped_column(Float, default=0.0)

    # Set by a moderator via POST /numbers/{number}/moderate. Once set, it
    # overrides automatic status calculation until explicitly reset — this
    # is the human-in-the-loop checkpoint from the system architecture.
    manual_override: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    reports: Mapped[list["Report"]] = relationship(back_populates="phone_number", order_by="Report.created_at")


class Report(Base):
    """A single submitted report: one message, from one reporter, about one number."""
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    phone_number_id: Mapped[int] = mapped_column(ForeignKey("phone_numbers.id"), index=True)
    reporter_id: Mapped[int] = mapped_column(ForeignKey("reporters.id"), index=True)

    message_content: Mapped[str] = mapped_column(Text)
    message_score: Mapped[float] = mapped_column(Float)
    flags: Mapped[list] = mapped_column(JSON, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    phone_number: Mapped["PhoneNumber"] = relationship(back_populates="reports")
    reporter: Mapped["Reporter"] = relationship(back_populates="reports")


class ScamPattern(Base):
    """
    A keyword/phrase in the scam-pattern corpus, grouped by category. Seeded
    with defaults on first run (see seed_data.py); intended to be extended
    over time as moderators confirm new scam wording.
    """
    __tablename__ = "scam_patterns"

    id: Mapped[int] = mapped_column(primary_key=True)
    phrase: Mapped[str] = mapped_column(String(128), unique=True)
    category: Mapped[str] = mapped_column(String(32))  # lottery | urgency | money | sensitive_info
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ReportReview(Base):
    """Latest moderator-confirmed label for an individual message report."""
    __tablename__ = "report_reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("reports.id"), unique=True, index=True)
    label: Mapped[str] = mapped_column(String(16))  # scam | legitimate
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    report: Mapped["Report"] = relationship()
