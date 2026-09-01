from dataclasses import dataclass
from datetime import datetime

from engine.src.schema.capture import ScaleMethod

@dataclass
class ScaleReport:
  method: ScaleMethod
  scale: float
  confidence: float
  notes: str | None

@dataclass
class Reconstruction:
  reconstruction_id: str
  bundle_id: str

  created_at: datetime
  point_cloud_path: str

  num_points: int
  
  scale: ScaleReport
  notes: str | None