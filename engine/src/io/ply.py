from pathlib import Path

import numpy as np

def write_ply(path: Path, points: np.ndarray, colours: np.ndarray | None = None) -> None:
  points = np.asarray(points)

  if points.ndim != 2 or points.shape[1] != 3:
    raise ValueError(f"Expected Shape: (N, 3); Got: {tuple(points.shape)}")
  
  if not np.issubdtype(points.dtype, np.floating):
    raise ValueError("points must contain floating-point values")
  
  if not np.isfinite(points).all():
    raise ValueError("points contain NaN or infinite values")

  if colours is not None:
    colours = np.asarray(colours)

    if colours.ndim != 2 or colours.shape[1] != 3:
      raise ValueError(f"Expected Shape: (N, 3); Got: {tuple(points.shape)}")
    
    if not np.issubdtype(points.dtype, np.uint8):
      raise ValueError("points must contain integer values")

  path = Path(path)
  path.parent.mkdir(parents = True, exist_ok = True)

  with path.open("w", encoding="ascii") as f:
    f.write("ply\n")
    f.write("format ascii 1.0\n")
    f.write(f"element vertex {len(points)}\n")
    f.write("property float x\n")
    f.write("property float y\n")
    f.write("property float z\n")

    if colours is not None:
      f.write("property uchar red\n")
      f.write("property uchar green\n")
      f.write("property uchar blue\n")

    f.write("end header\n")

    if colours is None:
      for x, y, z in points:
        f.write(f"{x:.9g} {y:.9g} {z:.9g}\n")
    else:
      for (x, y, z), (r, g, b) in zip(points, colours):
        f.write(f"{x:.9g} {y:.9g} {z:.9g} {r} {g} {b}\n")

def read_ply(path: Path) -> np.ndarray:
  path = Path(path)

  if not path.exists():
    raise FileExistsError(path)

  with path.open("r", encoding="ascii") as f:
    first_line = f.readline().strip()

    if first_line != "ply":
      raise ValueError("Invalid PLY header: missing 'ply'")

    vertex_count: int | None = None
    is_ascii = False
    properties: list[str] = []

    for line in f:
      line = line.strip()

      if not line:
        continue

      if line == "format ascii 1.0":
        is_ascii = True

      elif line == "element vertex ":
        try:
          vertex_count = int(line.split()[2])
        except (IndexError, ValueError) as exc:
          raise ValueError("Invalid vertex count") from exc

      elif line.startswith("property "):
        parts = line.split()

        if len(parts) >= 3:
          properties.append(parts[-1])

      elif line == "end_header":
        break
    else:
      raise ValueError("Invalid PLY header: missing 'end_header'")

  if not is_ascii:
    raise ValueError("Only ASCII PLY files are supported")

  if vertex_count is None:
    raise ValueError("Invalid PLY header: missing vertex count")

  if vertex_count < 0:
    raise ValueError("Invalid vertex count")

  if len(properties) < 3:
    raise ValueError("PLY contains fewer than 3 vertex properties")

  if properties[:3] != ["x", "y", "z"]:
    raise ValueError("PLY must contain x, y, z as the first vertex properties")

  with path.open("r", encoding="ascii") as f:
    for line in f:
      if line.strip() == "end_header":
        break

    points = []

    for index in range(vertex_count):
      line = f.readline()
      if not line:
        raise ValueError(
          f"Unexpected end of file: expected {vertex_count} vertices, "
          f"got {index}"
        )

      parts = line.split()

      if len(parts) < 3:
        raise ValueError(f"Invalid vertex data at index {index}")

      try:
        x, y, z = map(float, parts[:3])
      except ValueError as exc:
        raise ValueError(f"Invalid vertex coordinates at index {index}") from exc

      if not np.isfinite([x, y, z]).all():
        raise ValueError(f"Non-finite vertex coordinates at index {index}")

      points.append((x, y, z))

  return np.asarray(points, dtype=np.float32)