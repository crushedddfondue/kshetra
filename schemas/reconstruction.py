from dataclasses import dataclass
from datetime import datetime

from capture import ScaleMethod

@dataclass
class ScaleReport:
  method: ScaleMethod
  scale: int
  confidence: float
  notes: str | None

@dataclass
class Reconstruction:
  reconstruction_id: int
  bundle_id: int
  created_at: datetime
  point_cloud_path: str
  num_points: int
  scale: ScaleReport
  notes: str | None