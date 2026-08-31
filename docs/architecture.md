# Kshetra — Architecture (Initial)

*Status: draft v0.1 · Owner: Aattreya · Companion to `docs/build-plan.md`, `docs/roadmap.md`, and the tech-stack comparison.*

This is the initial architecture of record. It consolidates the decisions made so far into one reference: what Kshetra is, how it's structured, the contracts between its parts, and what we will deliberately revisit as it scales. It is intentionally MVP-honest — the MVP shape is real, the scale shape is sketched, and every seam that lets one become the other is called out.

---

## 1. Requirements

### 1.1 Functional

Kshetra answers one job, first: **"tell me what changed since the last site visit."**

- Ingest a capture of a room/site from a phone (MVP: iPhone/iPad Pro with LiDAR).
- Produce a metric-scaled reconstruction (point cloud + camera poses).
- Register a new capture against a previous one of the same space.
- Detect geometric change between the two, with confidence, localised to regions.
- Emit a ranked, human-readable, photo-backed change report.

Deferred by design (later phases, gated): semantic labels (wall/door/beam), progress states, plan-vs-reality deviation, natural-language reasoning, multi-project SaaS, Android/DSLR capture, the interiors branch.

### 1.2 Non-functional

| Property | MVP target | Notes |
| --- | --- | --- |
| **Accuracy** | 5–10 cm (progress tracking) | Architected to tighten to 0.5–2 cm later without a rewrite. |
| **Metric scale** | Solved by hardware (ARKit + LiDAR) | Removes monocular scale ambiguity for the MVP. |
| **Latency** | Batch, minutes per capture | Not interactive; reconstruction/registration are async jobs. |
| **Throughput** | 1 project, a handful of captures/week | Deliberately tiny. No high-QPS requirement exists yet. |
| **Availability** | Best-effort (local CLI) | No uptime SLA until there's a paying pilot. |
| **Cost** | Near-zero fixed cost | No always-on GPU; on-device reconstruction; local storage. |
| **Auditability** | Append-only from day one | "What did this room look like on 12 March?" must stay answerable. |

### 1.3 Constraints

Solo, bootstrapped founder. Optimise for **fewest moving parts, one primary language, fastest path to willingness-to-pay**, while keeping clean seams so scaling is additive rather than a rewrite. Professional quality (typed, tested, linted) from the first commit.

---

## 2. High-level design

### 2.1 The pipeline (the whole product, one line)

```text
Capture  →  Reconstruct  →  Register  →  Detect change  →  Report
(iOS/LiDAR)  (metric geom)  (align to    (geometric Δ +    (ranked, with
                            prior visit)  confidence)       photos)
```

Everything downstream of a paying pilot — semantics, reasoning, dashboard — hangs off the same spine and is added phase by phase.

### 2.2 Component diagram (MVP)

```text
┌──────────────────────────────────────────────────────────────────┐
│                         iOS Capture App (Swift/ARKit)              │
│   ARSession · LiDAR sceneDepth · pose recording · coverage guide  │
│                              │                                     │
│                              ▼  writes                             │
│                   ┌────────────────────┐                          │
│                   │   CaptureBundle     │  ◄── Seam 1 (contract)   │
│                   │  frames+poses+depth │                          │
│                   │  +cloud +scale meta │                          │
│                   └─────────┬──────────┘                          │
└─────────────────────────────┼─────────────────────────────────────┘
                              │  (file transfer: AirDrop / upload)
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                 kshetra CLI  (Python · Typer)                      │
│                                                                    │
│   capture/ ─ validate ──►  reconstruct/ ──►  register/ ──►  change/│
│   ingest & QC            (Seam 2)          (Seam 3)        geom Δ  │
│                          arkit | sfm       geometric |            │
│                                            floorplan |            │
│                                            fiducial              │
│                              │                 │            │      │
│                              ▼                 ▼            ▼      │
│                        Reconstruction   RegistrationResult  Report │
└──────────────────────────────┬─────────────────────────────────────┘
                              │  reads/writes
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│           State (MVP: SQLite + local files, behind Store iface)    │
│           append-only capture log  +  derived state @ t            │
└──────────────────────────────────────────────────────────────────┘
```

### 2.3 The three seams (why change stays cheap)

The architecture is organised around three interfaces. Each has a trivial MVP implementation and a clear upgrade path; the rest of the system depends only on the interface.

| Seam | Interface | MVP impl | Upgrade path (unlocks) |
| --- | --- | --- | --- |
| **1. Capture** | `CaptureBundle` (data contract) | iOS/LiDAR producer | Android (ARCore), DSLR/video producers — *new platforms* |
| **2. Reconstruct** | `Reconstructor: bundle → Reconstruction` | `arkit` pass-through | `colmap` / `vggt` backends + metric anchoring — *tighter accuracy, non-LiDAR input* |
| **3. Register** | `Registrar: (recon_t2, recon_t1) → RegistrationResult` | `geometric` (FPFH→ICP) | `floorplan`, `fiducial`, learned methods — *robustness, the core IP* |

Adding a platform, an accuracy tier, or a registration method is implementing an interface — never touching the code on the other side of it.

### 2.4 Contracts

`schemas/` is the single source of truth (JSON Schema), from which typed models are kept in sync in each language (Pydantic in Python, Codable in Swift).

**CaptureBundle** — one capture, platform-agnostic:

```jsonc
{
  "bundle_id": "uuid",
  "captured_at": "ISO-8601",
  "source": "ios_arkit | android_arcore | dslr | video",
  "frames": [ /* image refs + intrinsics + timestamp */ ],
  "poses":  [ /* 4x4 camera-to-world, VIO */ ],
  "depth":  [ /* per-frame depth refs, optional */ ],
  "point_cloud_path": "cloud.ply",           // optional (LiDAR fused)
  "scale": { "method": "lidar|scale_reference|floorplan|none",
             "confidence": 0.0-1.0 }         // Seam-2 metric anchor
}
```

**RegistrationResult** — never a boolean:

```jsonc
{
  "method": "geometric|floorplan|fiducial",
  "transform": [ /* row-major 4x4 */ ],
  "error_m": 0.0,          // alignment error in metres
  "confidence": 0.0-1.0
}
```

**ChangeReport** — the artifact a PM reads: ranked regions (`appeared|disappeared|volume_delta|changed|unchanged`), each with area/volume, confidence, and source photo refs.

### 2.5 Interface surface (CLI first, HTTP later)

The MVP product surface is the CLI; the same operations become HTTP endpoints in Phase 7 with **no change to the core**, because the CLI commands are thin wrappers over library functions.

```text
kshetra reconstruct ./capture_002/          → reconstruction/
kshetra register    ./capture_002 --against ./capture_001   → registration_result.json
kshetra diff        ./capture_002 --against ./capture_001   → change_report.json
kshetra report      ./change_report.json    → report.html / .pdf
```

Phase 7 mapping (illustrative): `POST /captures`, `POST /captures/{id}/reconstruct`, `POST /register`, `GET /projects/{id}/changes` — each enqueues a job and returns a handle; the worker runs the same `kshetra.*` functions.

---

## 3. Deep dive

### 3.1 Data model — append-only / event-sourced

Construction generates disputes, so history has direct commercial (sometimes contractual) value. State is modelled as an **immutable log of captures** with **derived** state, not a mutable object updated in place.

```text
Project
  ├─ floorplan / drawings            (first-class input)
  ├─ Site → Room A / Room B / …
  ├─ Capture 001   (immutable, timestamped)   ┐
  ├─ Capture 002   (immutable, timestamped)   │ the log (source of truth)
  ├─ Capture 003   (immutable, timestamped)   ┘
  └─ Derived state @ t   (a fold over the log; rebuildable, disposable)
```

Rules: captures and their reconstructions are never mutated or deleted; derived state (current geometry, latest change set) is a pure function of the log and can be recomputed. This makes *"what did Room A look like on 12 March?"* a query, not an archaeology project. Cheap now, expensive to retrofit — hence adopted at v0.

**MVP persistence:** SQLite for the log/metadata + local filesystem for blobs (`.ply`, images), both behind a `Store` interface.
**Scale persistence:** PostgreSQL for the log + Cloudflare R2 (S3-compatible, no egress fees) for blobs. Same interface; a config change, not a rewrite.

### 3.2 Reconstruction (Seam 2)

- **MVP (`arkit`):** ARKit already produces metric poses, depth, and a fused cloud on-device. The backend normalises the bundle into the internal `Reconstruction` (`point_cloud.ply`, `cameras.json`, `scale_report.json`). Cheap — the phone did the geometry.
- **Upgrade (`sfm`):** for DSLR/plain video, run COLMAP (precise, slower) or a feed-forward model (VGGT/MASt3R — fast, but *up-to-scale*) followed by an explicit metric-anchoring step (scale reference, floorplan constraint, or fiducials). This is how non-LiDAR input and the tighter 0.5–2 cm accuracy tier arrive, entirely behind the interface.

### 3.3 Registration (Seam 3) — the crux

The hard, circular problem: aligning two captures needs the unchanged geometry, but *knowing* what's unchanged is registration's output — and on a live site a large fraction of the scene changes between visits.

- **`geometric`:** downsample → FPFH features → RANSAC global alignment → ICP refinement (Open3D). Output: transform + `error_m` + `confidence`.
- **`floorplan` (fallback, cheap):** a 2D plan gives a global coordinate frame almost for free, solving much of registration with no learning.
- **`fiducial` (fallback, robust):** physical markers on structural elements (columns, door frames) as persistent anchors across visits.

**Design mandate:** run the two fallbacks *in parallel from the start*, before investing months in a clever learned solution. The result is always an error + confidence, never a yes/no.

### 3.4 Change detection (Phase 3, MVP-lite here)

Geometric only at first: `ΔS = S(t₂) ⊖ S(t₁)` producing region-level events (appeared / disappeared / volume added-removed / changed-beyond-threshold / **explicitly unchanged with confidence**). *"This 2.1 m² region of the north wall changed"* — never *"images differ by 14.2%."* A labelled benchmark (10–20 annotated pairs, with hard negatives: lighting, camera-only motion, moved clutter, people) is built alongside captures so precision is measurable at the pilot.

### 3.5 Jobs, errors, retries

- **MVP:** the CLI runs synchronously; each stage writes its output artifact, so a failed stage is re-runnable from the last good artifact (the pipeline is a series of pure-ish file→file transforms). Validation happens at ingest (`capture/`) — coverage, scale sanity — to fail fast before expensive stages.
- **Scale:** stages become idempotent queued jobs (Dramatiq/Celery) keyed by content hash, so retries are safe and results are cacheable. GPU stages run on on-demand workers.

---

## 4. Scale & reliability

Deliberately deferred, but the shape is fixed so nothing here is a surprise later.

| Concern | MVP | Scale (Phase 7) |
| --- | --- | --- |
| Compute | Laptop / phone | On-demand GPU workers (Runpod/Lambda), autoscaled per queue depth |
| API | none (CLI) | FastAPI, horizontally scalable (stateless), behind a load balancer |
| State | SQLite + local FS | PostgreSQL (primary + read replica) |
| Blobs | Local FS | Cloudflare R2 |
| Queue | none | Redis + Dramatiq |
| Failover | re-run CLI | Idempotent jobs, retries with backoff, dead-letter queue |
| Observability | logs | Structured logs + Sentry + per-stage metrics (success rate, error_m distribution) |
| Multi-tenant | single project | Project-scoped rows + object prefixes; auth via managed provider (Clerk/Auth0/Supabase) |

Scaling levers, in order of what breaks first: reconstruction/registration compute (GPU workers) → blob storage (R2) → API tier (stateless replicas) → database (replicas, then partition by project). The API is intentionally the *last* thing that needs to scale, because the workload is heavy-async-job, not high-QPS — which is exactly why Python/FastAPI is the right backbone (see the stack comparison).

---

## 5. Trade-offs made explicit

| Decision | Chosen | Gave up | Why it's right for now |
| --- | --- | --- | --- |
| Platform | iOS-first (LiDAR) | Android/DSLR reach | LiDAR solves metric scale for free; collapses Phase 1 so effort goes to registration. CaptureBundle keeps the door open. |
| Accuracy | 5–10 cm MVP | Immediate QA/QC precision | Matches the "what changed" job and the fastest pilot; seams allow tightening later. |
| Language | Python-on-C++ | JVM/Go raw throughput | Compute core has one mature ecosystem; one backend language beats a two-backend polyglot for a solo founder. |
| Architecture | Modular monolith + CLI | Microservices | Simplicity now; seams let services split out at Phase 7 without redesign. |
| State | Append-only/event-sourced | Simpler CRUD | Disputes make history commercially valuable; cheap now, expensive later. |
| Compute | On-device + on-demand GPU | Always-on GPU convenience | Near-zero fixed cost for a bootstrapped founder. |
| Persistence | SQLite + local FS | Cloud DB/storage from day one | No infra to run pre-pilot; `Store` interface makes the swap a config change. |

---

## 6. What we'll revisit as it grows

- **Registration method** — geometric alignment is expected to strain as scene-change fraction rises; the floorplan/fiducial fallbacks and, later, learned registration are where the real IP will concentrate. This is the first thing to harden after the pilot.
- **Metric-scale strategy** — moving from LiDAR-only toward the 0.5–2 cm tier means adding fiducial/total-station ground truth and swapping/ensembling reconstruction backends.
- **Monolith → services** — split `reconstruct` and `register` into their own GPU-worker services once a single process/queue is the bottleneck. The seams pre-draw the split lines.
- **SQLite → Postgres + R2** — at the second user / first shared project.
- **CLI → API + web** — when the pilot needs a UI; the CLI commands become endpoint handlers over the same library.
- **A throughput edge service (Go/Rust)** — only if capture-upload ingestion or streaming becomes a measured hot path. Profile first (roadmap's "optimise last").

---

## 7. Assumptions

- The first pilot user has iPhone/iPad Pro (LiDAR) access on site. *(Load-bearing — validate before committing further to iOS-first.)*
- A 2D floorplan is available for most projects (enables the cheap registration fallback).
- Captures are taken with reasonable coverage of the same space across visits (the guided-capture app enforces this).
- Batch (non-real-time) processing is acceptable to the user for the MVP.

---

*Revision history:* v0.1 — initial architecture of record, consolidating the build plan, stack comparison, and roadmap v2. Python 3.12 backbone; ARKit/LiDAR capture; append-only state; three-seam modular monolith.