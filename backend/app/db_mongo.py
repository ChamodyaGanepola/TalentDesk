from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()

MONGO_URL = os.getenv("MONGO_URL")
DB_NAME = os.getenv("DB_NAME")

if not MONGO_URL:
    raise ValueError("MONGO_URL is missing in .env file")

if not DB_NAME:
    raise ValueError("DB_NAME is missing in .env file")

client = MongoClient(MONGO_URL)
db = client[DB_NAME]

cv_collection = db["cvs"]