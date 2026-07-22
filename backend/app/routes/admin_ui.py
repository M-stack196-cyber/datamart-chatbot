from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.contact_info import ContactInfo

router = APIRouter(prefix="/admin", tags=["admin-ui"])

@router.get("/leads", response_class=HTMLResponse)
def view_leads(db: Session = Depends(get_db)):
    leads = db.query(ContactInfo).order_by(ContactInfo.created_at.desc()).all()
    
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Leads Dashboard</title>
        <style>
            body { font-family: Arial; padding: 20px; background: #f5f7fa; }
            h1 { color: #2c3e50; }
            .card { background: white; border-radius: 8px; padding: 20px; margin: 10px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            table { width: 100%; border-collapse: collapse; }
            th, td { padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }
            th { background: #3498db; color: white; }
            tr:hover { background: #f1f1f1; }
            .status-new { background: #2ecc71; color: white; padding: 4px 8px; border-radius: 4px; }
            .status-contacted { background: #f1c40f; padding: 4px 8px; border-radius: 4px; }
            .status-qualified { background: #3498db; color: white; padding: 4px 8px; border-radius: 4px; }
            .status-closed { background: #95a5a6; color: white; padding: 4px 8px; border-radius: 4px; }
        </style>
    </head>
    <body>
        <h1>📊 Lead Dashboard</h1>
        <p>Total Leads: <strong>""" + str(len(leads)) + """</strong></p>
        
        <div class="card">
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Name</th>
                        <th>Email</th>
                        <th>Phone</th>
                        <th>Project</th>
                        <th>Budget</th>
                        <th>Timeline</th>
                        <th>Status</th>
                        <th>Date</th>
                    </tr>
                </thead>
                <tbody>
    """
    
    for lead in leads:
        status_class = f"status-{lead.status}"
        html += f"""
            <tr>
                <td>{lead.id}</td>
                <td><strong>{lead.name}</strong></td>
                <td>{lead.email}</td>
                <td>{lead.phone}</td>
                <td>{lead.project_title or 'N/A'}</td>
                <td>{lead.budget or 'N/A'}</td>
                <td>{lead.timeline or 'N/A'}</td>
                <td><span class="{status_class}">{lead.status}</span></td>
                <td>{lead.created_at.strftime('%Y-%m-%d %H:%M')}</td>
            </tr>
        """
    
    html += """
                </tbody>
            </table>
        </div>
        <p style="color: #7f8c8d; margin-top: 20px;">📌 Lead capture system running</p>
    </body>
    </html>
    """
    return html
