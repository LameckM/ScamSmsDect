from datetime import datetime

from pydantic import BaseModel, Field


class ReportCreate(BaseModel):
    device_id: str = Field(..., min_length=1, description="Anonymized identifier for the reporting device/user")
    number: str = Field(..., min_length=1, description="The reported phone number")
    message: str = Field(..., min_length=1, description="Full content of the suspicious SMS")

    model_config = {
        "json_schema_extra": {
            "example": {
                "device_id": "device-abc123",
                "number": "+260971234567",
                "message": "Congratulations! You have won K5,000. Send your PIN to claim your prize now.",
            }
        }
    }


class ReportResult(BaseModel):
    """Returned immediately after a report is submitted: the score for this
    message plus the number's new aggregate state."""
    message_score: float
    flags: list[str]
    number: str
    report_count: int
    aggregate_score: float
    status: str


class ReportOut(BaseModel):
    id: int
    message_content: str
    message_score: float
    flags: list[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class PhoneNumberOut(BaseModel):
    number: str
    status: str
    aggregate_score: float
    report_count: int
    updated_at: datetime

    model_config = {"from_attributes": True}


class PhoneNumberDetail(PhoneNumberOut):
    reports: list[ReportOut]


class ModerationAction(BaseModel):
    action: str = Field(..., pattern="^(escalate|clear|reset)$", description="escalate | clear | reset")
