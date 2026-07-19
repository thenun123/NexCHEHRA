// ══════════════════════════════════════════════════════════
// NEXCHEHRA — AI Influencer Video Generator
// Dashboard Application Logic
// ══════════════════════════════════════════════════════════

const BASE_URL = window.location.origin;

// ── State ────────────────────────────────────────────────────
let state = {
  step:         0,
  sessionId:    null,
  phase0Data:   {},
  phase1Data:   {},
  selectedInfluencer: null,
  selectedShot: 'auto',
  eventSource:  null,
  // Product state
  hasProduct:         false,
  productImagePath:   null,
  productImageUrl:    null,
  productName:        '',
  productFeatures:    '',
  productPlacement:   'in_hand',
  // Custom reference
  customRefPath:      null,
  customRefUrl:       null,
};

// ── Influencer Data ───────────────────────────────────────────
const influencers = [
  {
    id: 'aira',
    name: 'Aira',
    category: 'Fashion & Lifestyle',
    image: '/static/images/aira.jpg',
    refImage: 'static/images/aira.jpg',
    gender: 'female',
    bodyType: 'normal',
    tags: ['Fashion', 'Traditional', 'Elegant'],
    prompt: 'Fashion influencer in red and gold traditional outfit, warm elegant lighting, half body shot'
  },
  {
    id: 'marcus',
    name: 'Marcus',
    category: 'Fitness & Lifestyle',
    image: '/static/images/franklin.png',
    refImage: 'static/images/franklin.png',
    gender: 'male',
    bodyType: 'chubby',
    tags: ['Chubby', 'Bold', 'Confident'],
    prompt: 'Chubby stocky man in a casual outfit, confident pose, warm lighting, half body shot, same chubby body type'
  },
  {
    id: 'franklin',
    name: 'Franklin',
    category: 'Street & Casual',
    image: '/static/images/marcus.png',
    refImage: 'static/images/marcus.png',
    gender: 'male',
    bodyType: 'normal',
    tags: ['Street', 'Cap', 'Casual'],
    prompt: 'Casual streetwear influencer in white tee and cap, relaxed vibe, natural lighting, half body shot'
  },
  {
    id: 'liberty',
    name: 'Liberty',
    category: 'Patriotic & Fashion',
    image: '/static/images/liberty.png',
    refImage: 'static/images/liberty.png',
    gender: 'female',
    bodyType: 'normal',
    tags: ['Patriotic', 'Trendy', 'Bold'],
    prompt: 'Patriotic fashion influencer with American flag accessories, denim vest, energetic and bold, headshot'
  },
  {
    id: 'custom',
    name: 'Custom',
    category: 'Upload Your Own',
    image: null,
    refImage: null,
    gender: 'unknown',
    bodyType: 'normal',
    tags: ['Custom'],
    prompt: ''
  }
];

// ── Init Gallery ─────────────────────────────────────────────
function initGallery() {
  const gallery = document.getElementById('influencerGallery');
  if (!gallery) return;

  influencers.forEach(inf => {
    const card = document.createElement('div');
    card.className = 'influencer-card';
    card.dataset.id = inf.id;

    if (inf.id === 'custom') {
      card.innerHTML = `
        <div class="custom-card-inner">
          <span>✨</span>
          <span>Upload Your Own</span>
          <span>Click to upload a reference photo</span>
        </div>
        <input type="file" id="customRefInput" accept="image/jpeg,image/png,image/webp"
               style="display:none" onchange="handleCustomRefUpload(event)">`;
    } else {
      card.innerHTML = `
        <img src="${inf.image}" alt="${inf.name}" class="influencer-img" onerror="this.style.display='none'">
        <div class="influencer-info">
          <div class="influencer-name">${inf.name}</div>
          <div class="influencer-cat">${inf.category}</div>
          <div class="influencer-tags">${inf.tags.map(t => `<span class="tag">${t}</span>`).join('')}</div>
        </div>`;
    }
    card.addEventListener('click', () => selectInfluencer(inf.id));
    gallery.appendChild(card);
  });
}

function selectInfluencer(id) {
  if (id === 'custom') {
    document.getElementById('customRefInput').click();
    return;
  }
  document.querySelectorAll('.influencer-card').forEach(c => c.classList.remove('selected'));
  document.querySelector(`.influencer-card[data-id="${id}"]`).classList.add('selected');
  state.selectedInfluencer = influencers.find(i => i.id === id);
  state.customRefPath = null;
  document.getElementById('description').value = state.selectedInfluencer.prompt;
  addLog('info', `👤 Selected: ${state.selectedInfluencer.name}`);
}

// ── Custom Reference Upload ──────────────────────────────────
async function handleCustomRefUpload(event) {
  const file = event.target.files[0];
  if (!file) return;

  if (file.size > 10 * 1024 * 1024) {
    addLog('error', '❌ Image too large (max 10MB)');
    return;
  }

  addLog('processing', '📤 Uploading custom reference image...');

  const formData = new FormData();
  formData.append('reference_image', file);

  try {
    const res = await fetch(`${BASE_URL}/api/upload_reference`, {
      method: 'POST',
      body: formData,
    });
    const data = await res.json();
    if (data.status !== 'success') throw new Error(data.message);

    document.querySelectorAll('.influencer-card').forEach(c => c.classList.remove('selected'));
    const customCard = document.querySelector('.influencer-card[data-id="custom"]');
    customCard.classList.add('selected');

    customCard.innerHTML = `
      <img src="${data.ref_url}" alt="Custom" class="influencer-img">
      <div class="influencer-info">
        <div class="influencer-name">Custom</div>
        <div class="influencer-cat">${file.name}</div>
        <div class="influencer-tags"><span class="tag">Uploaded</span></div>
      </div>
      <input type="file" id="customRefInput" accept="image/jpeg,image/png,image/webp"
             style="display:none" onchange="handleCustomRefUpload(event)">`;
    customCard.addEventListener('click', () => selectInfluencer('custom'));

    const customInf = influencers.find(i => i.id === 'custom');
    state.selectedInfluencer = customInf;
    state.customRefPath = data.ref_path;
    state.customRefUrl = data.ref_url;

    addLog('success', `✓ Custom reference uploaded: ${file.name}`);
    addLog('info', 'ℹ️ Now describe the scene/outfit in the text box below');
  } catch(e) {
    addLog('error', `❌ Upload failed: ${e.message}`);
  }
}

// ── Shot Type ─────────────────────────────────────────────────
function selectShot(el) {
  document.querySelectorAll('.shot-option').forEach(o => o.classList.remove('selected'));
  el.classList.add('selected');
  state.selectedShot = el.dataset.type;
  addLog('info', `📐 Shot type: ${state.selectedShot.toUpperCase()}`);
}

// ── SSE Logger ────────────────────────────────────────────────
function connectLogs(sessionId) {
  if (state.eventSource) state.eventSource.close();
  state.eventSource = new EventSource(`${BASE_URL}/api/logs/${sessionId}`);
  state.eventSource.onmessage = function(e) {
    const log = JSON.parse(e.data);
    if (log.type === 'heartbeat') return;
    if (log.type !== 'complete') addLog(log.type, log.message);
  };
  state.eventSource.onerror = function() {
    state.eventSource.close();
  };
}

// ── Phase 0: LLM ─────────────────────────────────────────────
async function runPhase0() {
  const description = document.getElementById('description').value.trim();
  const script      = document.getElementById('script').value.trim();
  const scriptLanguage = document.getElementById('scriptLanguage').value;  // NEW
  const aspectRatio = document.getElementById('aspectRatio').value;  // NEW

  if (!description) { addLog('info', '⚠️ Please describe the scene first'); return; }

  // Validate product
  if (state.hasProduct) {
    if (!state.productImagePath) { addLog('info', '⚠️ Please upload a product image first'); return; }
    state.productName = document.getElementById('productName').value.trim();
    state.productFeatures = document.getElementById('productFeatures').value.trim();
    if (!state.productName) { addLog('info', '⚠️ Please enter a product name'); return; }
  }

  state.sessionId = 'session_' + Date.now();
  setPhaseStatus(0, 'active');
  setSpinner('spinner0', true);
  setBtn('btnAnalyze', true);
  connectLogs(state.sessionId);
  addLog('info', '🚀 Starting Phase 0 — NexBrain™ AI...');
  if (state.hasProduct) {
    addLog('info', `🛍️ Product mode: ${state.productName} (${state.productPlacement})`);
  }

  try {
    const inf = state.selectedInfluencer || {};
    const gender = inf.gender || 'unknown';
    const bodyType = inf.bodyType || 'normal';
    const influencerName = inf.name || 'Custom';

    const res = await fetch(`${BASE_URL}/api/phase0`, {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({
        session_id:  state.sessionId,
        description,
        script:      script || null,
        shot_type:   state.selectedShot,
        script_language:   scriptLanguage,  // NEW
        aspect_ratio:      aspectRatio,     // NEW (store for Phase 2)
        gender:            gender,
        body_type:         bodyType,
        influencer_name:   influencerName,
        has_product:       state.hasProduct,
        product_name:      state.hasProduct ? state.productName : null,
        product_features:  state.hasProduct ? state.productFeatures : null,
        product_placement: state.hasProduct ? state.productPlacement : null,
      })
    });
    const data = await res.json();
    if (data.status !== 'success') throw new Error(data.message);

    state.phase0Data = data;
    state.aspectRatio = aspectRatio;  // NEW: Store for Phase 2
    setPhaseStatus(0, 'done');
    setSpinner('spinner0', false);
    setBtn('btnAnalyze', false);
    showGate1(data);

  } catch(e) {
    addLog('error', `❌ Phase 0 failed: ${e.message}`);
    setPhaseStatus(0, 'pending');
    setSpinner('spinner0', false);
    setBtn('btnAnalyze', false);
  }
}

function showGate1(data) {
  document.getElementById('gate1FluxPrompt').value   = data.flux_prompt;
  document.getElementById('gate1MotionPrompt').value = data.motion_prompt;
  document.getElementById('gate1Script').value       = data.video_script;
  document.getElementById('gate1ShotTypeVal').textContent = data.shot_type.replace('_',' ').toUpperCase();

  const badge = document.getElementById('gate1ProductBadge');
  if (state.hasProduct && state.productImageUrl) {
    badge.style.display = 'inline-flex';
    document.getElementById('gate1ProductThumb').src = state.productImageUrl;
    document.getElementById('gate1ProductName').textContent = state.productName;
    document.getElementById('gate1ProductPlacement').textContent = state.productPlacement.replace('_',' ');
  } else {
    badge.style.display = 'none';
  }

  updateCostPreview('gate1');
  showSection('sectionGate1');
  setStep(1);
}

// ── Phase 1: Image Generation ────────────────────────────────
async function runPhase1() {
  const fluxPrompt   = document.getElementById('gate1FluxPrompt').value.trim();
  const motionPrompt = document.getElementById('gate1MotionPrompt').value.trim();
  const script       = document.getElementById('gate1Script').value.trim();
  const shotType     = state.phase0Data.shot_type || 'half_body';

  state.phase0Data.flux_prompt   = fluxPrompt;
  state.phase0Data.motion_prompt = motionPrompt;
  state.phase0Data.video_script  = script;

  setPhaseStatus(1, 'active');
  setSpinner('spinner1', true);
  setBtn('btnGenPortrait', true);
  addLog('info', '🎨 Starting Phase 1 — NexVision™ Engine...');

  try {
    const inf = state.selectedInfluencer || {};
    const refImagePath = state.customRefPath || (inf.refImage || null);
    const gender = inf.gender || 'unknown';
    const bodyType = inf.bodyType || 'normal';

    const res = await fetch(`${BASE_URL}/api/phase1`, {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({
        session_id:  state.sessionId,
        flux_prompt: fluxPrompt,
        shot_type:   shotType,
        aspect_ratio: state.aspectRatio || '9:16',  // Pass to Flux for correct image dimensions
        reference_image_path: refImagePath,
        gender:               gender,
        body_type:            bodyType,
        product_image_path: state.hasProduct ? state.productImagePath : null,
        product_placement:  state.hasProduct ? state.productPlacement : null,
      })
    });
    const data = await res.json();
    if (data.status !== 'success') throw new Error(data.message);

    state.phase1Data = data;
    setPhaseStatus(1, 'done');
    setSpinner('spinner1', false);
    setBtn('btnGenPortrait', false);
    showGate2(data);

  } catch(e) {
    addLog('error', `❌ Phase 1 failed: ${e.message}`);
    setPhaseStatus(1, 'pending');
    setSpinner('spinner1', false);
    setBtn('btnGenPortrait', false);
  }
}

function showGate2(data) {
  document.getElementById('gate2Portrait').src         = data.portrait_path;
  document.getElementById('gate2Script').value         = state.phase0Data.video_script;
  document.getElementById('gate2MotionPrompt').value   = state.phase0Data.motion_prompt;

  updateCostPreview('gate2');
  showSection('sectionGate2');
  setStep(2);
  addLog('success', '✓ Portrait ready — review before generating video');
}

// ── Phase 2: Video Generation ────────────────────────────────
async function runPhase2() {
  const script       = document.getElementById('gate2Script').value.trim();
  const motionPrompt = document.getElementById('gate2MotionPrompt').value.trim();

  setPhaseStatus(2, 'active');
  setSpinner('spinner2', true);
  setBtn('btnGenVideo', true);
  addLog('info', '🎬 Starting Phase 2 — Kling O3 Pro...');

  try {
    const res = await fetch(`${BASE_URL}/api/phase2`, {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({
        session_id:   state.sessionId,
        portrait_local_path: state.phase1Data.portrait_local_path,
        portrait_url: state.phase1Data.portrait_url,
        motion_prompt: motionPrompt,
        video_script: script,
        duration: 15,  // Kling O3 Pro max 15 seconds
        aspect_ratio: state.aspectRatio || '9:16',  // Use stored aspect ratio
      })
    });
    const data = await res.json();
    if (data.status !== 'success') throw new Error(data.message);

    setPhaseStatus(2, 'done');
    setSpinner('spinner2', false);
    setBtn('btnGenVideo', false);
    showResult(data);

  } catch(e) {
    addLog('error', `❌ Phase 2 failed: ${e.message}`);
    setPhaseStatus(2, 'pending');
    setSpinner('spinner2', false);
    setBtn('btnGenVideo', false);
  }
}

function showResult(data) {
  const grid = document.getElementById('resultGrid');
  const cost = data.final_cost;
  grid.innerHTML = `
    <div class="result-card">
      <h3>📸 Generated Portrait</h3>
      <img src="${state.phase1Data.portrait_path}" alt="Portrait">
      <a href="${state.phase1Data.portrait_path}" download class="result-download">⬇️ Download Portrait</a>
    </div>
    <div class="result-card">
      <h3>🎬 Generated Video</h3>
      <video src="${data.video_path}" controls></video>
      <a href="${data.video_path}" download class="result-download">⬇️ Download Video</a>
      <div style="margin-top:8px; font-size:.82rem; color: var(--text-muted);">Duration: ${data.duration}s · Cost: $${cost}</div>
    </div>`;
  showSection('sectionResult');
  setStep(3);
  addLog('success', `🎉 Done! Cost: $${cost}`);
}

// ── Live Cost Preview ─────────────────────────────────────────
function updateCostPreview(gate) {
  const scriptEl    = document.getElementById(`${gate}Script`);
  const wordsEl     = document.getElementById(`${gate}WordCount`);
  const durationEl  = document.getElementById(`${gate}Duration`);
  const costEl      = document.getElementById(`${gate}Cost`);

  const voiceLangEl = document.getElementById('gate2VoiceLang');
  const voiceLang   = (gate === 'gate2' && voiceLangEl) ? voiceLangEl.value : null;

  const script = scriptEl.value.trim();
  const words = script.split(/\s+/).filter(Boolean).length;
  const duration = 15;

  let tier = 'audio_off';
  if (words > 0) {
    if (gate === 'gate2' && voiceLang === '') {
      tier = 'audio_off';
    } else {
      tier = 'audio_on';
    }
  }

  const rates = {
    'audio_off':     0.112,
    'audio_on':      0.168,
    'voice_control': 0.196
  };

  const rate = rates[tier];
  const cost = (duration * rate).toFixed(2);

  wordsEl.textContent    = words;
  durationEl.textContent = duration;
  costEl.textContent     = `$${cost}`;

  const detailsEl = document.getElementById(`${gate}CostDetails`);
  if (detailsEl) {
    const labels = {
      'audio_off': 'Audio OFF · NexMotion™',
      'audio_on':  'Audio ON · NexMotion™',
    };
    detailsEl.textContent = labels[tier];
  }

  wordsEl.style.color = words > 52 ? 'var(--accent-red)' : 'var(--text-muted)';
}

// ── Navigation ────────────────────────────────────────────────
function goBack(toStep) {
  const sections = ['sectionInput','sectionGate1','sectionGate2','sectionResult'];
  showSection(sections[toStep]);
  setStep(toStep);
}

function resetAll() {
  state = {
    step:0, sessionId:null, phase0Data:{}, phase1Data:{},
    selectedInfluencer:null, selectedShot:'auto', eventSource:null,
    hasProduct:false, productImagePath:null, productImageUrl:null,
    productName:'', productFeatures:'', productPlacement:'in_hand',
    customRefPath:null, customRefUrl:null
  };

  document.querySelectorAll('.influencer-card').forEach(c => c.classList.remove('selected'));
  document.querySelectorAll('.shot-option').forEach(o => o.classList.remove('selected'));
  document.querySelector('.shot-option[data-type="auto"]').classList.add('selected');
  document.getElementById('description').value = '';
  document.getElementById('script').value      = '';
  document.getElementById('logOutput').innerHTML = '<div class="log-item info"><span>ℹ️</span><span>Ready.</span></div>';

  // Reset product UI
  document.getElementById('productToggle').checked = false;
  document.getElementById('productSection').classList.remove('open');
  document.getElementById('productName').value = '';
  document.getElementById('productFeatures').value = '';
  document.getElementById('productPreview').classList.remove('visible');
  document.getElementById('productUploadArea').style.display = 'block';
  document.querySelectorAll('.placement-option').forEach(o => o.classList.remove('selected'));
  document.querySelector('.placement-option[data-placement="in_hand"]').classList.add('selected');

  // Reset custom card
  const customCard = document.querySelector('.influencer-card[data-id="custom"]');
  if (customCard) {
    customCard.innerHTML = `
      <div class="custom-card-inner">
        <span>✨</span>
        <span>Upload Your Own</span>
        <span>Click to upload a reference photo</span>
      </div>
      <input type="file" id="customRefInput" accept="image/jpeg,image/png,image/webp"
             style="display:none" onchange="handleCustomRefUpload(event)">`;
  }

  [0,1,2].forEach(i => setPhaseStatus(i, 'pending'));
  showSection('sectionInput');
  setStep(0);
}

// ── UI Helpers ────────────────────────────────────────────────
function showSection(id) {
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
  document.getElementById(id).classList.add('active');
}

function setStep(n) {
  for(let i=0; i<=3; i++) {
    const circle = document.getElementById(`step${i}`);
    circle.classList.remove('active','done');
    if (i < n)       circle.classList.add('done');
    else if (i === n) circle.classList.add('active');
  }
  for(let i=0; i<=2; i++) {
    const conn = document.getElementById(`conn${i}`);
    conn.classList.toggle('done', i < n);
  }
}

function setPhaseStatus(phase, status) {
  const card  = document.getElementById(`phaseCard${phase}`);
  const label = document.getElementById(`phaseStatus${phase}`);
  if (!card || !label) return;

  card.style.borderColor = {
    active: 'var(--accent-amber)',
    done:   'var(--accent-green)',
    pending:'var(--border-subtle)'
  }[status];

  card.style.boxShadow = status === 'active' ? '0 0 20px rgba(255, 170, 0, 0.2)' :
                          status === 'done'   ? '0 0 20px rgba(0, 255, 136, 0.15)' : 'none';

  const text = {active:'⏳ Running...', done:'✓ Done', pending:'Waiting'}[status];
  const color = {active:'var(--accent-amber)', done:'var(--accent-green)', pending:'var(--text-muted)'}[status];
  label.textContent = text;
  label.style.color = color;
}

function setSpinner(id, show) {
  document.getElementById(id).classList.toggle('active', show);
}

function setBtn(id, disabled) {
  document.getElementById(id).disabled = disabled;
}

function addLog(type, message) {
  const out  = document.getElementById('logOutput');
  const item = document.createElement('div');
  item.className = `log-item ${type}`;
  const icons = {success:'✓', processing:'⏳', error:'❌', info:'ℹ️'};
  item.innerHTML = `<span>${icons[type]||'ℹ️'}</span><span>${message}</span>`;
  out.appendChild(item);
  out.scrollTop = out.scrollHeight;
}

// ── Product Upload / Toggle ──────────────────────────────────
function toggleProduct() {
  state.hasProduct = document.getElementById('productToggle').checked;
  const section = document.getElementById('productSection');
  if (state.hasProduct) {
    section.classList.add('open');
    addLog('info', '🛍️ Product placement enabled');
  } else {
    section.classList.remove('open');
    addLog('info', 'ℹ️ Product placement disabled');
  }
}

function selectPlacement(el) {
  document.querySelectorAll('.placement-option').forEach(o => o.classList.remove('selected'));
  el.classList.add('selected');
  state.productPlacement = el.dataset.placement;
  addLog('info', `📍 Placement: ${state.productPlacement.replace('_',' ')}`);
}

async function handleProductUpload(event) {
  const file = event.target.files[0];
  if (!file) return;

  if (file.size > 5 * 1024 * 1024) {
    addLog('error', '❌ Product image too large (max 5MB)');
    return;
  }

  addLog('processing', '📤 Uploading product image...');

  const formData = new FormData();
  formData.append('product_image', file);

  try {
    const res = await fetch(`${BASE_URL}/api/upload_product`, {
      method: 'POST',
      body: formData,
    });
    const data = await res.json();
    if (data.status !== 'success') throw new Error(data.message);

    state.productImagePath = data.product_path;
    state.productImageUrl  = data.product_url;

    document.getElementById('productPreviewImg').src = data.product_url;
    document.getElementById('productFileName').textContent = file.name;
    document.getElementById('productFileSize').textContent = (file.size / 1024).toFixed(0) + ' KB';
    document.getElementById('productPreview').classList.add('visible');
    document.getElementById('productUploadArea').style.display = 'none';

    addLog('success', `✓ Product image uploaded: ${file.name}`);
  } catch(e) {
    addLog('error', `❌ Upload failed: ${e.message}`);
  }
}

function removeProduct() {
  state.productImagePath = null;
  state.productImageUrl  = null;
  document.getElementById('productPreview').classList.remove('visible');
  document.getElementById('productUploadArea').style.display = 'block';
  document.getElementById('productFileInput').value = '';
  addLog('info', 'ℹ️ Product image removed');
}

// ── Toast Notification ───────────────────────────────────────
function showToast(message, type = 'info', duration = 4000) {
  const existing = document.querySelector('.toast');
  if (existing) existing.remove();

  const toast = document.createElement('div');
  toast.className = `toast show ${type}`;
  const icons = { success: '✓', error: '✕', info: 'ℹ' };
  toast.innerHTML = `<span>${icons[type] || 'ℹ'}</span><span>${message}</span>`;
  document.body.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(100%)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

// ── Init on Load ─────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  initGallery();
});


// ── Word Count Tracker (Main Input) ──────────────────────────
function updateWordCount() {
  const scriptEl = document.getElementById('script');
  const countEl = document.getElementById('wordCount');
  const statusEl = document.getElementById('wordCountStatus');
  
  if (!scriptEl || !countEl || !statusEl) return;
  
  const script = scriptEl.value.trim();
  const words = script.split(/\s+/).filter(Boolean).length;
  
  countEl.textContent = words;
  
  if (words < 44) {
    statusEl.textContent = '(too short - add more)';
    statusEl.style.color = 'var(--accent-amber)';
  } else if (words > 52) {
    statusEl.textContent = '(too long - will be trimmed)';
    statusEl.style.color = 'var(--accent-red)';
  } else {
    statusEl.textContent = '(perfect!)';
    statusEl.style.color = 'var(--accent-green)';
  }
}
