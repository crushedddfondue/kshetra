from dataclasses import asdict
from datetime import datetime, timezone

from src.schema.capture import (
  CameraPose,
  CaptureBundle,
  CaptureSource,
  Frame,
  Intrinsics,
  ScaleInfo,
  ScaleMethod,
)

_IDENTITY_16 = [
  1.0, 0.0, 0.0, 0.0,
  0.0, 1.0, 0.0, 0.0,
  0.0, 0.0, 1.0, 0.0,
  0.0, 0.0, 0.0, 1.0,
]


def _frame(index: int) -> Frame:
  return Frame(
    index=index,
    timestamp=float(index),
    image_path=f"frames/{index:04d}.jpg",
    intrinsics=Intrinsics(fx=500.0, fy=500.0, cx=320.0, cy=240.0, width=640, height=480),
    pose=CameraPose(transform=list(_IDENTITY_16), convention="opengl"),
  )


def _bundle() -> CaptureBundle:
  return CaptureBundle(
    bundle_id="room-a-001",
    captured_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
    source=CaptureSource.android_arcore,
    scale=ScaleInfo(method=ScaleMethod.vio, confidence=0.9),
    frames=[_frame(0), _frame(1)],
    point_cloud_path="cloud.ply",
    depth_dir=None,
    notes=None,
  )


def test_bundle_construction():
  b = _bundle()
  assert b.bundle_id == "room-a-001"
  assert b.source is CaptureSource.android_arcore
  assert b.scale.method is ScaleMethod.vio
  assert len(b.frames) == 2
  assert b.frames[0].pose.transform == _IDENTITY_16
  assert b.frames[0].pose.convention == "opengl"


def test_enum_string_values():
  assert CaptureSource.android_arcore == "android_arcore"
  assert CaptureSource.ios_arkit == "ios_arkit"
  assert ScaleMethod.vio == "vio"
  assert ScaleMethod.floorplan == "floorplan"


def test_strenum_is_str():
  # bundle_io relies on StrEnum serialising as its string value in JSON.
  assert isinstance(CaptureSource.android_arcore, str)
  assert isinstance(ScaleMethod.vio, str)


def test_dataclass_equality():
  assert _bundle() == _bundle()
  other = _bundle()
  other.bundle_id = "different"
  assert _bundle() != other


def test_asdict_structure():
  data = asdict(_bundle())
  assert set(data) >= {
    "bundle_id", "captured_at", "source", "scale",
    "frames", "point_cloud_path", "depth_dir", "notes",
  }
  assert data["frames"][0]["intrinsics"]["width"] == 640
  assert data["frames"][0]["pose"]["convention"] == "opengl"