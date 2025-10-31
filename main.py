from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles
from dotenv import load_dotenv
import os
from database import db, users_collection, sessions_collection, notifications_collection, availability_collection
from models import UserSignup, UserLogin
from auth import hash_password, verify_password, create_access_token
from datetime import datetime

# Load environment variables
load_dotenv()

# Helper function to create notifications
def create_notification(user_email, message, notification_type):
    """Helper function to create a notification"""
    notification = {
        "user_email": user_email,
        "message": message,
        "type": notification_type,
        "read": False,
        "created_at": datetime.utcnow()
    }
    notifications_collection.insert_one(notification)

# Create FastAPI app
app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://10.0.0.23:3000",
        "https://studierbridge.vercel.app",
        "https://studierbridge-git-main-monish-cloud8s-projects.vercel.app",
        "https://studierbridge-*.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files for uploads
UPLOADS_DIR = os.path.join(os.path.dirname(__file__), "uploads")
AVATARS_DIR = os.path.join(UPLOADS_DIR, "avatars")
os.makedirs(AVATARS_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")

# Test routes
@app.get("/")
def read_root():
    return {"message": "Studier Bridge API is running!"}

@app.get("/api/test")
def test_route():
    return {"status": "success", "message": "Backend is working!"}

@app.get("/api/db-test")
def test_database():
    try:
        user_count = users_collection.count_documents({})
        return {"status": "success", "message": "MongoDB connected!", "user_count": user_count}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# SIGNUP ROUTE
# SIGNUP ROUTE
@app.post("/api/signup")
def signup(user: UserSignup):
    print("=== SIGNUP REQUEST RECEIVED ===")
    print(f"Name: {user.name}")
    print(f"Email: {user.email}")
    print(f"Role: {user.role}")
    print(f"Grade: {user.grade}")
    print(f"School: {getattr(user, 'school', 'NOT PROVIDED')}")
    print(f"ZipCode: {getattr(user, 'zipCode', 'NOT PROVIDED')}")
    print("================================")
    try:
        existing_user = users_collection.find_one({"email": user.email})
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        hashed_password = hash_password(user.password)
        
        # Create user document
        user_data = {
            "name": user.name,
            "email": user.email,
            "password": hashed_password,
            "grade": user.grade,
            "role": user.role,
            "school": user.school if hasattr(user, 'school') else '',
            "zipCode": user.zipCode if hasattr(user, 'zipCode') else '',
            "subjects": [],
            "created_at": datetime.utcnow()
        }
        
        result = users_collection.insert_one(user_data)
        token = create_access_token({"email": user.email, "user_id": str(result.inserted_id)})
        
        return {
            "status": "success",
            "message": "User created successfully",
            "token": token,
            "user": {
                "name": user.name,
                "email": user.email,
                "role": user.role,
                "grade": user.grade,
                "school": user.school if hasattr(user, 'school') else '',
                "zipCode": user.zipCode if hasattr(user, 'zipCode') else ''
            }
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
# LOGIN ROUTE
@app.post("/api/login")
def login(user: UserLogin):
    try:
        db_user = users_collection.find_one({"email": user.email})
        
        if not db_user:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        if not verify_password(user.password, db_user["password"]):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        token = create_access_token({"email": db_user["email"], "user_id": str(db_user["_id"])})
        
        return {
            "status": "success",
            "message": "Login successful",
            "token": token,
            "user": {
                "name": db_user["name"],
                "email": db_user["email"],
                "role": db_user["role"],
                "grade": db_user["grade"]
            }
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Get all mentors
@app.get("/api/mentors")
def get_mentors():
    try:
        mentors = users_collection.find(
            {"role": {"$in": ["mentor", "both"]}},
            {"password": 0}
        )
        
        mentor_list = []
        for mentor in mentors:
            mentor["_id"] = str(mentor["_id"])
            mentor_list.append(mentor)
        
        return {
            "status": "success",
            "mentors": mentor_list
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Get user profile
@app.get("/api/profile/{email}")
def get_profile(email: str):
    try:
        user = users_collection.find_one({"email": email}, {"password": 0})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user["_id"] = str(user["_id"])
        return {"status": "success", "user": user}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Update user subjects
@app.put("/api/subjects")
def update_subjects(data: dict):
    try:
        email = data.get("email")
        subjects = data.get("subjects", [])
        
        if not email:
            raise HTTPException(status_code=400, detail="Email is required")
        
        result = users_collection.update_one(
            {"email": email},
            {"$set": {"subjects": subjects}}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {"status": "success", "message": "Subjects updated successfully"}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Create session request
@app.post("/api/session-request")
def create_session_request(data: dict):
    try:
        mentee_email = data.get("mentee_email")
        mentor_email = data.get("mentor_email")
        subject = data.get("subject")
        message = data.get("message", "")
        
        if not mentee_email or not mentor_email or not subject:
            raise HTTPException(status_code=400, detail="Missing required fields")
        
        session_data = {
            "mentee_email": mentee_email,
            "mentor_email": mentor_email,
            "subject": subject,
            "message": message,
            "status": "pending",
            "created_at": datetime.utcnow()
        }
        
        result = sessions_collection.insert_one(session_data)
        
        # Create notification for mentor
        mentor = users_collection.find_one({"email": mentor_email})
        if mentor:
            create_notification(
                mentor_email,
                f"New session request for {subject} from {mentee_email}",
                "session_request"
            )
        
        return {
            "status": "success",
            "message": "Session request sent successfully!",
            "session_id": str(result.inserted_id)
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Get session requests for a user
@app.get("/api/sessions/{email}")
def get_sessions(email: str):
    try:
        sessions = sessions_collection.find({
            "$or": [
                {"mentee_email": email},
                {"mentor_email": email}
            ]
        })
        
        session_list = []
        for session in sessions:
            session["_id"] = str(session["_id"])
            session_list.append(session)
        
        return {
            "status": "success",
            "sessions": session_list
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Update session status
@app.put("/api/session-status")
def update_session_status(data: dict):
    try:
        from bson import ObjectId
        
        session_id = data.get("session_id")
        status = data.get("status")
        
        if not session_id or not status:
            raise HTTPException(status_code=400, detail="Missing required fields")
        
        if status not in ["accepted", "declined"]:
            raise HTTPException(status_code=400, detail="Invalid status")
        
        result = sessions_collection.update_one(
            {"_id": ObjectId(session_id)},
            {"$set": {"status": status}}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get session details to notify mentee
        session = sessions_collection.find_one({"_id": ObjectId(session_id)})
        if session:
            create_notification(
                session["mentee_email"],
                f"Your session request for {session['subject']} was {status}",
                f"session_{status}"
            )
        
        return {
            "status": "success",
            "message": f"Session {status} successfully"
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Update user profile
@app.put("/api/profile")
def update_profile(data: dict):
    try:
        email = data.get("email")
        updates = {}
        
        if not email:
            raise HTTPException(status_code=400, detail="Email is required")
        
        if data.get("name"):
            updates["name"] = data.get("name")
        if data.get("grade"):
            updates["grade"] = data.get("grade")
        if data.get("role"):
            if data.get("role") not in ["mentor", "mentee", "both"]:
                raise HTTPException(status_code=400, detail="Invalid role")
            updates["role"] = data.get("role")
        
        if data.get("new_password"):
            updates["password"] = hash_password(data.get("new_password"))
        
        if not updates:
            raise HTTPException(status_code=400, detail="No updates provided")
        
        result = users_collection.update_one(
            {"email": email},
            {"$set": updates}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="User not found")
        
        updated_user = users_collection.find_one({"email": email}, {"password": 0})
        updated_user["_id"] = str(updated_user["_id"])
        
        return {
            "status": "success",
            "message": "Profile updated successfully",
            "user": updated_user
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Upload profile picture
@app.post("/api/profile-picture")
async def upload_profile_picture(email: str = Form(...), file: UploadFile = File(...)):
    try:
        # Validate user
        user = users_collection.find_one({"email": email})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Validate content type
        if file.content_type not in ["image/jpeg", "image/png", "image/webp"]:
            raise HTTPException(status_code=400, detail="Unsupported file type")

        # Choose extension
        ext = ".jpg"
        if file.content_type == "image/png":
            ext = ".png"
        elif file.content_type == "image/webp":
            ext = ".webp"

        # Save file
        safe_email = email.replace("/", "_").replace("\\", "_")
        filename = f"{safe_email}{ext}"
        filepath = os.path.join(AVATARS_DIR, filename)

        contents = await file.read()
        with open(filepath, "wb") as f:
            f.write(contents)

        base_url = os.getenv("PUBLIC_BASE_URL", "http://localhost:8000")
        picture_url = f"{base_url}/uploads/avatars/{filename}"

        users_collection.update_one(
            {"email": email},
            {"$set": {"profile_picture_url": picture_url}}
        )

        updated_user = users_collection.find_one({"email": email}, {"password": 0})
        updated_user["_id"] = str(updated_user["_id"])

        return {
            "status": "success",
            "message": "Profile picture uploaded",
            "user": updated_user,
            "profile_picture_url": picture_url
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Get notifications for a user
@app.get("/api/notifications/{email}")
def get_notifications(email: str):
    try:
        notifications = notifications_collection.find(
            {"user_email": email}
        ).sort("created_at", -1)
        
        notification_list = []
        for notif in notifications:
            notif["_id"] = str(notif["_id"])
            notification_list.append(notif)
        
        unread_count = notifications_collection.count_documents({
            "user_email": email,
            "read": False
        })
        
        return {
            "status": "success",
            "notifications": notification_list,
            "unread_count": unread_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Mark notification as read
@app.put("/api/notifications/read/{notification_id}")
def mark_notification_read(notification_id: str):
    try:
        from bson import ObjectId
        
        result = notifications_collection.update_one(
            {"_id": ObjectId(notification_id)},
            {"$set": {"read": True}}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Notification not found")
        
        return {"status": "success", "message": "Notification marked as read"}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Mark all notifications as read
@app.put("/api/notifications/read-all/{email}")
def mark_all_notifications_read(email: str):
    try:
        notifications_collection.update_many(
            {"user_email": email, "read": False},
            {"$set": {"read": True}}
        )
        
        return {"status": "success", "message": "All notifications marked as read"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    # Set mentor availability
@app.post("/api/availability")
def set_availability(data: dict):
    try:
        email = data.get("email")
        time_slots = data.get("time_slots", [])
        
        if not email:
            raise HTTPException(status_code=400, detail="Email is required")
        
        # Delete existing availability
        availability_collection.delete_many({"mentor_email": email})
        
        # Insert new availability
        if time_slots:
            availability_data = {
                "mentor_email": email,
                "time_slots": time_slots,
                "updated_at": datetime.utcnow()
            }
            availability_collection.insert_one(availability_data)
        
        return {
            "status": "success",
            "message": "Availability updated successfully"
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Get mentor availability
@app.get("/api/availability/{email}")
def get_availability(email: str):
    try:
        availability = availability_collection.find_one({"mentor_email": email})
        
        if not availability:
            return {
                "status": "success",
                "time_slots": []
            }
        
        availability["_id"] = str(availability["_id"])
        
        return {
            "status": "success",
            "time_slots": availability.get("time_slots", [])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Update session request to include scheduled time
@app.post("/api/session-request-scheduled")
def create_scheduled_session_request(data: dict):
    try:
        mentee_email = data.get("mentee_email")
        mentor_email = data.get("mentor_email")
        subject = data.get("subject")
        message = data.get("message", "")
        scheduled_date = data.get("scheduled_date")  # ISO format date string
        scheduled_time = data.get("scheduled_time")  # e.g., "14:00-15:00"
        
        if not mentee_email or not mentor_email or not subject or not scheduled_date or not scheduled_time:
            raise HTTPException(status_code=400, detail="Missing required fields")
        
        session_data = {
            "mentee_email": mentee_email,
            "mentor_email": mentor_email,
            "subject": subject,
            "message": message,
            "scheduled_date": scheduled_date,
            "scheduled_time": scheduled_time,
            "status": "pending",
            "created_at": datetime.utcnow()
        }
        
        result = sessions_collection.insert_one(session_data)
        
        # Create notification for mentor
        mentor = users_collection.find_one({"email": mentor_email})
        if mentor:
            create_notification(
                mentor_email,
                f"New session request for {subject} on {scheduled_date} at {scheduled_time}",
                "session_request"
            )
        
        return {
            "status": "success",
            "message": "Session request sent successfully!",
            "session_id": str(result.inserted_id)
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Get upcoming sessions (accepted sessions only)
@app.get("/api/upcoming-sessions/{email}")
def get_upcoming_sessions(email: str):
    try:
        from datetime import datetime, date
        
        # Get today's date
        today = date.today().isoformat()
        
        # Find accepted sessions that are scheduled for today or later
        sessions = sessions_collection.find({
            "$or": [
                {"mentee_email": email},
                {"mentor_email": email}
            ],
            "status": "accepted",
            "scheduled_date": {"$gte": today}
        }).sort("scheduled_date", 1)
        
        session_list = []
        for session in sessions:
            session["_id"] = str(session["_id"])
            
            # Get other person's name
            if session["mentee_email"] == email:
                other_user = users_collection.find_one({"email": session["mentor_email"]})
                session["other_person"] = other_user["name"] if other_user else session["mentor_email"]
                session["role"] = "mentee"
            else:
                other_user = users_collection.find_one({"email": session["mentee_email"]})
                session["other_person"] = other_user["name"] if other_user else session["mentee_email"]
                session["role"] = "mentor"
            
            session_list.append(session)
        
        return {
            "status": "success",
            "sessions": session_list
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    # Get all mentees
@app.get("/api/mentees")
def get_mentees():
    try:
        # Find users who are mentees or both
        mentees = users_collection.find(
            {"role": {"$in": ["mentee", "both"]}},
            {"password": 0}  # Don't send passwords!
        )
        
        mentee_list = []
        for mentee in mentees:
            mentee["_id"] = str(mentee["_id"])
            mentee_list.append(mentee)
        
        return {
            "status": "success",
            "mentees": mentee_list
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
  