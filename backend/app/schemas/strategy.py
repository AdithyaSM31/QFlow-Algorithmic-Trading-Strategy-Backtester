"""Strategy schemas."""

from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class StrategyType(str, Enum):
    MA_CROSSOVER = "MA_CROSSOVER"
    RSI = "RSI"
    BOLLINGER = "BOLLINGER"
    ML_SIGNAL = "ML_SIGNAL"


class StrategyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    type: StrategyType
    parameters: dict = Field(default_factory=dict)
    description: str | None = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "Golden Cross AAPL",
                    "type": "MA_CROSSOVER",
                    "parameters": {"fast_window": 50, "slow_window": 200},
                    "description": "Classic golden cross strategy on Apple stock",
                }
            ]
        }
    }


class StrategyUpdate(BaseModel):
    name: str | None = None
    parameters: dict | None = None
    description: str | None = None


from uuid import UUID

class StrategyResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    type: str
    parameters: dict
    description: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
