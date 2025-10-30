from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()

# Get MongoDB URL from environment variables
MONGODB_URL = os.getenv("MONGODB_URL")

# Connect to MongoDB
client = MongoClient(MONGODB_URL)

# Create/access database
db = client["studier_bridge_db"]

# Create/access collections (tables)
users_collection = db["users"]
sessions_collection = db["sessions"]
messages_collection = db["messages"]
notifications_collection = db["notifications"]
availability_collection = db["availability"]

print("✅ Connected to MongoDB successfully!")