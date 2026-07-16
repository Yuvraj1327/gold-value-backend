"""Import every model here so `Base.metadata` is fully populated for Alembic
autogenerate (`env.py` imports `app.models` as a single entrypoint)."""
from app.models.calculation import Calculation
from app.models.gold_rate import GoldRate
from app.models.settings import UserSettings
from app.models.user import User

__all__ = ["User", "GoldRate", "Calculation", "UserSettings"]
