from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_
from typing import Optional
from datetime import datetime, timedelta
from app.database import get_db
from app.models.contact_info import ContactInfo
from app.models.project_requests import ProjectRequest
from app.models.user import User
from app.schemas.lead import LeadUpdate
from app.schemas.project_request import ProjectRequestUpdate
from app.core.security import get_current_user
import csv
from io import StringIO
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/admin/leads", tags=["Admin - Leads"])

# ==========================================
# EXTERNAL LEADS MANAGEMENT
# ==========================================

@router.get("/external")
async def get_external_leads(
    status: Optional[str] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="Search by name/email/project"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all external leads with pagination and filters"""
    
    if current_user.role not in ["admin", "cto", "pmo"]:
        raise HTTPException(403, "Insufficient permissions")
    
    query = db.query(ContactInfo)
    
    # Apply filters
    if status:
        query = query.filter(ContactInfo.status == status)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                ContactInfo.name.ilike(search_term),
                ContactInfo.email.ilike(search_term),
                ContactInfo.project_title.ilike(search_term),
                ContactInfo.project_description.ilike(search_term)
            )
        )
    
    # Get total count for pagination
    total = query.count()
    
    # Apply pagination and sorting
    leads = query.order_by(desc(ContactInfo.created_at))\
                 .offset((page - 1) * limit)\
                 .limit(limit)\
                 .all()
    
    return {
        "leads": leads,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit
        },
        "status_counts": {
            "new": db.query(ContactInfo).filter(ContactInfo.status == "new").count(),
            "contacted": db.query(ContactInfo).filter(ContactInfo.status == "contacted").count(),
            "qualified": db.query(ContactInfo).filter(ContactInfo.status == "qualified").count(),
            "closed": db.query(ContactInfo).filter(ContactInfo.status == "closed").count()
        }
    }

@router.get("/external/{lead_id}")
async def get_external_lead(
    lead_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific lead with conversation history"""
    
    if current_user.role not in ["admin", "cto", "pmo"]:
        raise HTTPException(403, "Insufficient permissions")
    
    lead = db.query(ContactInfo).filter(ContactInfo.id == lead_id).first()
    if not lead:
        raise HTTPException(404, "Lead not found")
    
    return {
        "lead": lead,
        "messages": lead.messages
    }

@router.patch("/external/{lead_id}")
async def update_external_lead(
    lead_id: int,
    update_data: LeadUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update lead status or details"""
    
    if current_user.role not in ["admin", "cto", "pmo"]:
        raise HTTPException(403, "Insufficient permissions")
    
    lead = db.query(ContactInfo).filter(ContactInfo.id == lead_id).first()
    if not lead:
        raise HTTPException(404, "Lead not found")
    
    for field, value in update_data.dict(exclude_unset=True).items():
        setattr(lead, field, value)
    
    lead.updated_by = current_user.id
    lead.updated_at = datetime.now()
    
    db.commit()
    db.refresh(lead)
    
    return lead

# ==========================================
# INTERNAL PROJECT REQUESTS MANAGEMENT
# ==========================================

@router.get("/internal")
async def get_internal_requests(
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all internal project requests"""
    
    if current_user.role not in ["admin", "cto", "pmo"]:
        raise HTTPException(403, "Insufficient permissions")
    
    query = db.query(ProjectRequest)
    
    if status:
        query = query.filter(ProjectRequest.status == status)
    if priority:
        query = query.filter(ProjectRequest.priority == priority)
    
    total = query.count()
    requests = query.order_by(desc(ProjectRequest.created_at))\
                   .offset((page - 1) * limit)\
                   .limit(limit)\
                   .all()
    
    return {
        "requests": requests,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit
        },
        "status_counts": {
            "pending": db.query(ProjectRequest).filter(ProjectRequest.status == "pending").count(),
            "reviewed": db.query(ProjectRequest).filter(ProjectRequest.status == "reviewed").count(),
            "approved": db.query(ProjectRequest).filter(ProjectRequest.status == "approved").count(),
            "in_progress": db.query(ProjectRequest).filter(ProjectRequest.status == "in_progress").count(),
            "completed": db.query(ProjectRequest).filter(ProjectRequest.status == "completed").count()
        }
    }

@router.patch("/internal/{request_id}")
async def update_internal_request(
    request_id: int,
    update_data: ProjectRequestUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update project request status or details"""
    
    if current_user.role not in ["admin", "cto", "pmo"]:
        raise HTTPException(403, "Insufficient permissions")
    
    request = db.query(ProjectRequest).filter(ProjectRequest.id == request_id).first()
    if not request:
        raise HTTPException(404, "Request not found")
    
    for field, value in update_data.dict(exclude_unset=True).items():
        setattr(request, field, value)
    
    request.updated_at = datetime.now()
    db.commit()
    db.refresh(request)
    
    return request

# ==========================================
# CSV EXPORT
# ==========================================

@router.get("/export/csv")
async def export_leads_csv(
    status: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export leads to CSV"""
    
    if current_user.role not in ["admin", "cto", "pmo"]:
        raise HTTPException(403, "Insufficient permissions")
    
    query = db.query(ContactInfo)
    
    if status:
        query = query.filter(ContactInfo.status == status)
    
    if date_from:
        query = query.filter(ContactInfo.created_at >= datetime.fromisoformat(date_from))
    if date_to:
        query = query.filter(ContactInfo.created_at <= datetime.fromisoformat(date_to))
    
    leads = query.order_by(desc(ContactInfo.created_at)).all()
    
    # Create CSV
    output = StringIO()
    writer = csv.writer(output)
    
    writer.writerow([
        "ID", "Date", "Name", "Email", "Phone", "Company", "Country",
        "Project Title", "Project Description", "Industry", "Budget",
        "Timeline", "Contact Method", "Status", "Lead Score"
    ])
    
    for lead in leads:
        writer.writerow([
            lead.id,
            lead.created_at.strftime("%Y-%m-%d %H:%M"),
            lead.name,
            lead.email,
            lead.phone,
            lead.company or "",
            lead.country or "",
            lead.project_title or "",
            lead.project_description,
            lead.industry or "",
            lead.budget or "",
            lead.timeline or "",
            lead.preferred_contact_method or "",
            lead.status,
            lead.lead_score or 0
        ])
    
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=leads_{datetime.now().strftime('%Y%m%d')}.csv"
        }
    )

# ==========================================
# DASHBOARD STATISTICS
# ==========================================

@router.get("/stats")
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get dashboard statistics"""
    
    if current_user.role not in ["admin", "cto", "pmo"]:
        raise HTTPException(403, "Insufficient permissions")
    
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    external_stats = {
        "total": db.query(ContactInfo).count(),
        "new_today": db.query(ContactInfo).filter(ContactInfo.created_at >= today_start).count(),
        "by_status": {
            status: db.query(ContactInfo).filter(ContactInfo.status == status).count()
            for status in ["new", "contacted", "qualified", "closed"]
        }
    }
    
    internal_stats = {
        "total": db.query(ProjectRequest).count(),
        "pending": db.query(ProjectRequest).filter(ProjectRequest.status == "pending").count(),
        "in_progress": db.query(ProjectRequest).filter(ProjectRequest.status == "in_progress").count(),
        "by_priority": {
            priority: db.query(ProjectRequest).filter(ProjectRequest.priority == priority).count()
            for priority in ["high", "medium", "low"]
        }
    }
    
    recent_leads = db.query(ContactInfo)\
                     .filter(ContactInfo.created_at >= (now - timedelta(days=7)))\
                     .order_by(desc(ContactInfo.created_at))\
                     .limit(10)\
                     .all()
    
    return {
        "external": external_stats,
        "internal": internal_stats,
        "recent_leads": recent_leads,
        "timestamp": now.isoformat()
    }