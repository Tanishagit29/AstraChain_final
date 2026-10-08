from typing import Optional
from pydantic import BaseModel

class ReportOut(BaseModel):
    id: str
    title: str
    date: str
    type: str
    author: str
    size: str

class ReportGenerateRequest(BaseModel):
    title: str
    report_type: str
    time_range: str = "Q4"
