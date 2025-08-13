import os
from flask import Flask, Response

app = Flask(__name__)

INDEX_HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, viewport-fit=cover" />
  <title>Stickman Pose — Live</title>
  <style>
    :root { --bg:#0b0b0b; --fg:#f4f4f5; --muted:#a1a1aa; --accent:#60a5fa; }
    html, body { height: 100%; }
    body { margin:0; background:var(--bg); color:var(--fg); font:16px/1.4 system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,"Helvetica Neue",Arial,"Noto Sans",sans-serif; }
    .app { position:fixed; inset:0; display:grid; grid-template-rows:auto 1fr; }
    header { display:flex; gap:.75rem; align-items:center; padding:.75rem 1rem; border-bottom:1px solid #1f2937; background:rgba(17,17,20,.75); backdrop-filter:blur(6px); }
    header h1 { font-size:1rem; font-weight:600; margin:0; letter-spacing:.2px; }
    header .spacer { flex:1; }
    .btn { appearance:none; border:0; padding:.5rem .8rem; border-radius:.75rem; background:#111827; color:var(--fg); cursor:pointer; font-weight:600; }
    .btn:hover { background:#0f172a; }
    .btn[disabled]{ opacity:.5; cursor:not-allowed; }
    .toggle { display:inline-flex; align-items:center; gap:.4rem; font-size:.9rem; color:var(--muted); }
    .stage { position:relative; width:100%; height:calc(100vh - 56px); overflow:hidden; }
    canvas { position:absolute; inset:0; width:100%; height:100%; display:block; }
    video { position:absolute; inset:0; width:100%; height:100%; object-fit:cover; visibility:hidden; }
    .hint { position:absolute; left:50%; bottom:1rem; transform:translateX(-50%); color:var(--muted); font-size:.9rem; background:rgba(17,17,20,.6); padding:.4rem .6rem; border-radius:.5rem; }
    .toast { position:absolute; left:50%; top:1rem; transform:translateX(-50%); background:#111827; color:var(--fg); padding:.5rem .75rem; border-radius:.6rem; box-shadow:0 8px 24px rgba(0,0,0,.35); max-width:min(92vw, 800px); text-align:center; }
    .link { color:var(--accent); text-decoration:none; }
  </style>
</head>
<body>
  <div class="app">
    <header>
      <h1>Stickman Pose</h1>
      <div class="spacer"></div>
      <label class="toggle"><input id="showVideo" type="checkbox" checked /> Show video</label>
      <label class="toggle"><input id="mirror" type="checkbox" checked /> Mirror (selfie)</label>
      <button id="switchCam" class="btn" title="Switch front/back">Switch camera</button>
      <button id="startBtn" class="btn">Start camera</button>
      <button id="stopBtn" class="btn" disabled>Stop</button>
    </header>

    <div class="stage">
      <video id="video" playsinline autoplay muted></video>
      <canvas id="canvas"></canvas>
      <div id="toast" class="toast" hidden></div>
      <div class="hint">Tip: stand so your full body fits in view for best results.</div>
    </div>
  </div>

  <script type="module">
    import { PoseLandmarker, FilesetResolver } from "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.3";

    const MODEL_URL = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task";
    const WASM_BASE = "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.3/wasm";

    const els = {
      start: document.getElementById('startBtn'),
      stop: document.getElementById('stopBtn'),
      switchCam: document.getElementById('switchCam'),
      showVideo: document.getElementById('showVideo'),
      mirror: document.getElementById('mirror'),
      video: document.getElementById('video'),
      canvas: document.getElementById('canvas'),
      toast: document.getElementById('toast'),
    };

    const ctx = els.canvas.getContext('2d');
    const DPR = Math.min(devicePixelRatio || 1, 2); // cap DPR for perf

    let landmarker;
    let stream;
    let running = false;
    let facingMode = 'user'; // 'user' | 'environment'

    function toast(msg, ms = 3000) {
      els.toast.textContent = msg;
      els.toast.hidden = false;
      clearTimeout(els.toast._t);
      els.toast._t = setTimeout(() => (els.toast.hidden = true), ms);
    }

    function resizeCanvas() {
      const { innerWidth: w, innerHeight: h } = window;
      els.canvas.width = Math.floor(w * DPR);
      els.canvas.height = Math.floor(h * DPR);
    }
    window.addEventListener('resize', resizeCanvas, { passive: true });
    resizeCanvas();

    async function ensureLandmarker() {
      if (landmarker) return landmarker;
      const vision = await FilesetResolver.forVisionTasks(WASM_BASE);
      landmarker = await PoseLandmarker.createFromOptions(vision, {
        baseOptions: { modelAssetPath: MODEL_URL, delegate: 'GPU' },
        runningMode: 'VIDEO',
        numPoses: 1,
      });
      return landmarker;
    }

    async function startCamera() {
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode, width: { ideal: 640 }, height: { ideal: 480 } },
          audio: false,
        });
        els.video.srcObject = stream;
        await els.video.play();
        els.stop.disabled = false;
        els.start.disabled = true;
        running = true;
        loop();
        toast('Camera started. Move into view and strike a pose!');
      } catch (err) {
        console.error(err);
        toast('Could not access the camera. Grant permission and use HTTPS.');
      }
    }

    function stopCamera() {
      running = false;
      if (stream) {
        for (const t of stream.getTracks()) t.stop();
        stream = null;
      }
      els.start.disabled = false;
      els.stop.disabled = true;
      ctx.clearRect(0, 0, els.canvas.width, els.canvas.height);
    }

    async function switchCamera() {
      facingMode = facingMode === 'user' ? 'environment' : 'user';
      if (stream) stopCamera();
      await startCamera();
    }

    function mapPoint(lm, vw, vh, dx, dy, scale, mirror) {
      const x = (mirror ? (1 - lm.x) : lm.x) * vw * scale + dx;
      const y = lm.y * vh * scale + dy;
      return [x * DPR, y * DPR];
    }

    function drawStickman(landmarks, vw, vh, dx, dy, scale, mirror) {
      if (!landmarks || landmarks.length < 33) return;
      const L = landmarks;
      const p = (i) => mapPoint(L[i], vw, vh, dx, dy, scale, mirror);
      const w = 4 * DPR;

      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';

      if (els.showVideo.checked) {
        // background already drawn in loop
      } else {
        ctx.fillStyle = '#0b0b0b';
        ctx.fillRect(0, 0, els.canvas.width, els.canvas.height);
      }

      function seg(a, b) {
        const [x1, y1] = p(a); const [x2, y2] = p(b);
        ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.lineWidth = w; ctx.strokeStyle = '#ffffff'; ctx.stroke();
      }

      // BlazePose indexes
      const LS=11, RS=12, LE=13, RE=14, LW=15, RW=16, LH=23, RH=24, LK=25, RK=26, LA=27, RA=28, LHE=29, RHE=30, LFI=31, RFI=32;

      // Torso
      seg(LS, RS); seg(LH, RH); seg(LS, LH); seg(RS, RH);
      // Arms
      seg(LS, LE); seg(LE, LW); seg(RS, RE); seg(RE, RW);
      // Legs
      seg(LH, LK); seg(LK, LA); seg(RH, RK); seg(RK, RA);
      // Feet hints
      seg(LA, LHE); seg(LHE, LFI); seg(RA, RHE); seg(RHE, RFI);

      // Head: circle from ears/eyes, fallback to nose+shoulder span
      const NOSE=0, LEYE=2, REYE=5, LEAR=7, REAR=8;
      function dist(a, b) { const [x1,y1]=p(a), [x2,y2]=p(b); const dx=x1-x2, dy=y1-y2; return Math.hypot(dx,dy); }
      function mid(a, b) { const [x1,y1]=p(a), [x2,y2]=p(b); return [(x1+x2)/2, (y1+y2)/2]; }

      let center, radius;
      if (L[LEAR] && L[REAR]) { center = mid(LEAR, REAR); radius = Math.max(8*DPR, 0.7 * dist(LEAR, REAR)); }
      else if (L[LEYE] && L[REYE]) { center = mid(LEYE, REYE); radius = Math.max(8*DPR, 1.2 * dist(LEYE, REYE)); }
      else if (L[NOSE]) {
        const shoulderSpan = dist(LS, RS);
        const [nx, ny] = p(NOSE);
        center = [nx, ny - 0.4 * shoulderSpan];
        radius = Math.max(8*DPR, 0.35 * shoulderSpan);
      }
      if (center && radius) {
        ctx.beginPath(); ctx.arc(center[0], center[1], radius, 0, Math.PI*2); ctx.lineWidth = w; ctx.strokeStyle = '#ffffff'; ctx.stroke();
        const [sx, sy] = mid(LS, RS);
        ctx.beginPath(); ctx.moveTo(sx, sy); ctx.lineTo(center[0], center[1]); ctx.lineWidth = w; ctx.stroke();
      }
    }

    async function loop() {
      await ensureLandmarker();
      const v = els.video;
      const c = els.canvas;
      const w = v.videoWidth || 640;
      const h = v.videoHeight || 480;

      function frame() {
        if (!running) return;
        const cw = c.width / DPR, ch = c.height / DPR;
        const scale = Math.max(cw / w, ch / h);
        const drawW = w * scale, drawH = h * scale;
        const dx = (cw - drawW) / 2; const dy = (ch - drawH) / 2;

        ctx.clearRect(0, 0, c.width, c.height);
        if (els.showVideo.checked) {
          ctx.save();
          if (els.mirror.checked && facingMode === 'user') {
            ctx.translate(c.width, 0); ctx.scale(-1, 1);
            ctx.drawImage(v, Math.floor(dx*DPR), Math.floor(dy*DPR), Math.floor(drawW*DPR), Math.floor(drawH*DPR));
            ctx.restore();
          } else {
            ctx.drawImage(v, Math.floor(dx*DPR), Math.floor(dy*DPR), Math.floor(drawW*DPR), Math.floor(drawH*DPR));
          }
        }

        const now = performance.now();
        const result = landmarker.detectForVideo(v, now);
        if (result && result.landmarks && result.landmarks[0]) {
          const mirror = els.mirror.checked && facingMode === 'user';
          drawStickman(result.landmarks[0], w, h, dx, dy, scale, mirror);
        }

        requestAnimationFrame(frame);
      }
      requestAnimationFrame(frame);
    }

    els.start.addEventListener('click', startCamera);
    els.stop.addEventListener('click', stopCamera);
    els.switchCam.addEventListener('click', switchCamera);

    if (!('mediaDevices' in navigator) || !('getUserMedia' in navigator.mediaDevices)) {
      toast('Your browser does not support camera access. Try the latest Chrome/Safari/Edge/Firefox.');
      els.start.disabled = true;
      els.switchCam.disabled = true;
    }
    if (location.protocol !== 'https:' && location.hostname !== 'localhost') {
      toast('Camera requires HTTPS. Deploy to Render (it gives you HTTPS automatically).', 6000);
    }
  </script>
</body>
</html>"""

@app.get("/")
def index():
    return Response(INDEX_HTML, mimetype="text/html")

@app.get("/health")
def health():
    return "ok", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))  # Render sets PORT
    app.run(host="0.0.0.0", port=port)
