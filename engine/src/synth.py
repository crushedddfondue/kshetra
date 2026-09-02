import numpy as np

CHANGE_BBOX_MIN = np.array([1.0, 1.0, 0.0], dtype=np.float64)
CHANGE_BBOX_MAX = np.array([2.0, 2.0, 1.0], dtype=np.float64)
CHANGE_N = 100


def make_room(rng, n_points: int = 20_000, dims: tuple[float, float, float] = (5., 4., 3.)) -> np.ndarray:
  """Sample points on the 5 interior faces of a room box.

  dims = [w, d, h]; the room spans [0, w] x [0, d] x [0, h].
  Face areas A = [w*d, d*h, d*h, w*h, w*h] (floor, x=0, x=w, y=0, y=d).
  Points are apportioned by area with the largest-remainder method, then
  sampled uniformly on each face with the passed-in Generator `rng`.
  """
  w, d, h = dims
  areas = np.asarray([w*d, d*h, d*h, w*h, w*h], dtype=np.float64)

  raw_counts = n_points * areas / areas.sum()
  counts = np.floor(raw_counts).astype(int)

  remainder = n_points - counts.sum()
  if remainder > 0:
    fractions = raw_counts - counts
    order = np.argsort(fractions)[::-1]
    counts[order[:remainder]] += 1

  points = []

  # Floor (z = 0)
  n = counts[0]
  if n > 0:
    x = rng.uniform(0, w, n)
    y = rng.uniform(0, d, n)
    z = np.zeros(n)
    points.append(np.column_stack((x, y, z)))

  # Wall (x = 0)
  n = counts[1]
  if n > 0:
    x = np.zeros(n)
    y = rng.uniform(0, d, n)
    z = rng.uniform(0, h, n)
    points.append(np.column_stack((x, y, z)))

  # Wall (x = w)
  n = counts[2]
  if n > 0:
    x = np.full(n, w)
    y = rng.uniform(0, d, n)
    z = rng.uniform(0, h, n)
    points.append(np.column_stack((x, y, z)))

  # Wall (y = 0)
  n = counts[3]
  if n > 0:
    x = rng.uniform(0, w, n)
    y = np.zeros(n)
    z = rng.uniform(0, h, n)
    points.append(np.column_stack((x, y, z)))

  # Wall (y = d)
  n = counts[4]
  if n > 0:
    x = rng.uniform(0, w, n)
    y = np.full(n, d)
    z = rng.uniform(0, h, n)
    points.append(np.column_stack((x, y, z)))

  if not points:
    return np.empty((0, 3), dtype=np.float64)

  return np.concatenate(points, axis=0).astype(np.float64)


def se3(rotation_deg: tuple[float, float, float], translation: tuple[float, float, float]) -> np.ndarray:
  """Build a 4x4 rigid transform from euler angles (degrees) + translation.

  R = Rz @ Ry @ Rx, with the standard right-handed axis rotations:
    Rx = [[1,0,0],[0, c_x,-s_x],[0, s_x, c_x]]
    Ry = [[ c_y,0, s_y],[0,1,0],[-s_y,0, c_y]]
    Rz = [[ c_z,-s_z,0],[ s_z, c_z,0],[0,0,1]]
  T = [[R, t], [0, 0, 0, 1]].
  """
  r_x, r_y, r_z = np.radians(np.array(rotation_deg, dtype=np.float64))

  Rx = np.array([
    [1.0, 0.0, 0.0],
    [0.0, np.cos(r_x), -np.sin(r_x)],
    [0.0, np.sin(r_x), np.cos(r_x)],
  ], dtype=np.float64)

  Ry = np.array([
    [np.cos(r_y), 0.0, np.sin(r_y)],
    [0.0, 1.0, 0.0],
    [-np.sin(r_y), 0.0, np.cos(r_y)],
  ], dtype=np.float64)

  Rz = np.array([
    [np.cos(r_z), -np.sin(r_z), 0.0],
    [np.sin(r_z), np.cos(r_z), 0.0],
    [0.0, 0.0, 1.0],
  ], dtype=np.float64)

  R = Rz @ Ry @ Rx

  T = np.eye(4, dtype=np.float64)
  T[:3, :3] = R
  T[:3, 3] = np.asarray(translation, dtype=np.float64)

  return T


def transform_points(points: np.ndarray, T: np.ndarray) -> np.ndarray:
  """Apply a 4x4 rigid transform to (N,3) points: p' = R p + t."""
  R = T[:3, :3]
  t = T[:3, 3]
  return (R @ points.T).T + t


def add_block(points: np.ndarray, bbox_min, bbox_max, n: int, rng) -> np.ndarray:
  """Concatenate n points sampled uniformly inside the AABB [bbox_min, bbox_max]."""
  bbox_min = np.asarray(bbox_min, dtype=np.float64)
  bbox_max = np.asarray(bbox_max, dtype=np.float64)

  new_points = rng.uniform(low=bbox_min, high=bbox_max, size=(n, 3))

  return np.concatenate([points, new_points], axis=0)


def make_pair(rng, *, transform: np.ndarray, noise_m: float = 0.005, add_change: bool = True) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
  """Return (t1, t2, ground_truth_T): t2 = transform of t1 [+ noise] [+ change block]."""
  t1 = make_room(rng)
  t2 = transform_points(t1, transform)

  if noise_m > 0:
    t2 = t2 + rng.normal(0.0, noise_m, size=t2.shape)

  if add_change:
    t2 = add_block(t2, CHANGE_BBOX_MIN, CHANGE_BBOX_MAX, n=CHANGE_N, rng=rng)

  return t1, t2, transform