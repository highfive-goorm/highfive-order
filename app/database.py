import os

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URI = f"mongodb://postgres:han00719@mongodb_order:27017/"
client = AsyncIOMotorClient(MONGO_URI)
db = client['order']

collection = db['order']
