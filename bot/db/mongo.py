import logging
from typing import Any
from urllib.parse import quote_plus

from pymongo import MongoClient
from pymongo.database import Database

from config import get_config

conf = get_config()

logger = logging.getLogger(__name__)

uri = "mongodb://%s:%s@%s" % (
    quote_plus(conf["MONGO_USER"]),
    quote_plus(conf["MONGO_PASS"]),
    conf["MONGO_HOST"],
)

__client: MongoClient[Any] = MongoClient(uri)


def get_db(db_name: str) -> Database[Any]:
    return __client.get_database(db_name)
