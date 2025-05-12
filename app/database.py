from pymongo import MongoClient

MONGO_URL = "mongodb://localhost:27017"
client = MongoClient(MONGO_URL)

db = client["order"]  # 데이터베이스 이름
order_collection = db["order"]  # 컬렉션 (테이블에 해당)



