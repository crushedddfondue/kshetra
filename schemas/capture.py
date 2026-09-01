from enum import StrEnum
from dataclasses import dataclass
from datetime import datetime
from typing import Any

@dataclass
class CaptureSource(StrEnum):
  android_arcore: object
  ios_arkit: object
  dslr: object
  video: object

@dataclass
class ScaleMethod(StrEnum):
  vio: Any
  lidar: Any
  arcore_depth: Any  
  scale_reference: Any  
  floorplan: Any 

@dataclass
class Intrinsics:
  fx: float
  fy: float
  cx: float
  cy: float
  width: int
  height: int

@dataclass
class CameraPose:
  transform: list[float]
  convention: str

@dataclass
class Frame:
  index: int
  timestamp: float
  image_path: str
  intrinsics: Intrinsics
  pose: CameraPose

@dataclass
class ScaleInfo:
  method: ScaleMethod
  confidence: float

@dataclass
class CaptureBundle:
  bundle_id: str
  captured_at: datetime
  source: CaptureSource
  scale: ScaleInfo
  frames: list[Frame]
  point_cloud_path: str | None
  depth_dir: str | None
  notes: str | None