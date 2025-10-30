from pydantic import BaseModel, EmailStr
from typing import Optional, List

class UserSignup(BaseModel):
    name: str
    email: EmailStr
    password: str
    grade: str
    role: str
    school: str = ""
    zipCode: str = ""

class UserLogin(BaseModel):
    email: EmailStr
    password: str

# Models for scheduling (if you have them)
class TimeSlot(BaseModel):
    day: str
    start_time: str
    end_time: str

class AvailabilityUpdate(BaseModel):
    email: str
    time_slots: List[dict]