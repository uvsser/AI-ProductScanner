/**
 * AI Product Scanner — Frontend Application Logic
 * Live camera scanning, session management, photo scan & catalog.
 */

// ─── Global State ─────────────────────────────────────────────────────────────
let token = localStorage.getItem("scanner_token") || "";
let authMode = "login";
let activeCartId = null;      // legacy photo-scan cart
let activeSessionId = null;   // live scanner session
let cameraStream = null;
let captureTimerId = null;
let isCapturing = false;

const $ = (id) => document.getElementById(id);

// ─── Utilities ────────────────────────────────────────────────────────────────
function showToast(message, duration = 3500) {
  const el = $("toast");
  el.textContent = message;
  el.classList.add("show");
  clearTimeout(el._timer);
  el._timer = setTimeout(() => el.classList.remove("show"), duration);
}

function showBanner(elementId, text, type = "") {
  const el = $(elementId);
  if (!el) return;
  el.textContent = text;
  if (!text) {
    el.className = "status-banner";
    el.style.display = "none";
    return;
  }
  el.style.display = "block";
  el.className = "status-banner show" + (type ? " " + type : " info");
}

function esc(unsafe) {
  return String(unsafe ?? "").replace(/[&<>"']/g, (m) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[m])
  );
}

async function apiRequest(endpoint, options = {}) {
  const headers = { ...(token ? { Authorization: `Bearer ${token}` } : {}) };
  if (!(options.body instanceof FormData)) headers["Content-Type"] = "application/json";
  const response = await fetch(endpoint, { ...options, headers: { ...headers, ...(options.headers || {}) } });
  let data = {};
  try { data = await response.json(); } catch { /* non-JSON */ }
  if (!response.ok) {
    if (response.status === 401 && token) {
      token = ""; localStorage.removeItem("scanner_token"); updateViewState();
      showToast("Session expired. Please log in again.");
    }
    throw new Error(data.detail || `HTTP ${response.status}`);
  }
  return data;
}

// ─── View State ───────────────────────────────────────────────────────────────
function updateViewState() {
  const auth = !!token;
  $("authPanel").hidden = auth;
  $("appPanel").hidden = !auth;
  const accountEl = $("account");
  if (auth) {
    accountEl.innerHTML = `
      <span class="badge badge-accent">Authenticated</span>
      <button class="btn btn-secondary" id="logoutBtn">Log out</button>`;
    $("logoutBtn").onclick = () => {
      stopCamera(); token = ""; activeCartId = null; activeSessionId = null;
      localStorage.removeItem("scanner_token"); updateViewState(); showToast("Signed out successfully.");
    };
    loadUserProducts(); initializeActiveCart(); resetLiveUI();
  } else { accountEl.innerHTML = ""; }
}

// ─── Authentication ───────────────────────────────────────────────────────────
document.querySelectorAll("[data-auth]").forEach((btn) => {
  btn.onclick = () => {
    authMode = btn.dataset.auth;
    document.querySelectorAll("[data-auth]").forEach((b) => b.classList.toggle("active", b === btn));
    $("authSubmit").textContent = authMode === "login" ? "Sign In to Dashboard" : "Create Account & Sign In";
  };
});

$("authForm").onsubmit = async (e) => {
  e.preventDefault();
  try {
    const data = await apiRequest(`/api/auth/${authMode}`, {
      method: "POST", body: JSON.stringify({ email: $("email").value.trim(), password: $("password").value })
    });
    token = data.access_token; localStorage.setItem("scanner_token", token);
    updateViewState(); showToast(`Signed in as ${data.user.email}`);
  } catch (err) { showToast(err.message); }
};

// ─── Navigation ───────────────────────────────────────────────────────────────
document.querySelectorAll("[data-page]").forEach((btn) => {
  btn.onclick = () => {
    document.querySelectorAll("[data-page]").forEach((b) => b.classList.toggle("active", b === btn));
    document.querySelectorAll(".page").forEach((page) => { page.hidden = page.id !== btn.dataset.page; });
    if (btn.dataset.page === "catalogPage") loadUserProducts();
    if (btn.dataset.page === "scanPage") loadCartDetails();
    if (btn.dataset.page !== "livePage") stopCaptureLoop();
  };
});

// ═══════════════════════════════════════════════════════════════════════════════
//  LIVE CAMERA SCANNER
// ═══════════════════════════════════════════════════════════════════════════════

function resetLiveUI() {
  $("sessionBadge").textContent = "No Session";
  $("sessionBadge").className = "badge badge-subtle";
  $("sessionStatusText").textContent = "Start a session and activate the camera to begin scanning.";
  $("startCameraBtn").disabled = true;
  $("captureManualBtn").disabled = true;
  $("sessionActions").hidden = true;
  $("cartBadge").textContent = "0 items";
  $("totalAmount").textContent = "0.00 \u2014";
  $("sessionItems").innerHTML = `<div class="empty-state">
    <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="margin:0 auto 8px;display:block;opacity:.4"><circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"/></svg>
    Cart is empty.<br>Point camera at a product to automatically add it.</div>`;
  $("liveCandidates").hidden = true;
  $("candidateList").innerHTML = "";
}

// ── Session Management ────────────────────────────────────────────────────────
$("newSessionBtn").onclick = async () => {
  if (activeSessionId) {
    if (!confirm("A session is already open. Cancel it and start a new one?")) return;
    try { await apiRequest(`/api/v1/sessions/${activeSessionId}/cancel`, { method: "POST" }); } catch { /**/ }
    stopCamera(); activeSessionId = null;
  }
  try {
    const session = await apiRequest("/api/v1/sessions", { method: "POST" });
    activeSessionId = session.id;
    $("sessionBadge").textContent = `Session #${session.id}`;
    $("sessionBadge").className = "badge badge-accent";
    $("sessionStatusText").textContent = `Session #${session.id} open. Point camera at products to auto-add.`;
    $("startCameraBtn").disabled = false;
    $("sessionActions").hidden = false;
    renderSessionItems(session);
    showToast(`Session #${session.id} started.`);
  } catch (err) { showToast(err.message); }
};

function renderSessionItems(session) {
  const currency = session.currency || "";
  const count = session.items.length;
  $("cartBadge").textContent = `${count} item${count !== 1 ? "s" : ""}`;
  $("totalAmount").textContent = `${Number(session.total).toFixed(2)} ${currency}`;

  if (!count) {
    $("sessionItems").innerHTML = `<div class="empty-state">
      <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="margin:0 auto 8px;display:block;opacity:.4"><circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"/></svg>
      Cart is empty.<br>Point camera at a product to automatically add it.</div>`;
    return;
  }

  $("sessionItems").innerHTML = session.items.map((item) => `
    <div class="session-item-row">
      <div class="session-item-info">
        <strong>${esc(item.title)}</strong>
        ${item.description ? `<p class="item-description">${esc(item.description)}</p>` : ""}
        <span class="text-muted" style="font-size:.8rem;">${Number(item.unit_price).toFixed(2)} ${esc(currency)} each</span>
      </div>
      <div class="session-item-controls">
        <button class="qty-btn" data-action="dec" data-item="${item.id}">&#x2212;</button>
        <span class="qty-display">${item.quantity}</span>
        <button class="qty-btn" data-action="inc" data-item="${item.id}">+</button>
        <span class="item-subtotal">${Number(item.subtotal).toFixed(2)} ${esc(currency)}</span>
        <button class="btn-icon-danger" data-remove="${item.id}">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
        </button>
      </div>
    </div>`).join("") + `
    <div class="session-total-row">
      <span>Total</span>
      <strong style="color:var(--accent-cyan)">${Number(session.total).toFixed(2)} ${esc(currency)}</strong>
    </div>`;

  $("sessionItems").querySelectorAll(".qty-btn").forEach((btn) => {
    btn.onclick = async () => {
      const itemId = Number(btn.dataset.item);
      const item = session.items.find((i) => i.id === itemId);
      if (!item) return;
      const newQty = btn.dataset.action === "inc" ? item.quantity + 1 : item.quantity - 1;
      if (newQty < 1) return;
      try {
        const updated = await apiRequest(`/api/v1/sessions/${activeSessionId}/items/${itemId}`,
          { method: "PATCH", body: JSON.stringify({ quantity: newQty }) });
        renderSessionItems(updated);
      } catch (err) { showToast(err.message); }
    };
  });

  $("sessionItems").querySelectorAll("[data-remove]").forEach((btn) => {
    btn.onclick = async () => {
      try {
        const updated = await apiRequest(`/api/v1/sessions/${activeSessionId}/items/${btn.dataset.remove}`,
          { method: "DELETE" });
        renderSessionItems(updated); showToast("Item removed.");
      } catch (err) { showToast(err.message); }
    };
  });
}

$("finalizeBtn").onclick = async () => {
  if (!activeSessionId) return;
  try {
    const result = await apiRequest(`/api/v1/sessions/${activeSessionId}/finalize`, { method: "POST" });
    stopCamera(); activeSessionId = null; resetLiveUI();
    showToast(`Session finalized. Total: ${Number(result.session.total).toFixed(2)} ${result.session.currency}`, 5000);
  } catch (err) { showToast(err.message); }
};

$("cancelSessionBtn").onclick = async () => {
  if (!activeSessionId) return;
  if (!confirm("Cancel this shopping session? All items will be discarded.")) return;
  try {
    await apiRequest(`/api/v1/sessions/${activeSessionId}/cancel`, { method: "POST" });
    stopCamera(); activeSessionId = null; resetLiveUI(); showToast("Session cancelled.");
  } catch (err) { showToast(err.message); }
};

// ── Camera Control ────────────────────────────────────────────────────────────
$("startCameraBtn").onclick = startCamera;
$("stopCameraBtn").onclick = stopCamera;
$("captureManualBtn").onclick = () => captureFrame();
$("frameInterval").onchange = () => { if (cameraStream) { stopCaptureLoop(); startCaptureLoop(); } };

async function startCamera() {
  if (!activeSessionId) {
    try {
      const session = await apiRequest("/api/v1/sessions", { method: "POST" });
      activeSessionId = session.id;
      $("sessionBadge").textContent = `Session #${session.id}`;
      $("sessionBadge").className = "badge badge-accent";
      $("sessionStatusText").textContent = `Session #${session.id} open. Point camera at products to auto-add.`;
      $("sessionActions").hidden = false;
      renderSessionItems(session);
    } catch (err) {
      showToast("Could not start session: " + err.message);
      return;
    }
  }
  try {
    cameraStream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: "environment", width: { ideal: 1280 }, height: { ideal: 720 } }, audio: false
    });
    const video = $("liveVideo");
    video.srcObject = cameraStream;
    video.onloadedmetadata = () => { resizeOverlayCanvas(); startCaptureLoop(); };
    $("cameraIdleOverlay").hidden = true;
    $("startCameraBtn").hidden = true; $("stopCameraBtn").hidden = false;
    $("captureManualBtn").disabled = false; $("liveIndicator").hidden = false;
    $("scanRing").hidden = false; showStatusChip("Camera live", 2000);
  } catch (err) { showToast("Camera access denied: " + err.message); }
}

function stopCamera() {
  stopCaptureLoop();
  if (cameraStream) { cameraStream.getTracks().forEach((t) => t.stop()); cameraStream = null; }
  $("liveVideo").srcObject = null;
  $("cameraIdleOverlay").hidden = false;
  $("startCameraBtn").hidden = false; $("stopCameraBtn").hidden = true;
  $("captureManualBtn").disabled = true; $("liveIndicator").hidden = true;
  $("scanRing").hidden = true; $("cameraStatusChip").hidden = true;
  clearOverlay();
}

function resizeOverlayCanvas() {
  const video = $("liveVideo"); const canvas = $("overlayCanvas");
  canvas.width = video.videoWidth; canvas.height = video.videoHeight;
}
window.addEventListener("resize", () => { if (cameraStream) resizeOverlayCanvas(); });

// ── Capture Loop ──────────────────────────────────────────────────────────────
function startCaptureLoop() {
  const interval = parseInt($("frameInterval").value, 10);
  if (interval === 0) return;
  stopCaptureLoop();
  captureTimerId = setInterval(() => captureFrame(), interval);
}
function stopCaptureLoop() {
  if (captureTimerId !== null) { clearInterval(captureTimerId); captureTimerId = null; }
}

async function captureFrame() {
  if (!cameraStream || !activeSessionId || isCapturing) return;
  isCapturing = true; showStatusChip("Analyzing\u2026", 0);
  try {
    const video = $("liveVideo");
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth; canvas.height = video.videoHeight;
    canvas.getContext("2d").drawImage(video, 0, 0);
    const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.85));
    const formData = new FormData();
    formData.append("file", blob, "frame.jpg");
    formData.append("frame_timestamp_ms", String(Date.now()));
    const result = await apiRequest(`/api/v1/live-scan/${activeSessionId}/frame`,
      { method: "POST", body: formData });
    if (result.session) {
      renderSessionItems(result.session);
    }
    drawOverlay(result.detections);
    renderCandidates(result.detections);
    showStatusChip(`${result.detections.length} detected`, 2000);
  } catch (err) { showStatusChip("Error", 2500); console.error("Frame error:", err.message); }
  finally { isCapturing = false; }
}

// ── Canvas Overlay ────────────────────────────────────────────────────────────
function clearOverlay() {
  const canvas = $("overlayCanvas");
  canvas.getContext("2d").clearRect(0, 0, canvas.width, canvas.height);
}

function drawOverlay(detections) {
  const canvas = $("overlayCanvas"); const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  detections.forEach((det) => {
    const box = det.box || det.bbox;
    if (!box || box.length < 4) return;
    const [x1, y1, x2, y2] = box; const w = x2 - x1; const h = y2 - y1;
    const isConfirmed = det.status === "confirmed_in_session";
    const alreadyInCart = det.status === "candidate_already_in_cart" || isConfirmed;
    const isConfident = Boolean(det.product_id && !det.needs_confirmation);
    const isCatalogItem = alreadyInCart || isConfirmed || isConfident;
    const color = isCatalogItem ? "#10b981" : "#94a3b8";
    ctx.strokeStyle = color; ctx.lineWidth = 2.5;
    ctx.shadowColor = color; ctx.shadowBlur = 8;
    ctx.strokeRect(x1, y1, w, h); ctx.shadowBlur = 0;
    const rawLabel = isCatalogItem ? `\u2713 ${det.title || det.suggested_title || "Item"}` : (det.detected_class || "Object");
    const short = rawLabel.length > 24 ? rawLabel.slice(0, 22) + "\u2026" : rawLabel;
    const simPct = (isCatalogItem && det.similarity) ? ` \u00b7 ${(det.similarity * 100).toFixed(0)}%` : "";
    const text = short + simPct;
    ctx.font = "bold 12px 'Plus Jakarta Sans', sans-serif";
    const textW = ctx.measureText(text).width + 10;
    const labelY = y1 > 22 ? y1 - 4 : y1 + h + 16;
    ctx.fillStyle = color; ctx.globalAlpha = 0.85;
    ctx.beginPath(); ctx.roundRect(x1, labelY - 16, textW, 20, 4); ctx.fill();
    ctx.globalAlpha = 1; ctx.fillStyle = "#fff"; ctx.fillText(text, x1 + 5, labelY - 2);
  });
}

// ── Candidate List ────────────────────────────────────────────────────────────
function renderCandidates(detections) {
  const area = $("liveCandidates"); const list = $("candidateList");
  $("candidateCount").textContent = detections.length;
  if (!detections.length) { area.hidden = true; list.innerHTML = ""; return; }
  area.hidden = false;

  // Group by product or tracking ID to count duplicates
  const grouped = [];
  const map = new Map();

  detections.forEach((det) => {
    const key = det.product_id || det.suggested_product_id || (det.title ? `t_${det.title}` : `trk_${det.tracking_id}`);
    if (map.has(key)) {
      const existing = map.get(key);
      existing.count += 1;
      if (det.similarity > existing.similarity) {
        existing.similarity = det.similarity;
      }
    } else {
      const entry = { ...det, count: 1 };
      map.set(key, entry);
      grouped.push(entry);
    }
  });

  list.innerHTML = grouped.map((det) => {
    const isConfident = Boolean(det.product_id && !det.needs_confirmation);
    const isConfirmed = det.status === "confirmed_in_session";
    const alreadyInCart = det.status === "candidate_already_in_cart" || isConfirmed;
    const simPct = det.similarity ? `${(det.similarity * 100).toFixed(1)}%` : "";
    const isCatalogItem = isConfident || isConfirmed || alreadyInCart;
    const title = esc(isCatalogItem ? (det.title || det.suggested_title) : (det.detected_class || "Unidentified object"));

    let badge = `<span class="badge badge-subtle">Unidentified</span>`;
    if (isConfirmed || alreadyInCart) badge = `<span class="badge badge-success">&#x2713; Auto-Added</span>`;
    else if (det.match_method === "barcode") badge = `<span class="badge badge-success">Exact Barcode</span>`;
    else if (isConfident) badge = `<span class="badge badge-accent">Confident Match</span>`;

    const countBadge = det.count > 1 ? `<span class="badge badge-accent" style="margin-left:6px; font-weight:700;">&times;${det.count} detected</span>` : "";

    let action = "";
    if (isConfirmed || alreadyInCart || isConfident) {
      action = `<span class="badge badge-success" style="font-size:.78rem; padding:4px 8px;">&#x2713; In Shopping List (${det.count})</span>`;
    } else {
      action = `<span class="badge badge-subtle" style="font-size:.76rem;">Not in catalog</span>`;
    }

    return `<div class="candidate-card ${isCatalogItem ? "confident" : "uncertain"}">
      <div class="candidate-info">
        <div class="spread" style="margin-bottom:3px;"><strong style="font-size:.88rem;">${title}${countBadge}</strong>${badge}</div>
        ${(isCatalogItem && det.description) ? `<p class="candidate-description">${esc(det.description)}</p>` : ""}
        <div class="candidate-meta">
          <span>Class: <b>${esc(det.detected_class || "?")}</b></span>
          ${simPct ? `<span>Match: <b>${simPct}</b></span>` : ""}
          ${(isCatalogItem && det.price) ? `<span>Price: <b>${Number(det.price).toFixed(2)} ${esc(det.currency || "")}</b>${det.count > 1 ? ` each (Total: ${(Number(det.price) * det.count).toFixed(2)} ${esc(det.currency || "")})` : ""}</span>` : ""}
        </div>
        ${det.barcode_detected ? `<div class="detection-ocr">Barcode: ${esc(det.barcode_detected)}</div>` : ""}
      </div>
      <div>${action}</div>
    </div>`;
  }).join("");
}

// ── Status Chip ───────────────────────────────────────────────────────────────
let chipTimerId = null;
function showStatusChip(text, duration = 2500) {
  const chip = $("cameraStatusChip"); $("cameraStatusText").textContent = text;
  chip.hidden = false; clearTimeout(chipTimerId);
  if (duration > 0) chipTimerId = setTimeout(() => { chip.hidden = true; }, duration);
}

// ═══════════════════════════════════════════════════════════════════════════════
//  PHOTO SCAN (Legacy Cart)
// ═══════════════════════════════════════════════════════════════════════════════

async function initializeActiveCart() {
  if (!activeCartId) {
    try { const cart = await apiRequest("/api/carts", { method: "POST" }); activeCartId = cart.id; }
    catch (err) { showToast(err.message); }
  }
  await loadCartDetails();
}

$("newCart").onclick = async () => {
  try {
    const cart = await apiRequest("/api/carts", { method: "POST" }); activeCartId = cart.id;
    $("detections").innerHTML = `<div class="empty-state">Cart #${activeCartId} active. Scan an image.</div>`;
    $("detectionCount").textContent = "0 items";
    await loadCartDetails(); showToast(`Created new cart #${activeCartId}`);
  } catch (err) { showToast(err.message); }
};

async function loadCartDetails() {
  if (!activeCartId) {
    $("cartView").innerHTML = '<div class="empty-state">Create a cart to get started.</div>';
    const totalEl = $("photoCartTotalAmount");
    if (totalEl) totalEl.textContent = "0.00 \u2014";
    return;
  }
  try {
    const cart = await apiRequest(`/api/carts/${activeCartId}`);
    renderCartView(cart);
  } catch (err) { showToast(err.message); }
}

$("scanForm").onsubmit = async (e) => {
  e.preventDefault();
  if (!activeCartId) await initializeActiveCart();
  const submitBtn = $("scanSubmitBtn"); submitBtn.disabled = true; $("detections").innerHTML = "";
  showBanner("scanMessage", "Running YOLO, Barcode, OCR and CLIP matching\u2026", "");
  try {
    const result = await apiRequest(`/api/carts/${activeCartId}/scan`, { method: "POST", body: new FormData(e.currentTarget) });
    const autoAddedCount = result.detections.filter((d) => d.product_id || d.suggested_product_id).length;
    showBanner(
      "scanMessage",
      `Scan complete: ${result.detections.length} region(s) detected. ${autoAddedCount} product(s) automatically confirmed into cart.`,
      "success"
    );
    $("detectionCount").textContent = `${result.detections.length} regions`;
    renderScanDetections(result.detections, activeCartId);
    if (result.cart) {
      renderCartView(result.cart);
    } else {
      await loadCartDetails();
    }
  } catch (err) { showBanner("scanMessage", err.message, "error"); }
  finally { submitBtn.disabled = false; }
};

function renderCartView(cart) {
  $("cartStatus").textContent = `Cart #${cart.id} (${cart.status})`;
  $("cartItemBadge").textContent = `${cart.items.length} items`;
  const totalEl = $("photoCartTotalAmount");
  if (totalEl) totalEl.textContent = `${Number(cart.total).toFixed(2)} ${esc(cart.currency || "")}`;

  if (!cart.items.length) {
    $("cartView").innerHTML = '<div class="empty-state">Cart is currently empty.</div>';
    return;
  }
  $("cartView").innerHTML = cart.items.map((item) => `
    <div class="cart-item-row">
      <div>
        <strong>${esc(item.title)}</strong>
        ${item.description ? `<p class="item-description">${esc(item.description)}</p>` : ""}
        <div class="text-muted" style="font-size:.82rem;">${item.quantity} \u00d7 ${Number(item.unit_price).toFixed(2)} ${esc(cart.currency)}</div>
      </div>
      <div class="row align-center">
        <strong style="color:var(--accent-emerald);">${Number(item.subtotal).toFixed(2)} ${esc(cart.currency)}</strong>
        <button class="btn btn-danger" style="padding:4px 10px;" data-remove="${item.id}">\u2715</button>
      </div>
    </div>`).join("") + `
    <div class="cart-total-bar"><span>Cart Total</span>
      <span style="color:var(--accent-cyan);">${Number(cart.total).toFixed(2)} ${esc(cart.currency)}</span></div>`;
  $("cartView").querySelectorAll("[data-remove]").forEach((btn) => {
    btn.onclick = async () => {
      try { await apiRequest(`/api/carts/${activeCartId}/items/${btn.dataset.remove}`, { method: "DELETE" }); loadCartDetails(); }
      catch (err) { showToast(err.message); }
    };
  });
}

function renderScanDetections(detections, cartId) {
  const container = $("detections");
  if (!detections.length) { container.innerHTML = '<div class="empty-state">No objects detected.</div>'; return; }
  container.innerHTML = detections.map((det, i) => {
    const isMatched = !!(det.product_id || det.suggested_product_id);
    const simPct = (det.similarity * 100).toFixed(1); const yoloPct = (det.detector_confidence * 100).toFixed(1);
    let methodBadge = `<span class="badge badge-subtle">Visual Match</span>`;
    if (det.match_method === "barcode") methodBadge = `<span class="badge badge-success">Exact Barcode</span>`;
    else if (det.match_method === "ocr_boosted") methodBadge = `<span class="badge badge-accent">Visual + OCR</span>`;
    return `<div class="detection-card ${isMatched ? "confident" : "uncertain"}">
      <div>
        <div class="spread" style="margin-bottom:4px;">
          <h4>${i + 1}. ${esc(det.title || det.suggested_title || "Unidentified")}</h4>
          ${methodBadge}
        </div>
        ${det.description ? `<p class="detection-description">${esc(det.description)}</p>` : ""}
        <div class="detection-meta">
          <span>Class: <b>${esc(det.detected_class)}</b> (${yoloPct}%)</span>
          <span>Match: <b>${simPct}%</b></span>
          ${det.price ? `<span>Price: <b>${Number(det.price).toFixed(2)} ${esc(det.currency)}</b></span>` : ""}
        </div>
        ${det.barcode_detected ? `<div class="detection-ocr">Barcode: ${esc(det.barcode_detected)}</div>` : ""}
        ${det.ocr_text_snippet ? `<div class="detection-ocr">OCR: "${esc(det.ocr_text_snippet)}"</div>` : ""}
      </div>
      <div>${isMatched
        ? `<span class="badge badge-success" style="padding:6px 10px; font-size:.82rem;">&#x2713; Auto-Added to Cart</span>`
        : `<span class="badge badge-subtle">No Database Match</span>`}</div>
    </div>`;
  }).join("");
}

// ═══════════════════════════════════════════════════════════════════════════════
//  CATALOG MANAGEMENT
// ═══════════════════════════════════════════════════════════════════════════════

$("productForm").onsubmit = async (e) => {
  e.preventDefault();
  const btn = e.currentTarget.querySelector("button[type='submit']"); btn.disabled = true;
  showBanner("productMessage", "Extracting frames and generating CLIP embeddings\u2026", "");
  try {
    const product = await apiRequest("/api/products", { method: "POST", body: new FormData(e.currentTarget) });
    showBanner("productMessage", `Registered "${product.title}" (${product.image_count} reference frames embedded).`, "success");
    e.currentTarget.reset(); loadUserProducts();
  } catch (err) { showBanner("productMessage", err.message, "error"); }
  finally { btn.disabled = false; }
};

async function loadUserProducts() {
  if (!token) return;
  try {
    const products = await apiRequest("/api/products");
    const el = $("catalog");
    if (!products.length) { el.innerHTML = `<div class="empty-state" style="grid-column:1/-1;">No products yet. Register one to get started!</div>`; return; }
    el.innerHTML = products.map((p) => `
      <article class="product-card">
        <div>
          <h3>${esc(p.title)}</h3>
          ${p.barcode ? `<div style="margin:4px 0;"><span class="product-barcode">Barcode: ${esc(p.barcode)}</span></div>` : ""}
          <p class="hint" style="margin-top:6px;">${esc(p.description || "No description provided.")}</p>
        </div>
        <div>
          <div class="spread" style="margin-bottom:8px;">
            <strong style="font-size:1.1rem;">${Number(p.price).toFixed(2)} ${esc(p.currency)}</strong>
            <span class="badge ${p.status === "ready" ? "badge-success" : "badge-warning"}">${esc(p.status)} \u00b7 ${p.image_count} frames</span>
          </div>
          <button class="btn btn-danger btn-block" data-del="${p.id}">Delete Product</button>
        </div>
      </article>`).join("");
    el.querySelectorAll("[data-del]").forEach((btn) => {
      btn.onclick = async () => {
        if (confirm("Permanently delete this product and its embeddings?")) {
          try { await apiRequest(`/api/products/${btn.dataset.del}`, { method: "DELETE" }); loadUserProducts(); showToast("Deleted."); }
          catch (err) { showToast(err.message); }
        }
      };
    });
  } catch (err) { showToast(err.message); }
}

$("refreshProducts").onclick = loadUserProducts;

// ── Boot ──────────────────────────────────────────────────────────────────────
updateViewState();
