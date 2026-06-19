"""APIRouter modules included by backend.main.

Each router reads ``backend.main`` back via module import (not ``from backend.main
import db``) so that request handlers always see the live ``db`` / ``db_client``
globals -- including the in-memory fakes tests swap in after import.
"""
