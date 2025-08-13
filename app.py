from flask import Flask, render_template_string, jsonify, request
from datetime import datetime

app = Flask(__name__)

# In-memory state (use a real DB in production)
visited_zones = {}
custom_zones = {}

# Zones organized by floor
zones_data = {
    'Basement': [{'id': '10151853', 'location': 'Basement Interior', 'visited': False}],
    'Floor 2': [
        {'id': '10151808', 'location': 'Catwalk Stairwell', 'visited': False},
        {'id': '10150864', 'location': 'East Stairwell', 'visited': False},
        {'id': '10151804', 'location': 'Gym', 'visited': False},
        {'id': '10150871', 'location': 'West Stairwell', 'visited': False}
    ],
    'Floor 3': [
        {'id': '10151833', 'location': 'Patio & Lounge', 'visited': False},
        {'id': '10150882', 'location': 'West Stairwell', 'visited': False},
        {'id': '10150874', 'location': 'Catwalk Stairwell', 'visited': False}
    ],
    'Floor 4': [
        {'id': '10151806', 'location': 'Catwalk Stairwell', 'visited': False},
        {'id': '10151844', 'location': 'East Stairwell', 'visited': False},
        {'id': '10151851', 'location': 'West Stairwell', 'visited': False}
    ],
    'Floor 5': [
        {'id': '10151848', 'location': 'Catwalk Stairwell', 'visited': False},
        {'id': '10151839', 'location': 'East Stairwell', 'visited': False},
        {'id': '10151815', 'location': 'West Stairwell', 'visited': False}
    ],
    'Floor 6': [
        {'id': '10151834', 'location': 'Alley Stairwell', 'visited': False},
        {'id': '10151842', 'location': 'East Stairwell', 'visited': False},
        {'id': '10150866', 'location': 'West Stairwell', 'visited': False}
    ],
    'Floor 7': [
        {'id': '10150873', 'location': 'Alley Stairwell', 'visited': False},
        {'id': '10151819', 'location': 'East Stairwell', 'visited': False},
        {'id': '10151811', 'location': 'West Stairwell', 'visited': False}
    ],
    'Floor 8': [
        {'id': '10150867', 'location': 'Alley Stairwell', 'visited': False},
        {'id': '10151814', 'location': 'East', 'visited': False},
        {'id': '10151835', 'location': 'West', 'visited': False}
    ],
    'Floor 9': [
        {'id': '10150881', 'location': 'Alley Stairwell', 'visited': False},
        {'id': '10150885', 'location': 'East', 'visited': False},
        {'id': '10150887', 'location': 'West Stairwell', 'visited': False}
    ],
    'Floor 10': [
        {'id': '10150865', 'location': 'Alley Stairwell', 'visited': False},
        {'id': '10151807', 'location': 'East', 'visited': False},
        {'id': '10151852', 'location': 'West Stairwell', 'visited': False}
    ],
    'Floor 11': [
        {'id': '10151805', 'location': 'Alley Stairwell', 'visited': False},
        {'id': '10151825', 'location': 'East', 'visited': False},
        {'id': '10151816', 'location': 'West Stairwell', 'visited': False}
    ],
    'Floor 12': [
        {'id': '10150880', 'location': 'Alley Stairwell', 'visited': False},
        {'id': '10150884', 'location': 'East Stairwell', 'visited': False},
        {'id': '10151829', 'location': 'West Stairwell', 'visited': False}
    ],
    'Floor 14': [
        {'id': '10150889', 'location': 'Alley Stairwell', 'visited': False},
        {'id': '10150875', 'location': 'East', 'visited': False},
        {'id': '10151818', 'location': 'West Stairwell', 'visited': False}
    ],
    'Floor 15': [
        {'id': '10151837', 'location': '15th Floor', 'visited': False},
        {'id': '10151827', 'location': 'Alley Stairwell', 'visited': False}
    ],
    'Floor 16': [{'id': '10151847', 'location': 'Penthouse', 'visited': False}],
    'Floor 17': [{'id': '10150879', 'location': 'Floor 17', 'visited': False}]
}

# Allow Web NFC on this origin (some hosts block it by default)
@app.after_request
def add_headers(resp):
    # Allow only this origin to use NFC
    resp.headers['Permissions-Policy'] = 'nfc=(self)'
    # (Optional) prevent embedding that could disable features in iframes
    resp.headers['X-Frame-Options'] = 'SAMEORIGIN'
    return resp

HTML = """
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Plaza 555 — NFC Tour</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  :root { --accent:#ff6b35; --bg:#111827; --card:#1f2937; --ok:#16a34a; --muted:#9ca3af; }
  * { box-sizing:border-box; }
  body { margin:0; font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell;
         background:var(--bg); color:white; }
  header { position:sticky; top:0; background:#0b1220; padding:12px 16px; border-bottom:1px solid #223;
           display:flex; gap:12px; align-items:center; flex-wrap:wrap; }
  h1 { margin:0; font-size:18px; font-weight:700; }
  .row { display:flex; gap:8px; align-items:center; flex-wrap:wrap; margin-left:auto; }
  select, input[type=text] { background:#0f172a; color:white; border:1px solid #334155; border-radius:8px; padding:8px 10px; }
  button { background:var(--accent); color:white; border:0; border-radius:8px; padding:10px 12px; font-weight:700; cursor:pointer; }
  button:disabled { opacity:.6; cursor:not-allowed; }
  main { max-width:900px; margin:16px auto; padding:0 12px 80px; }
  .stats { display:flex; gap:16px; margin:12px 0 16px; font-size:14px; color:var(--muted); }
  .bar { height:8px; background:#233; border-radius:4px; overflow:hidden; }
  .fill { height:100%; width:0%; background:linear-gradient(90deg,#22c55e,#84cc16); transition:width .3s ease; }
  .list { display:grid; gap:10px; }
  .card { background:var(--card); border:1px solid #243042; border-radius:12px; padding:12px; display:flex; gap:12px; align-items:center; justify-content:space-between; }
  .meta { display:flex; flex-direction:column; gap:4px; }
  .id { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace; color:var(--accent); }
  .status { font-size:12px; color:var(--muted); }
  .status.ok { color:#86efac; }
  .toast { position:fixed; left:50%; transform:translateX(-50%); bottom:16px; background:#0f172a; color:white;
           border:1px solid #334155; padding:10px 12px; border-radius:8px; display:none; z-index:1000; }
  form.add { display:flex; gap:8px; flex-wrap:wrap; margin-top:8px; }
  .hint { font-size:12px; color:var(--muted); margin-left:auto; }

  /* NFC sheet */
  .sheet { position:fixed; inset:0; background:rgba(0,0,0,.6); display:none; align-items:center; justify-content:center; z-index:999; }
  .sheet .box { width:min(420px,92vw); background:#0f172a; border:1px solid #243042; border-radius:12px; padding:18px; }
  .sheet h3 { margin:0 0 10px; font-size:18px; }
  .sheet p { margin:8px 0; color:#cbd5e1; font-size:14px; }
  .sheet .id { color:var(--accent); }
  .sheet .row { margin-top:12px; justify-content:flex-end; }
</style>
</head>
<body>
<header>
  <h1>🏢 Plaza 555 — NFC Tour</h1>
  <div class="row">
    <label class="hint" id="envHint">Use Chrome on Android • HTTPS or localhost</label>
    <select id="floorSelect" aria-label="Choose floor">
      {% for floor in zones_data.keys() %}
        <option value="{{ floor }}">{{ floor }}</option>
      {% endfor %}
    </select>
  </div>
  <div class="row" style="width:100%">
    <div style="flex:1">
      <div class="stats">
        <div><strong id="visitedCount">0</strong>/<span id="totalCount">0</span> visited</div>
        <div>• Remaining: <span id="remainingCount">0</span></div>
        <div>• Floor: <span id="floorStats">0/0</span></div>
      </div>
      <div class="bar"><div class="fill" id="progressFill"></div></div>
    </div>
  </div>
</header>

<main>
  <section>
    <h2 style="font-size:16px; margin:6px 0;">Zones</h2>
    <div class="list" id="zoneList">
      {% for floor, zones in zones_data.items() %}
        {% for z in zones %}
          <div class="card" data-floor="{{ floor }}" id="zone-{{ z.id }}">
            <div class="meta">
              <div><strong>{{ z.location }}</strong> <span style="opacity:.7">• {{ floor }}</span></div>
              <div class="id">NFC: {{ z.id }}</div>
              <div class="status" id="status-{{ z.id }}">Not visited</div>
            </div>
            <div style="display:flex; gap:8px;">
              <button class="write" onclick="writeNFC('{{ z.id }}')">Write to NFC Tag</button>
            </div>
          </div>
        {% endfor %}
      {% endfor %}
    </div>
  </section>

  <section style="margin-top:24px;">
    <h2 style="font-size:16px; margin:6px 0;">Add Custom Tag</h2>
    <form class="add" onsubmit="return addCustom(event)">
      <input type="text" id="tagId" placeholder="Tag ID (e.g. 10151999)" maxlength="8" inputmode="numeric" pattern="[0-9]{8}" required>
      <input type="text" id="tagLocation" placeholder="Location (e.g. Security Office)" required>
      <select id="tagFloor" required>
        {% for floor in zones_data.keys() %}
          <option value="{{ floor }}">{{ floor }}</option>
        {% endfor %}
      </select>
      <button type="submit">Add</button>
    </form>
  </section>
</main>

<div class="toast" id="toast"></div>

<!-- NFC status sheet -->
<div class="sheet" id="nfcSheet">
  <div class="box">
    <h3 id="sheetTitle">Writing to tag…</h3>
    <p id="sheetMsg">Hold the NFC tag against the phone to write<br>Value: <span class="id" id="sheetId"></span></p>
    <p id="sheetHint" style="font-size:12px; color:#94a3b8;">If nothing happens in ~20s, ensure NFC is ON and try a fresh tag.</p>
    <div class="row">
      <button id="sheetClose" onclick="closeSheet()">Close</button>
    </div>
  </div>
</div>

<script>
  // --- Simple state ---
  const totalZones = {{ total_zones }};
  let visited = new Set();
  const zoneList = document.getElementById('zoneList');
  const floorSelect = document.getElementById('floorSelect');

  // --- Helpers ---
  function showToast(msg, ok=false) {
    const el = document.getElementById('toast');
    el.textContent = msg;
    el.style.display = 'block';
    el.style.borderColor = ok ? '#14532d' : '#334155';
    el.style.color = ok ? '#86efac' : 'white';
    setTimeout(() => { el.style.display='none'; }, 2200);
  }
  function updateProgress() {
    const v = visited.size;
    const pct = totalZones ? Math.round((v/totalZones)*100) : 0;
    document.getElementById('visitedCount').textContent = v;
    document.getElementById('totalCount').textContent = totalZones;
    document.getElementById('remainingCount').textContent = totalZones - v;
    document.getElementById('progressFill').style.width = pct + '%';

    const cur = floorSelect.value;
    const cards = [...document.querySelectorAll('.card[data-floor="'+cur+'"]')];
    const ok = cards.filter(c => c.classList.contains('visited')).length;
    document.getElementById('floorStats').textContent = ok + '/' + cards.length;
  }
  function filterByFloor() {
    const cur = floorSelect.value;
    [...document.querySelectorAll('.card')].forEach(c => {
      c.style.display = (c.dataset.floor === cur) ? '' : 'none';
    });
    updateProgress();
  }
  function markVisited(zoneId) {
    visited.add(zoneId);
    const card = document.getElementById('zone-' + zoneId);
    const status = document.getElementById('status-' + zoneId);
    if (card) card.classList.add('visited');
    if (status) { status.textContent = 'Visited at ' + new Date().toLocaleTimeString(); status.classList.add('ok'); }
    updateProgress();
    fetch('/mark_visited', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ zoneId })
    }).catch(()=>{});
  }

  // --- NFC sheet controls ---
  const sheet = document.getElementById('nfcSheet');
  const sheetTitle = document.getElementById('sheetTitle');
  const sheetMsg = document.getElementById('sheetMsg');
  const sheetId = document.getElementById('sheetId');
  function openSheet(title, msg, idText='') {
    sheetTitle.textContent = title;
    sheetMsg.innerHTML = msg;
    sheetId.textContent = idText;
    sheet.style.display = 'flex';
  }
  function closeSheet(){ sheet.style.display='none'; }

  // --- NFC write with explicit UI + timeout + nicer errors ---
  const NFC_TIMEOUT_MS = 20000;

  async function writeNFC(zoneId) {
    const btn = document.querySelector('#zone-' + zoneId + ' .write');

    if (!('NDEFReader' in window)) {
      showToast('Web NFC not supported. Use Chrome on Android.', false);
      return;
    }
    if (!window.isSecureContext) {
      showToast('This page is not HTTPS (or localhost). NFC blocked.', false);
      return;
    }

    // visible sheet
    openSheet('Ready to write', 'Hold the NFC tag against the phone to write<br>Value: <span class="id" id="sheetId"></span>', zoneId);

    let controller;
    try {
      btn.disabled = true;
      btn.textContent = 'Hold tag to phone…';

      controller = new AbortController();
      const t = setTimeout(() => controller.abort('Timeout'), NFC_TIMEOUT_MS);

      const ndef = new NDEFReader();

      // Write an explicit text record (more interoperable than implicit string)
      await ndef.write(
        { records: [{ recordType: 'text', data: zoneId }] },
        { signal: controller.signal }
      );

      clearTimeout(t);

      // Success UI
      sheetTitle.textContent = '✅ Written!';
      sheetMsg.innerHTML = 'Tag successfully written with<br>Value: <span class="id">'+escapeHtml(zoneId)+'</span>';
      if (navigator.vibrate) navigator.vibrate(80);
      showToast('✅ Written: ' + zoneId, true);
      markVisited(zoneId);
    } catch (err) {
      // Map common errors to friendly text
      let msg = 'NFC error.';
      if (err === 'Timeout' || (err && (err.name === 'AbortError'))) msg = 'Timed out waiting for a tag. Make sure NFC is ON and tap a tag.';
      else if (err && err.name === 'NotAllowedError') msg = 'NFC permission denied. Tap again and allow when prompted.';
      else if (err && err.name === 'NotSupportedError') msg = 'Device/Browser does not support NFC or it is disabled.';
      else if (err && err.name === 'SecurityError') msg = 'Web NFC requires HTTPS (or http://localhost).';
      else if (err && err.name === 'NetworkError') msg = 'NFC hardware busy/unavailable. Toggle NFC and retry.';
      else if (err && err.message) msg = err.message;

      sheetTitle.textContent = '❌ Failed';
      sheetMsg.textContent = msg;
      showToast('❌ ' + msg, false);
      console.error('NFC write failed:', err);
    } finally {
      btn.disabled = false;
      btn.textContent = 'Write to NFC Tag';
    }
  }

  // --- Add custom tag ---
  async function addCustom(e) {
    e.preventDefault();
    const id = document.getElementById('tagId').value.trim();
    const location = document.getElementById('tagLocation').value.trim();
    const floor = document.getElementById('tagFloor').value;

    if (!/^[0-9]{8}$/.test(id)) {
      showToast('Tag ID must be exactly 8 digits.', false);
      return false;
    }

    try {
      const res = await fetch('/add_custom_tag', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({ id, location, floor })
      });
      const data = await res.json();
      if (!data.success) throw new Error(data.error || 'Failed to add tag');

      const card = document.createElement('div');
      card.className = 'card';
      card.dataset.floor = floor;
      card.id = 'zone-' + id;
      card.innerHTML = `
        <div class="meta">
          <div><strong>${escapeHtml(location)}</strong> <span style="opacity:.7">• ${escapeHtml(floor)}</span></div>
          <div class="id">NFC: ${escapeHtml(id)}</div>
          <div class="status" id="status-${escapeHtml(id)}">Not visited</div>
        </div>
        <div><button class="write" onclick="writeNFC('${escapeAttr(id)}')">Write to NFC Tag</button></div>
      `;
      document.getElementById('zoneList').appendChild(card);

      document.getElementById('tagId').value = '';
      document.getElementById('tagLocation').value = '';
      showToast('Custom tag added.', true);
      filterByFloor();
    } catch (err) {
      console.error(err);
      showToast('❌ ' + (err.message || 'Add failed'), false);
    }
    return false;
  }

  function escapeHtml(s){ return s.replace(/[&<>"']/g, m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[m])); }
  function escapeAttr(s){ return s.replace(/['"\\]/g, '\\$&'); }

  // --- Init ---
  document.addEventListener('DOMContentLoaded', () => {
    const httpsOk = (location.protocol === 'https:') || (location.hostname === 'localhost' || location.hostname === '127.0.0.1');
    if (!httpsOk) document.getElementById('envHint').textContent = '⚠️ Use HTTPS (or http://localhost) for NFC';

    const fs = document.getElementById('floorSelect');
    fs.value = fs.options[0].value;
    fs.addEventListener('change', filterByFloor);
    filterByFloor();

    // Re-add any custom tags on reload
    fetch('/get_custom_tags').then(r=>r.json()).then(data=>{
      if (!data.tags) return;
      for (const t of data.tags) {
        if (document.getElementById('zone-' + t.id)) continue;
        const card = document.createElement('div');
        card.className = 'card';
        card.dataset.floor = t.floor;
        card.id = 'zone-' + t.id;
        card.innerHTML = `
          <div class="meta">
            <div><strong>${escapeHtml(t.location)}</strong> <span style="opacity:.7">• ${escapeHtml(t.floor)}</span></div>
            <div class="id">NFC: ${escapeHtml(t.id)}</div>
            <div class="status" id="status-${escapeHtml(t.id)}">Not visited</div>
          </div>
          <div><button class="write" onclick="writeNFC('${escapeAttr(t.id)}')">Write to NFC Tag</button></div>
        `;
        document.getElementById('zoneList').appendChild(card);
      }
      filterByFloor();
    }).catch(()=>{});
  });
</script>
</body>
</html>
"""

@app.route("/")
def index():
    total = sum(len(z) for z in zones_data.values())
    return render_template_string(HTML, zones_data=zones_data, total_zones=total)

@app.route("/mark_visited", methods=["POST"])
def mark_visited():
    data = request.get_json(force=True, silent=True) or {}
    zone_id = data.get("zoneId")
    if zone_id:
        visited_zones[zone_id] = {"timestamp": datetime.now().isoformat(), "visited": True}
        for floor, zones in zones_data.items():
            for z in zones:
                if z["id"] == zone_id:
                    z["visited"] = True
    return jsonify({"success": True, "zone_id": zone_id})

@app.route("/add_custom_tag", methods=["POST"])
def add_custom_tag():
    data = request.get_json(force=True, silent=True) or {}
    tag_id = (data.get("id") or "").strip()
    location = (data.get("location") or "").strip()
    floor = (data.get("floor") or "").strip()
    if not (tag_id and location and floor):
        return jsonify({"success": False, "error": "Missing required fields"})
    if not tag_id.isdigit() or len(tag_id) != 8:
        return jsonify({"success": False, "error": "Tag ID must be exactly 8 digits"})
    custom_zones.setdefault(floor, []).append({"id": tag_id, "location": location, "visited": False})
    zones_data.setdefault(floor, []).append({"id": tag_id, "location": location, "visited": False})
    return jsonify({"success": True, "tag": {"id": tag_id, "location": location, "floor": floor}})

@app.route("/get_custom_tags")
def get_custom_tags():
    res = []
    for floor, tags in custom_zones.items():
        for t in tags:
            res.append({"id": t["id"], "location": t["location"], "floor": floor})
    return jsonify({"tags": res})

@app.route("/status")
def status():
    total = sum(len(z) for z in zones_data.values())
    visited = len(visited_zones)
    return jsonify({
        "total_zones": total,
        "visited_zones": visited,
        "progress": round((visited / total * 100), 2) if total else 0,
        "visited_list": list(visited_zones.keys())
    })

if __name__ == "__main__":
    # For Web NFC, use HTTPS in production. Chrome treats http://localhost as secure for development.
    app.run(host="0.0.0.0", port=5000, debug=False)
