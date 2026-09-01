from enum import StrEnum
from datetime import datetime
from dataclasses import dataclass

class RegistrationMethod(StrEnum):
  geometric = "geometric"
  floorplan = "floorplan"
  fiducial = "fiducial"

@dataclass
class RegistrationResult:
  method: RegistrationMethod

  source_id: str
  target_id: str

  transform: list[float]

  error_m: float
  confidence: float
  inlier_ratio: float

  iterations: int
  
  created_at: datetime