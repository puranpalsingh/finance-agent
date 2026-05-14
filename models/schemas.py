from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class InvoiceBase(BaseModel):
    invoice_no: str
    customer_name: str
    customer_email: str
    amount_due: float
    due_date: str # YYYY-MM-DD
    
class InvoiceComputed(InvoiceBase):
    days_overdue: int
    stage: str

class EmailGenerationRequest(BaseModel):
    invoice: InvoiceComputed

class EmailGenerationResponse(BaseModel):
    subject: str
    body: str

class SendEmailRequest(BaseModel):
    invoice: InvoiceComputed
    subject: str
    body: str
    dry_run: bool = True

class AuditLogEntry(BaseModel):
    id: Optional[int] = None
    timestamp: datetime
    invoice_no: str
    amount_due: float
    stage: str
    send_status: str
    dry_run: bool

    class Config:
        from_attributes = True
