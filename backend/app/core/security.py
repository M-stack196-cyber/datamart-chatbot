from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Dummy authentication for now. Replace with real auth."""
    token = credentials.credentials
    
    class MockUser:
        def __init__(self):
            self.id = 1
            self.full_name = "Admin User"
            self.first_name = "Admin"
            self.email = "admin@datamart.com"
            self.role = "admin"
            self.phone = "+1 555-000-0000"
    
    return MockUser()
