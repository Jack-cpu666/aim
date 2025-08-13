import os, io, uuid, time, math, shutil, pathlib, urllib.request
from typing import List, Tuple, Dict
from dataclasses import dataclass

from flask import Flask, Response, request, redirect, url_for, send_from_directory, render_template_string, abort

# ---- Server config ----
APP_DIR = pathlib.Path(__file__).parent.resolve()
DATA_DIR = APP_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
RESULTS_DIR = DATA_DIR / "results"
MODEL_DIR = DATA_DIR / "models"
for p in (UPLOAD_DIR, RESULTS_DIR, MODEL_DIR):
    p.mkdir(parents=True, exist_ok=True)

# Flask setup
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024  # 200 MB uploads

# ---- HTML (upload form + simple status) ----
INDEX_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Stickman Pose — Video Labeler</title>
<style>
  :root{--bg:#0b0b0b;--fg:#f4f4f5;--muted:#a1a1aa;--accent:#60a5fa}
  *{box-sizing:border-box} html,body{height:100%}
  body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.45 system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,"Helvetica Neue",Arial,"Noto Sans",sans-serif}
  .wrap{max-width:960px;margin:0 auto;padding:24px}
  h1{font-size:20px;margin:8px 0 16px;font-weight:700}
  p{color:var(--muted)}
  .card{background:#111827;border:1px solid #1f2937;border-radius:12px;padding:16px}
  .row{display:flex;gap:12px;align-items:center;flex-wrap:wrap}
  .btn{appearance:none;border:0;border-radius:10px;background:#1f2937;color:var(--fg);padding:.7rem 1rem;font-weight:600;cursor:pointer}
  .btn:hover{background:#0f172a}
  input[type=file]{border:1px dashed #334155;border-radius:10px;padding:16px;width:100%;background:#0b1220;color:#cbd5e1}
  .hint{color:#94a3b8;font-size:.95rem}
  .link{color:var(--accent);text-decoration:none}
  .mono{font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,"Liberation Mono","Courier New",monospace}
  .grid{display:grid;grid-template-columns:1fr;gap:12px}
  .tag{display:inline-block;background:#0b1220;border:1px solid #1e293b;border-radius:999px;padding:.2rem .6rem;color:#cbd5e1;font-size:.85rem}
</style>
</head>
<body>
  <div class="wrap">
    <h1>Stickman Pose — Video Labeler</h1>
    <div class="card grid">
      <form method="POST" action="/upload" enctype="multipart/form-data">
        <label class="hint">Upload a short video (recommended ≤ ~30–60 seconds)</label>
        <input type="file" name="video" accept="video/*" required>
        <div class="row">
          <label><input type="checkbox" name="show_video" checked> Draw over original frames (uncheck for black background)</label>
        </div>
        <div class="row">
          <span class="tag">High confidence</span>
          <span class="hint">We use strict thresholds so we don’t draw stickmen on non-people.</span>
        </div>
        <div class="row">
          <button class="btn" type="submit">Upload & Process</button>
        </div>
      </form>
      <p class="hint">When done, you’ll get a download link to the labeled video. People are tracked and labeled <span class="mono">Person 1</span>, <span class="mono">Person 2</span>, etc.</p>
      <p class="hint">Tip: Good lighting and the whole body in frame improves accuracy.</p>
    </div>
  </div>
</body>
</html>
"""

DONE_HTML = r"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Done — Stickman Pose</title>
<style>
  :root{--bg:#0b0b0b;--fg:#f4f4f5;--muted:#a1a1aa;--accent:#60a5fa}
  body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.45 system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,"Helvetica Neue",Arial,"Noto Sans",sans-serif}
  .wrap{max-width:860px;margin:0 auto;padding:28px}
  .card{background:#111827;border:1px solid #1f2937;border-radius:12px;padding:16px}
  .link{color:var(--accent);text-decoration:none;font-weight:700}
  .hint{color:#94a3b8}
  .row{display:flex;gap:12px;align-items:center;flex-wrap:wrap}
  code{background:#0b1220;border:1px solid #1e293b;border-radius:8px;padding:.1rem .4rem}
</style></head>
<body>
  <div class="wrap">
    <div class="card">
      <h2>✅ Processing complete</h2>
      <p class="row">Download your labeled video: <a class="link" href="{{ url }}" download>{{ name }}</a></p>
      <p class="hint">File will be kept temporarily on the server.</p>
      <p><a class="link" href="/">Process another video</a></p>
    </div>
  </div>
</body></html>
"""

ERROR_HTML = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Error</title>
<style>body{background:#0b0b0b;color:#f4f4f5;font:16px/1.45 system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,"Helvetica Neue",Arial,"Noto Sans",sans-serif;margin:0}
.wrap{max-width:860px;margin:0 auto;padding:28px}.card{background:#111827;border:1px solid #1f2937;border-radius:12px;padding:16px}
a{color:#60a5fa;text-decoration:none}</style></head>
<body><div class="wrap"><div class="card"><h2>⚠️ Error</h2><pre>{{msg}}</pre><p><a href="/">Back</a></p></div></div></body></html>
"""

# ---- Model (download once) ----
POSE_TASK_URL = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task"
MODEL_PATH = MODEL_DIR / "pose_landmarker_lite.task"

def ensure_model() -> str:
    if not MODEL_PATH.exists():
        try:
            print(f"Downloading model to {MODEL_PATH} ...", flush=True)
            urllib.request.urlretrieve(POSE_TASK_URL, MODEL_PATH)
        except Exception as e:
            raise RuntimeError(f"Failed to download pose model: {e}")
    return str(MODEL_PATH)

# ---- Pose + drawing ----
import cv2
import numpy as np
import mediapipe as mp

BaseOptions = mp.tasks.BaseOptions
VisionRunningMode = mp.tasks.vision.RunningMode
PoseLandmarker = mp.tasks.vision.PoseLandmarker
PoseLandmarkerOptions = mp.tasks.vision.PoseLandmarkerOptions
ImageFormat = mp.ImageFormat

# skeleton indices (BlazePose)
LS, RS, LE, RE, LW, RW = 11, 12, 13, 14, 15, 16
LH, RH, LK, RK, LA, RA = 23, 24, 25, 26, 27, 28
LHE, RHE, LFI, RFI = 29, 30, 31, 32
NOSE, LEYE, REYE, LEAR, REAR = 0, 2, 5, 7, 8

SEGMENTS = [
    (LS, RS), (LH, RH), (LS, LH), (RS, RH),                # torso
    (LS, LE), (LE, LW), (RS, RE), (RE, RW),               # arms
    (LH, LK), (LK, LA), (RH, RK), (RK, RA),               # legs
    (LA, LHE), (LHE, LFI), (RA, RHE), (RHE, RFI),         # feet hints
]

def draw_stickman(img, lms, label_text: str = None, show_video_bg=True, color=(255,255,255), thick=3):
    """lms: list[NormalizedLandmark] length 33"""
    h, w = img.shape[:2]

    def pt(i):
        lm = lms[i]
        return int(lm.x * w), int(lm.y * h)

    # lines
    for a, b in SEGMENTS:
        x1, y1 = pt(a); x2, y2 = pt(b)
        cv2.line(img, (x1, y1), (x2, y2), color, thick, cv2.LINE_AA)

    # head circle using ears/eyes/nose + shoulder span
    def dist(a, b):
        x1, y1 = pt(a); x2, y2 = pt(b)
        return math.hypot(x1-x2, y1-y2)
    def mid(a, b):
        x1, y1 = pt(a); x2, y2 = pt(b)
        return int((x1+x2)/2), int((y1+y2)/2)

    center = None; radius = None
    if lms[LEAR].visibility > 0 and lms[REAR].visibility > 0:
        center = mid(LEAR, REAR); radius = max(8, int(0.7 * dist(LEAR, REAR)))
    elif lms[LEYE].visibility > 0 and lms[REYE].visibility > 0:
        center = mid(LEYE, REYE); radius = max(8, int(1.2 * dist(LEYE, REYE)))
    else:
        shoulder_span = dist(LS, RS)
        nx, ny = pt(NOSE)
        center = (nx, int(ny - 0.4 * shoulder_span))
        radius = max(8, int(0.35 * shoulder_span))

    if center and radius:
        cv2.circle(img, center, radius, color, thick, cv2.LINE_AA)
        sx, sy = mid(LS, RS)
        cv2.line(img, (sx, sy), center, color, thick, cv2.LINE_AA)

    # label near head
    if label_text:
        tx, ty = center if center else pt(NOSE)
        y = max(20, ty - (radius + 10))
        cv2.putText(img, label_text, (max(5, tx - 30), y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (50,205,50), 2, cv2.LINE_AA)

def pose_confidence(lms) -> float:
    """Conservative confidence using key landmarks' presence/visibility."""
    key_idx = [NOSE, LS, RS, LH, RH, LE, RE, LW, RW]
    pres = []
    vis = []
    for i in key_idx:
        lm = lms[i]
        # presence may not always be populated; guard with getattr
        pres.append(getattr(lm, "presence", 1.0))
        vis.append(getattr(lm, "visibility", 1.0))
    return min(float(np.mean(pres)), float(np.mean(vis)))

# Simple centroid-based tracker to give stable person IDs across frames
@dataclass
class Track:
    id: int
    cx: float
    cy: float
    last_frame: int

class Tracker:
    def __init__(self, max_age=30, dist_thresh=80.0):
        self.max_age = max_age
        self.dist_thresh = dist_thresh
        self.tracks: Dict[int, Track] = {}
        self.next_id = 1

    def _distance(self, a: Tuple[float,float], b: Tuple[float,float]) -> float:
        return math.hypot(a[0]-b[0], a[1]-b[1])

    def update(self, detections: List[Tuple[float,float]], frame_idx: int) -> List[Tuple[int, Tuple[float,float]]]:
        # Greedy nearest-neighbor assignment
        assigned = []
        det_used = [False]*len(detections)

        # try to match existing tracks
        for tid, tr in list(self.tracks.items()):
            # find nearest unmatched detection
            best_j = -1; best_d = 1e9
            for j, (cx, cy) in enumerate(detections):
                if det_used[j]: continue
                d = self._distance((tr.cx, tr.cy), (cx, cy))
                if d < best_d:
                    best_d, best_j = d, j
            if best_j != -1 and best_d <= self.dist_thresh:
                cx, cy = detections[best_j]
                det_used[best_j] = True
                tr.cx, tr.cy, tr.last_frame = cx, cy, frame_idx
                assigned.append((tid, (cx, cy)))
            else:
                # age out later
                pass

        # create new tracks for unmatched detections
        for j, (cx, cy) in enumerate(detections):
            if not det_used[j]:
                tid = self.next_id; self.next_id += 1
                self.tracks[tid] = Track(tid, cx, cy, frame_idx)
                assigned.append((tid, (cx, cy)))

        # remove stale tracks
        for tid in list(self.tracks.keys()):
            if frame_idx - self.tracks[tid].last_frame > self.max_age:
                del self.tracks[tid]

        return assigned

def ensure_landmarker():
    ensure_model()
    options = PoseLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(MODEL_PATH)),
        running_mode=VisionRunningMode.VIDEO,
        # High-confidence to avoid non-people false positives:
        num_poses=4,
        min_pose_detection_confidence=0.8,
        min_pose_presence_confidence=0.8,
        min_tracking_confidence=0.8,
        output_segmentation_masks=False,
    )
    return PoseLandmarker.create_from_options(options)

def process_video(in_path: str, out_path: str, draw_over_video: bool = True) -> None:
    landmarker = ensure_landmarker()
    cap = cv2.VideoCapture(in_path)
    if not cap.isOpened():
        raise RuntimeError("Could not open input video.")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")  # save .mp4
    writer = cv2.VideoWriter(out_path, fourcc, fps, (width, height))
    if not writer.isOpened():
        raise RuntimeError("Could not open VideoWriter. Try different codec or extension.")

    tracker = Tracker(max_age=20, dist_thresh=max(40.0, 0.05*max(width,height)))

    frame_idx = 0
    t0 = time.time()

    try:
        while True:
            ok, frame_bgr = cap.read()
            if not ok:
                break

            frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=ImageFormat.SRGB, data=frame_rgb)
            ts_ms = int((frame_idx / fps) * 1000.0)

            result = landmarker.detect_for_video(mp_image, ts_ms)

            # choose background
            if draw_over_video:
                out = frame_bgr.copy()
            else:
                out = np.zeros_like(frame_bgr)
                out[:] = (0,0,0)  # black background

            detections_centers = []
            valid_poses = []

            if result and getattr(result, "pose_landmarks", None):
                # result.pose_landmarks is List[List[NormalizedLandmark]]
                for pose_lms in result.pose_landmarks:
                    conf = pose_confidence(pose_lms)
                    if conf < 0.8:
                        continue  # keep it strict
                    # centroid by hips/shoulders midpoints
                    sx = (pose_lms[LS].x + pose_lms[RS].x) * 0.5 * width
                    sy = (pose_lms[LS].y + pose_lms[RS].y) * 0.5 * height
                    hx = (pose_lms[LH].x + pose_lms[RH].x) * 0.5 * width
                    hy = (pose_lms[LH].y + pose_lms[RH].y) * 0.5 * height
                    cx, cy = (sx+hx)/2.0, (sy+hy)/2.0
                    detections_centers.append((cx, cy))
                    valid_poses.append(pose_lms)

            # assign IDs
            assignments = tracker.update(detections_centers, frame_idx)
            # map back: detections_centers index -> id
            id_by_index = {}
            for tid, (cx, cy) in assignments:
                # match by nearest within same frame to keep order
                # (detections_centers and valid_poses are aligned)
                nearest_idx = -1; best = 1e9
                for idx, (dx, dy) in enumerate(detections_centers):
                    d = math.hypot(dx - cx, dy - cy)
                    if d < best:
                        best, nearest_idx = d, idx
                if nearest_idx != -1 and nearest_idx not in id_by_index:
                    id_by_index[nearest_idx] = tid

            # draw
            for i, pose_lms in enumerate(valid_poses):
                tid = id_by_index.get(i)
                label = f"Person {tid}" if tid is not None else None
                draw_stickman(out, pose_lms, label_text=label, thick=max(2, int(0.004*max(width,height))))

            writer.write(out)
            frame_idx += 1

    finally:
        cap.release()
        writer.release()
        landmarker.close()
        print(f"Processed {frame_idx} frames in {time.time()-t0:.1f}s", flush=True)

# ---- Routes ----
@app.get("/")
def index():
    return Response(INDEX_HTML, mimetype="text/html")

@app.post("/upload")
def upload():
    f = request.files.get("video")
    if not f or f.filename == "":
        return render_template_string(ERROR_HTML, msg="No video provided"), 400

    ext = (pathlib.Path(f.filename).suffix or ".mp4").lower()
    if ext not in {".mp4", ".mov", ".m4v", ".avi", ".webm", ".mkv"}:
        return render_template_string(ERROR_HTML, msg="Unsupported file type"), 400

    file_id = uuid.uuid4().hex
    in_path  = UPLOAD_DIR / f"{file_id}{ext}"
    out_path = RESULTS_DIR / f"{file_id}.mp4"

    try:
        f.save(in_path)
        draw_over = ("show_video" in request.form)
        process_video(str(in_path), str(out_path), draw_over_video=draw_over)
    except Exception as e:
        return render_template_string(ERROR_HTML, msg=str(e)), 500
    finally:
        # keep uploads small; optionally delete input to save space
        try:
            if in_path.exists() and in_path.stat().st_size > 0:
                pass
        except Exception:
            pass

    dl_url = url_for("download_file", filename=out_path.name, _external=False)
    return render_template_string(DONE_HTML, url=dl_url, name=out_path.name)

@app.get("/files/<path:filename>")
def download_file(filename):
    return send_from_directory(RESULTS_DIR, filename, as_attachment=True, mimetype="video/mp4")

@app.get("/health")
def health():
    return "ok", 200

if __name__ == "__main__":
    # Ensure model at startup (so first request is faster)
    ensure_model()
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
