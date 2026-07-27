from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_role
from app.models import STAFF_ROLES, User
from app.models.contact_info import ContactInfo
from app.models.conversation_state import ConversationState
from app.models.conversation_history import ConversationHistory

router = APIRouter(prefix="/admin", tags=["Admin - Delete"])


@router.delete("/leads/{lead_id}")
def delete_lead(
    lead_id: int,
    current_user: User = Depends(require_role(*STAFF_ROLES)),
    db: Session = Depends(get_db),
):
    """Delete a lead from the database. Only staff members can delete leads."""
    lead = db.query(ContactInfo).filter(ContactInfo.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Also clean up related conversation data
    if lead.conversation_id:
        # Delete conversation history
        db.query(ConversationHistory).filter(
            ConversationHistory.conversation_id == lead.conversation_id
        ).delete()
        # Delete conversation state
        db.query(ConversationState).filter(
            ConversationState.conversation_id == lead.conversation_id
        ).delete()
    
    db.delete(lead)
    db.commit()
    
    return {"message": "Lead deleted successfully"}


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    current_user: User = Depends(require_role(*STAFF_ROLES)),
    db: Session = Depends(get_db),
):
    """Delete a user from the database. Cannot delete admin or CEO users."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent deletion of admin and CEO accounts
    if user.role in ["admin", "ceo"]:
        raise HTTPException(
            status_code=403, 
            detail="Cannot delete admin or CEO users"
        )
    
    # Prevent self-deletion
    if user.id == current_user.id:
        raise HTTPException(
            status_code=403, 
            detail="You cannot delete your own account"
        )
    
    db.delete(user)
    db.commit()
    
    return {"message": f"User {user.display_name} deleted successfully"}
