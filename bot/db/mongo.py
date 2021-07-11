from pymongo import MongoClient
from pymongo.database import Database

from config import get_config

conf = get_config()

__client = MongoClient(
    f"mongodb://{conf['MONGO_USER']}:{conf['MONGO_PASS']}@{conf['MONGO_HOST']}:{conf['MONGO_PORT']}")


def get_db(db_name: str) -> Database:
    return __client.get_database(db_name)
