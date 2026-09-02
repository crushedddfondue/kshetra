from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from src.schema.registration import RegistrationResult


class ChangeKind(StrEnum):
  APPEARED = "appeared"
  DISAPPEARED = "disappeared"
  CHANGED = "changed"
  UNCHANGED = "unchanged"


@dataclass
class ChangeRegion:
  kind: ChangeKind

  centroid: list[float]
  bbox_min: list[float]
  bbox_max: list[float]

  area_m2: float
  volume_m3: float
  num_points: int

  confidence: float


@dataclass
class ChangeReport:
  report_id: str

  source_id: str
  against_id: str
  
  created_at: datetime
  distance_threshold_m: float
  registration: RegistrationResult
  regions: list[ChangeRegion] = field(default_factory=list)

  def counts(self) -> dict[ChangeKind, int]:
    counts = {kind: 0 for kind in ChangeKind}
    for region in self.regions:
      counts[region.kind] += 1
    return counts