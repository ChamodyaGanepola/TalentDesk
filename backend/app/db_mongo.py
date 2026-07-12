from pymongo import MongoClient
from pymongo.collection import Collection
from dotenv import load_dotenv
import os

load_dotenv()

MONGO_URL = os.getenv("MONGO_URL")
DB_NAME = os.getenv("DB_NAME")

if not MONGO_URL:
    raise ValueError("MONGO_URL is missing in .env file")

if not DB_NAME:
    raise ValueError("DB_NAME is missing in .env file")

_client = None
_db = None
_cv_collection = None
_mongo_error = None


def _connect():
    global _client, _db, _cv_collection, _mongo_error
    if _cv_collection is not None:
        return _cv_collection
    if _mongo_error is not None:
        raise ConnectionError(f"MongoDB unavailable: {_mongo_error}") from _mongo_error

    try:
        _client = MongoClient(
            MONGO_URL,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
        )
        # Force early failure with a clear message if DNS/cluster is down
        _client.admin.command("ping")
        _db = _client[DB_NAME]
        _cv_collection = _db["cvs"]
        return _cv_collection
    except Exception as e:
        _mongo_error = e
        _client = None
        _db = None
        _cv_collection = None
        raise ConnectionError(f"MongoDB unavailable: {e}") from e


class _LazyCVCollection:
    """Proxy so importing this module does not require live Mongo DNS."""

    def __getattr__(self, name):
        return getattr(_connect(), name)

    def __bool__(self):
        try:
            _connect()
            return True
        except Exception:
            return False


cv_collection: Collection | _LazyCVCollection = _LazyCVCollection()
