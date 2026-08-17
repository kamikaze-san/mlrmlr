import re
from typing import Optional, List
from pydantic import BaseModel, Field
from solution.extractors.money_parser import parse_money, parse_date, normalize_text

class ProjectCertificateSchema(BaseModel):
    doc_id: str = Field(description="Document ID, e.g. DOC-CC-145")
    package_no: Optional[str] = Field(default=None, description="Package identifier, e.g. Pkg-145")
    project_name: str = Field(description="Name or title of the project")
    client_name: str = Field(description="Client or issuing authority name")
    category: Optional[str] = Field(default=None, description="Work category, e.g. small buildings, bridges flyovers")
    raw_category: Optional[str] = Field(default=None, description="Raw category string from document")
    value_raw: Optional[str] = Field(default=None, description="Raw currency text, e.g. Rs. 3.00 Crore")
    value_inr: int = Field(default=0, description="Lossless integer INR value")
    completion_date_raw: Optional[str] = Field(default=None, description="Raw completion date string")
    completion_date: Optional[str] = Field(default=None, description="ISO YYYY-MM-DD completion date")
    lead_engineer: Optional[str] = Field(default=None, description="Lead engineer or project manager name")
    state: Optional[str] = Field(default="", description="State location")
    ref_letter_code: Optional[str] = Field(default=None, description="Client certificate ref code")
    has_reference_letter: int = Field(default=0, description="1 if reference letter exists, else 0")
    reference_letter_doc_id: Optional[str] = Field(default=None, description="Matched reference letter doc ID")

    @classmethod
    def from_raw(cls, **data) -> "ProjectCertificateSchema":
        val_inr = parse_money(data.get("value_raw", "")) if data.get("value_raw") else data.get("value_inr", 0)
        comp_d = parse_date(data.get("completion_date_raw", "")) if data.get("completion_date_raw") else data.get("completion_date")
        
        # Clean client name
        client = data.get("client_name", "")
        if client:
            client = normalize_text(client)
            client = re.sub(r'\s*\([^)]*\)', '', client).strip()
            if client == 'Irrigation & Waterways Dept, Govt of West':
                client = 'Irrigation & Waterways Dept, Govt of West Bengal'

        # Clean category
        cat = data.get("category", "")
        if cat:
            cat = cat.lower().strip()
            cat = re.sub(r'[^\w\s]', ' ', cat)
            cat = re.sub(r'\s+', ' ', cat).strip()

        return cls(
            doc_id=data.get("doc_id", ""),
            package_no=data.get("package_no"),
            project_name=data.get("project_name", ""),
            client_name=client,
            category=cat,
            raw_category=data.get("raw_category") or data.get("category"),
            value_raw=data.get("value_raw"),
            value_inr=val_inr,
            completion_date_raw=data.get("completion_date_raw"),
            completion_date=comp_d,
            lead_engineer=data.get("lead_engineer"),
            state=data.get("state", ""),
            ref_letter_code=data.get("ref_letter_code"),
            has_reference_letter=data.get("has_reference_letter", 0),
            reference_letter_doc_id=data.get("reference_letter_doc_id")
        )

class PersonnelCertSchema(BaseModel):
    doc_id: str = Field(description="Document ID, e.g. DOC-PCERT-001")
    name: str = Field(description="Engineer name")
    emp_id: Optional[str] = Field(default=None, description="Employee ID")
    cred_type: str = Field(description="Credential type, e.g. PMP, Chartered Engineer, Lead Auditor")
    cred_id: str = Field(description="Credential registration ID")
    issue_date_raw: Optional[str] = Field(default=None, description="Raw issue date string")
    issue_date: Optional[str] = Field(default=None, description="ISO YYYY-MM-DD issue date")

    @classmethod
    def from_raw(cls, **data) -> "PersonnelCertSchema":
        issue_d = parse_date(data.get("issue_date_raw", "")) if data.get("issue_date_raw") else data.get("issue_date")
        return cls(
            doc_id=data.get("doc_id", ""),
            name=data.get("name", "").strip(),
            emp_id=data.get("emp_id"),
            cred_type=data.get("cred_type", "").strip(),
            cred_id=data.get("cred_id", "").strip(),
            issue_date_raw=data.get("issue_date_raw"),
            issue_date=issue_d
        )

class CVResumeSchema(BaseModel):
    doc_id: str = Field(description="Document ID, e.g. DOC-CV-001")
    name: str = Field(description="Engineer name")
    emp_id: Optional[str] = Field(default=None, description="Employee ID")
    designation: Optional[str] = Field(default=None, description="Designation, e.g. Senior Project Manager")
    business_unit: Optional[str] = Field(default=None, description="Business unit")

class ReceivablesRecordSchema(BaseModel):
    invoice_no: str = Field(description="Invoice reference number")
    client_name: str = Field(description="Client name")
    invoice_date: Optional[str] = Field(default=None, description="ISO date of invoice")
    invoiced_inr: int = Field(default=0, description="Total invoiced amount in INR")
    received_inr: int = Field(default=0, description="Total received/settled amount in INR")
    outstanding_inr: int = Field(default=0, description="Outstanding amount in INR")
