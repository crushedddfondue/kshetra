from enum import StrEnum
from dataclasses import dataclass
from datetime import datetime

class CaptureSource(StrEnum):
  android_arcore = "android_arcore"
  ios_arkit = "ios_arkit"
  dslr = "dslr"
  video = "video"

class ScaleMethod(StrEnum):
  vio = "vio"
  lidar = "lidar"
  arcore_depth = "arcore_depth"  
  scale_reference = "scale_reference"  
  floorplan = "floorplan" 

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