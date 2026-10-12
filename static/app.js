const NAV_STATUS = {
  0: "Under way (engine)", 1: "At anchor", 2: "Not under command",
  3: "Restricted manoeuvrability", 4: "Constrained by draught", 5: "Moored",
  6: "Aground", 7: "Fishing", 8: "Under way sailing", 15: "Not defined",
};
const COLORS = { normal: "#4da3ff", STOPPED_OFFSHORE: "#ff5d5d", HIGH_SPEED: "#ffb020" };
const LABELS = { STOPPED_OFFSHORE: "Stopped offshore", HIGH_SPEED: "High speed" };
const MAX_ROWS = 150;
const REFRESH_MS = 30000;

// ---- map ----
const map = L.map("map", { preferCanvas: true }).setView([50.5, 1.0], 7);
L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19,
  attribution:
    '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
}).addTo(map);
const layer = L.layerGroup().addTo(map);

// ---- state ----
let vessels = [];
let byId = {};
const markers = {};
let filter = "all";
let query = "";
let selected = null;

const $ = (id) => document.getElementById(id);
const listEl = $("list");

// Ship names come from an outside feed, so never insert them as raw HTML.
const esc = (s) =>
  String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const speedText = (v) => (v.speed == null ? "n/a" : v.speed.toFixed(1) + " kn");

function styleFor(v) {
  const flagged = !!v.alert_type;
  const color = COLORS[v.alert_type] || COLORS.normal;
  return {
    radius: flagged ? 8 : 4,
    color: v.mmsi === selected ? "#ffffff" : color,
    weight: v.mmsi === selected ? 3 : 1,
    fillColor: color,
    fillOpacity: flagged ? 0.85 : 0.6,
  };
}

function popupHtml(v) {
  const status = v.nav_status == null ? "Unknown" : NAV_STATUS[v.nav_status] || "Code " + v.nav_status;
  return (
    `<b>${esc(v.name)}</b><br>` +
    `<span class="muted">MMSI ${esc(v.mmsi)}</span><br>` +
    `Speed: ${speedText(v)}<br>Status: ${esc(status)}` +
    (v.alert ? `<div class="alert">&#9888; ${esc(v.alert)}</div>` : "")
  );
}

function matches(v) {
  if (filter !== "all" && v.alert_type !== filter) return false;
  if (query) {
    const q = query.toLowerCase();
    if (!String(v.name || "").toLowerCase().includes(q) && !String(v.mmsi).includes(q)) return false;
  }
  return true;
}

function upsert(v) {
  const m = markers[v.mmsi];
  if (m) {
    m.setLatLng([v.lat, v.lon]).setStyle(styleFor(v)).setPopupContent(popupHtml(v));
  } else {
    const mk = L.circleMarker([v.lat, v.lon], styleFor(v)).bindPopup(popupHtml(v));
    mk.on("click", () => select(v.mmsi, false));
    markers[v.mmsi] = mk;
  }
}

function syncVisibility() {
  vessels.forEach((v) => {
    const m = markers[v.mmsi];
    if (!m) return;
    const show = matches(v);
    const on = layer.hasLayer(m);
    if (show && !on) layer.addLayer(m);
    else if (!show && on) layer.removeLayer(m);
  });
}

function renderStats() {
  const stopped = vessels.filter((v) => v.alert_type === "STOPPED_OFFSHORE").length;
  const fast = vessels.filter((v) => v.alert_type === "HIGH_SPEED").length;
  $("stat-total").textContent = vessels.length.toLocaleString();
  $("stat-alerts").textContent = (stopped + fast).toLocaleString();
  $("stat-stopped").textContent = stopped.toLocaleString();
  $("stat-fast").textContent = fast.toLocaleString();
}

function renderList() {
  const rows = vessels
    .filter(matches)
    .sort((a, b) => (b.alert_type ? 1 : 0) - (a.alert_type ? 1 : 0) || String(a.name).localeCompare(String(b.name)));
  const top = listEl.scrollTop;
  let html = rows
    .slice(0, MAX_ROWS)
    .map(
      (v) => `
      <li class="row${v.mmsi === selected ? " sel" : ""}" data-id="${esc(v.mmsi)}">
        <span class="swatch" style="background:${COLORS[v.alert_type] || COLORS.normal}"></span>
        <div class="info">
          <div class="nm">${esc(v.name)}</div>
          <div class="sub">MMSI ${esc(v.mmsi)} &middot; ${speedText(v)}</div>
          ${v.alert ? `<div class="msg">${esc(v.alert)}</div>` : ""}
        </div>
        ${v.alert_type ? `<span class="badge ${v.alert_type}">${LABELS[v.alert_type]}</span>` : ""}
      </li>`
    )
    .join("");
  if (!rows.length) html = '<li class="empty">No ships match.</li>';
  else if (rows.length > MAX_ROWS) html += `<li class="more">Showing ${MAX_ROWS} of ${rows.length.toLocaleString()}. Use search to narrow down.</li>`;
  listEl.innerHTML = html;
  listEl.scrollTop = top;
}

function select(mmsi, fly) {
  const prev = selected;
  selected = mmsi;
  [prev, mmsi].forEach((id) => {
    if (id && byId[id] && markers[id]) markers[id].setStyle(styleFor(byId[id]));
  });
  if (fly && markers[mmsi]) {
    const mk = markers[mmsi];
    map.flyTo(mk.getLatLng(), Math.max(map.getZoom(), 10), { duration: 0.8 });
    mk.openPopup();
  }
  renderList();
}

async function refresh() {
  try {
    const res = await fetch("/vessels");
    if (!res.ok) throw new Error("HTTP " + res.status);
    vessels = await res.json();
    byId = Object.fromEntries(vessels.map((v) => [v.mmsi, v]));
    Object.keys(markers).forEach((id) => {
      if (!byId[id]) {
        layer.removeLayer(markers[id]);
        delete markers[id];
      }
    });
    vessels.forEach(upsert);
    syncVisibility();
    renderStats();
    renderList();
    $("dot").classList.remove("off");
    $("updated").textContent = `${vessels.length.toLocaleString()} ships · updated ${new Date().toLocaleTimeString()}`;
  } catch (err) {
    $("dot").classList.add("off");
    $("updated").textContent = "Connection lost, retrying…";
  }
}

// ---- ocean flow: animated waves driven by real data (Open-Meteo Marine API) ----
const OCEAN = { south: 47, north: 54, west: -7, east: 4, step: 0.5 }; // English Channel and approaches
const WAVE_CACHE_KEY = "cargolens-waves-v1";
const WAVE_TTL_MS = 60 * 60 * 1000; // wave forecasts change hourly
const WAVE_BATCH = 100;
const OPEN_METEO_ATTR = 'Wave data &copy; <a href="https://open-meteo.com/">Open-Meteo</a>';
const BUCKET_COLORS = ["rgba(80,190,230,0.40)", "rgba(120,215,240,0.50)", "rgba(190,235,250,0.60)", "rgba(255,255,255,0.70)"];
const RAD = Math.PI / 180;

const ocean = {
  field: null,
  enabled: !(window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches),
  running: false,
  particles: [],
  raf: 0,
  w: 0,
  h: 0,
  status: "Loading wave data…",
  credited: false,
};

// A pane between the map tiles and the ship markers.
const oceanPane = map.createPane("ocean");
oceanPane.style.zIndex = 250;
oceanPane.style.pointerEvents = "none";
const canvas = document.createElement("canvas");
canvas.className = "ocean-canvas";
oceanPane.appendChild(canvas);
const ctx = canvas.getContext("2d");

function place() {
  L.DomUtil.setPosition(canvas, map.containerPointToLayerPoint([0, 0]));
}

function sizeCanvas() {
  const s = map.getSize();
  const dpr = window.devicePixelRatio || 1;
  ocean.w = s.x;
  ocean.h = s.y;
  canvas.width = Math.round(s.x * dpr);
  canvas.height = Math.round(s.y * dpr);
  canvas.style.width = s.x + "px";
  canvas.style.height = s.y + "px";
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  place();
}

// Wave height (m) and direction at a lat/lon, or null if the spot is land or outside our data.
function sampleWave(lat, lon) {
  const f = ocean.field;
  const fy = (lat - OCEAN.south) / OCEAN.step;
  const fx = (lon - OCEAN.west) / OCEAN.step;
  if (fy < 0 || fx < 0 || fy > f.rows - 1 || fx > f.cols - 1) return null;
  if (f.h[Math.round(fy) * f.cols + Math.round(fx)] == null) return null; // nearest point is land
  const i0 = Math.floor(fy), j0 = Math.floor(fx);
  const i1 = Math.min(i0 + 1, f.rows - 1), j1 = Math.min(j0 + 1, f.cols - 1);
  const ty = fy - i0, tx = fx - j0;
  const corners = [
    [i0, j0, (1 - ty) * (1 - tx)], [i0, j1, (1 - ty) * tx],
    [i1, j0, ty * (1 - tx)], [i1, j1, ty * tx],
  ];
  let wsum = 0, hs = 0, east = 0, north = 0;
  for (const [i, j, w] of corners) {
    const idx = i * f.cols + j;
    if (f.h[idx] == null || w <= 0) continue;
    // wave_direction is where waves come FROM, so they travel the opposite way
    const to = (f.dir[idx] + 180) * RAD;
    hs += f.h[idx] * w;
    east += Math.sin(to) * w;
    north += Math.cos(to) * w;
    wsum += w;
  }
  if (wsum < 0.0001) return null;
  return { h: hs / wsum, e: east / wsum, n: north / wsum };
}

function covers() {
  const b = map.getBounds();
  return b.getSouth() < OCEAN.north && b.getNorth() > OCEAN.south && b.getWest() < OCEAN.east && b.getEast() > OCEAN.west;
}

function respawn(p, initial) {
  p.live = false;
  p.life = 70 + Math.random() * 90;
  p.age = initial ? Math.random() * p.life : 0;
  for (let tries = 0; tries < 6; tries++) {
    const x = Math.random() * ocean.w;
    const y = Math.random() * ocean.h;
    const ll = map.containerPointToLatLng([x, y]);
    if (sampleWave(ll.lat, ll.lng)) {
      p.x = p.px = x;
      p.y = p.py = y;
      p.live = true;
      return;
    }
  }
}

function seedParticles() {
  const n = Math.min(1800, Math.floor((ocean.w * ocean.h) / 1000));
  ocean.particles = Array.from({ length: n }, () => {
    const p = { x: 0, y: 0, px: 0, py: 0, age: 0, life: 0, live: false };
    respawn(p, true);
    return p;
  });
}

function frame() {
  if (!ocean.running) return;
  // fade the previous frame a little, so moving particles leave soft trails
  ctx.globalCompositeOperation = "destination-out";
  ctx.fillStyle = "rgba(0,0,0,0.09)";
  ctx.fillRect(0, 0, ocean.w, ocean.h);
  ctx.globalCompositeOperation = "source-over";
  ctx.lineWidth = 1.2;
  ctx.lineCap = "round";

  const buckets = [[], [], [], []];
  for (const p of ocean.particles) {
    if (!p.live || p.age++ > p.life) { respawn(p, false); continue; }
    const ll = map.containerPointToLatLng([p.x, p.y]);
    const s = sampleWave(ll.lat, ll.lng);
    if (!s) { p.live = false; continue; }
    const mag = Math.hypot(s.e, s.n) || 1;
    const speed = 0.4 + 0.45 * Math.min(s.h, 4); // bigger waves move faster
    p.px = p.x;
    p.py = p.y;
    p.x += (s.e / mag) * speed;
    p.y -= (s.n / mag) * speed;
    if (p.x < 0 || p.y < 0 || p.x > ocean.w || p.y > ocean.h) { p.live = false; continue; }
    buckets[Math.min(3, Math.floor(s.h))].push(p);
  }
  for (let b = 0; b < 4; b++) {
    ctx.strokeStyle = BUCKET_COLORS[b];
    ctx.beginPath();
    for (const p of buckets[b]) {
      ctx.moveTo(p.px, p.py);
      ctx.lineTo(p.x, p.y);
    }
    ctx.stroke();
  }
  ocean.raf = requestAnimationFrame(frame);
}

function startOcean() {
  if (ocean.running || !ocean.enabled || !ocean.field || !covers()) return;
  ocean.running = true;
  seedParticles();
  canvas.style.opacity = 1;
  ocean.raf = requestAnimationFrame(frame);
}

function stopOcean() {
  ocean.running = false;
  cancelAnimationFrame(ocean.raf);
  ctx.clearRect(0, 0, ocean.w, ocean.h);
}

async function fetchWaveBatch(lats, lons) {
  const url =
    "https://marine-api.open-meteo.com/v1/marine" +
    `?latitude=${lats.join(",")}&longitude=${lons.join(",")}&current=wave_height,wave_direction`;
  const res = await fetch(url);
  if (!res.ok) throw new Error("HTTP " + res.status);
  const data = await res.json();
  const list = Array.isArray(data) ? data : [data];
  return lats.map((_, i) => {
    const c = list[i] && list[i].current;
    const h = c && c.wave_height;
    const dir = c && c.wave_direction;
    return typeof h === "number" && typeof dir === "number" ? { h, dir } : null; // null = land / no data
  });
}

async function loadWaves(force) {
  const rows = Math.round((OCEAN.north - OCEAN.south) / OCEAN.step) + 1;
  const cols = Math.round((OCEAN.east - OCEAN.west) / OCEAN.step) + 1;
  if (!force) {
    try {
      const c = JSON.parse(sessionStorage.getItem(WAVE_CACHE_KEY) || "null");
      if (c && Date.now() - c.t < WAVE_TTL_MS && c.h.length === rows * cols) return { rows, cols, h: c.h, dir: c.dir, t: c.t };
    } catch (e) { /* no cache, fetch fresh */ }
  }
  const lats = [], lons = [];
  for (let i = 0; i < rows; i++) {
    for (let j = 0; j < cols; j++) {
      lats.push(+(OCEAN.south + i * OCEAN.step).toFixed(2));
      lons.push(+(OCEAN.west + j * OCEAN.step).toFixed(2));
    }
  }
  const jobs = [];
  for (let k = 0; k < lats.length; k += WAVE_BATCH) {
    const la = lats.slice(k, k + WAVE_BATCH), lo = lons.slice(k, k + WAVE_BATCH);
    jobs.push(fetchWaveBatch(la, lo).catch(() => la.map(() => null)));
  }
  const cells = (await Promise.all(jobs)).flat();
  const valid = cells.filter(Boolean).length;
  if (valid < 10) throw new Error("only " + valid + " sea points returned");
  const out = { rows, cols, h: cells.map((c) => (c ? c.h : null)), dir: cells.map((c) => (c ? c.dir : null)), t: Date.now() };
  try { sessionStorage.setItem(WAVE_CACHE_KEY, JSON.stringify({ t: out.t, h: out.h, dir: out.dir })); } catch (e) { /* ignore */ }
  return out;
}

async function loadOcean(force) {
  try {
    ocean.field = await loadWaves(force);
    const time = new Date(ocean.field.t).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    ocean.status = `Live wave data, ${time}`;
    if (!ocean.credited) { map.attributionControl.addAttribution(OPEN_METEO_ATTR); ocean.credited = true; }
    startOcean();
  } catch (err) {
    console.warn("Wave data unavailable:", err);
    ocean.field = null;
    ocean.status = "Wave data unavailable";
    stopOcean();
  }
  $("ocean-status").textContent = ocean.status;
}

const OceanControl = L.Control.extend({
  options: { position: "bottomleft" },
  onAdd() {
    const div = L.DomUtil.create("div", "ocean-ctl");
    div.innerHTML =
      '<label class="ocean-toggle"><input type="checkbox" id="ocean-toggle"> Ocean flow</label>' +
      '<div class="ocean-legend"><span>calm</span><i></i><span>4 m waves</span></div>' +
      '<div class="ocean-status" id="ocean-status">' + ocean.status + "</div>";
    L.DomEvent.disableClickPropagation(div);
    return div;
  },
});
new OceanControl().addTo(map);
$("ocean-toggle").checked = ocean.enabled;
$("ocean-toggle").addEventListener("change", (e) => {
  ocean.enabled = e.target.checked;
  if (ocean.enabled) startOcean();
  else stopOcean();
});

// Animation pauses while the map moves, then restarts for the new view.
map.on("movestart zoomstart", () => { canvas.style.opacity = 0; stopOcean(); });
map.on("moveend zoomend", () => { place(); startOcean(); });
map.on("resize", () => { stopOcean(); sizeCanvas(); startOcean(); });
sizeCanvas();
loadOcean(false);
setInterval(() => loadOcean(true), WAVE_TTL_MS);

// ---- events ----
$("search").addEventListener("input", (e) => {
  query = e.target.value.trim();
  syncVisibility();
  renderList();
});
$("chips").addEventListener("click", (e) => {
  const btn = e.target.closest(".chip");
  if (!btn) return;
  filter = btn.dataset.filter;
  document.querySelectorAll(".chip").forEach((c) => c.classList.toggle("active", c === btn));
  syncVisibility();
  renderList();
});
listEl.addEventListener("click", (e) => {
  const row = e.target.closest("li[data-id]");
  if (row) select(row.dataset.id, true);
});

refresh();
setInterval(refresh, REFRESH_MS);