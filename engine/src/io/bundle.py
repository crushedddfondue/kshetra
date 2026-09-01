import json
from pathlib import Path
from datetime import datetime
from dataclasses import asdict

import numpy as np

from engine.src.io.ply import read_ply
from engine.src.schema.capture import (
  CaptureBundle, 
  Intrinsics,
  CameraPose,
  Frame,
  ScaleInfo, 
  ScaleMethod,
  CaptureSource, 
)


def write_bundle(dir: Path, bundle: CaptureBundle) -> None:
  dir = Path(dir)
  dir.mkdir(parents=True, exist_ok=True)

  data = asdict(bundle)
  data["source"] = bundle.source.value
  data["scale"]["method"] = bundle.scale.method.value
  data["captured_at"] = bundle.captured_at

  with (dir / "bundle.json").open("w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)


def read_bundle(dir: Path) -> CaptureBundle:
  dir = Path(dir)
  bundle_path = dir / "bundle.json"

  if not bundle_path.exists():
    raise FileNotFoundError(bundle_path)

  data = json.loads(bundle_path.read_text(encoding="utf-8"))

  try:
    frames = []

    for frame_data in data["frames"]:
      intrinsics_data = frame_data["intrinsics"]
      pose_data = frame_data["pose"]

      intrinsics = Intrinsics(
          fx=float(intrinsics_data["fx"]),
          fy=float(intrinsics_data["fy"]),
          cx=float(intrinsics_data["cx"]),
          cy=float(intrinsics_data["cy"]),
          width=int(intrinsics_data["width"]),
          height=int(intrinsics_data["height"]),
      )

      pose = CameraPose(
        transform=[float(v) for v in pose_data["transform"]],
        convention=pose_data["convention"]
      )

      frames.append(
        Frame(
          index=int(frame_data["index"]),
          timestamp=float(frame_data["timestamp_ms"]),
          image_path=frame_data["image_path"],
          intrinsics=intrinsics,
          pose=pose,
        )
      )


    scale = ScaleInfo(
      method=ScaleMethod(data["scale"]["method"]),
      confidence=float(data["scale"]["confidence"]),
    )

    return CaptureBundle(
      bundle_id=data["bundle_id"],
      captured_at=datetime.fromisoformat(data["captured_at"]),
      source=CaptureSource(data["source"]),
      scale=scale,
      frames=frames,
      point_cloud_path=data.get("point_cloud_path"),
      depth_dir=data.get("depth_dir"),
      notes=data.get("notes"),
    )
  except (KeyError, TypeError, ValueError) as exc:
    raise ValueError(f"Invalid CaptureBundle in {bundle_path}") from exc


def load_cloud(dir: Path, bundle: CaptureBundle) -> np.ndarray | None:
  if bundle.point_cloud_path is None:
    return None
  
  dir = Path(dir).resolve()
  cloud_path = (dir / bundle.point_cloud_path).resolve()

  if not cloud_path.is_relative_to(dir):
    raise ValueError(f"point_cloud_path escapes bundle dir: {bundle.point_cloud_path}")

  return read_ply(cloud_path)