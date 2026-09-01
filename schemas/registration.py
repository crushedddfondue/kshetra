from enum import StrEnum
from datetime import datetime
from dataclasses import dataclass
from typing import Any

class RegistrationMethod(StrEnum):
  geometric: Any
  floorplan: Any
  fiducial: Any

@dataclass
class RegistrationResult:
  method: str
  source_id: int
  target_id: int
  transform: list[float]
  error_m: int
  confidence: float
  inliner_ratio: float
  iterations: int
  created_at: datetime