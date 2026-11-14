/* SupportPilot dashboard — vanilla JS, talks to the FastAPI backend. */
let token = localStorage.getItem('sp_token') || '';
let me = null;
let signupMode = false;

const api = async (path, method = 'GET', body = null) => {
  const res = await fetch(path, {
    method,
    headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: 'Bearer ' + token } : {}) },
    body: body ? JSON.stringify(body) : null,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || ('Request failed: ' + res.status));
  return data;
};

const showMsg = (text, ok = true, box = 'msg') => {
  const el = document.getElementById(box);
  el.innerHTML = `<div class="msg ${ok ? 'msg-ok' : 'msg-err'}">${text}</div>`;
  setTimeout(() => { el.innerHTML = ''; }, 6000);
};

function toggleSignup() {
  signupMode = !signupMode;
  document.getElementById('signupFields').classList.toggle('hidden', !signupMode);
  document.getElementById('signupBtn').textContent = signupMode ? 'Create workspace' : 'Sign up';
}

async function login() {
  const email = document.getElementById('email').value.trim();
  const password = document.getElementById('password').value;
  try {
    if (signupMode) {
      const name = document.getElementById('name').value.trim();
      const ws = document.getElementById('wsName').value.trim();
      if (!name || !ws) throw new Error('Name and workspace name are required for signup.');
      const d = await api('/auth/signup', 'POST', { name, email, password, workspace_name: ws });
      token = d.access_token; me = d.user;
    } else {
      const d = await api('/auth/login', 'POST', { email, password });
      token = d.access_token; me = d.user;
    }
    localStorage.setItem('sp_token', token);
    enterApp();
  } catch (e) { showMsg(e.message, false, 'authMsg'); }
}

function logout() { token = ''; me = null; localStorage.removeItem('sp_token'); location.reload(); }

async function enterApp() {
  try { me = await api('/auth/me'); } catch (e) { logout(); return; }
  document.getElementById('authView').classList.add('hidden');
  document.getElementById('appView').classList.remove('hidden');
  document.getElementById('whoami').textContent = `${me.name} · ${me.role} · workspace #${me.workspace_id}`;
  loadTickets(); loadKb(); loadBilling(); loadAnalytics();
}

function show(sec, btn) {
  ['inbox', 'new', 'kb', 'billing', 'analytics'].forEach(s => document.getElementById('sec-' + s).classList.toggle('hidden', s !== sec));
  document.querySelectorAll('.sidebar button').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  if (sec === 'billing') loadBilling();
  if (sec === 'analytics') loadAnalytics();
  if (sec === 'kb') loadKb();
}

const badge = (cls, txt) => `<span class="badge ${cls}">${txt}</span>`;

async function loadTickets() {
  const q = new URLSearchParams();
  const st = document.getElementById('fStatus').value, ch = document.getElementById('fChannel').value, s = document.getElementById('fSearch').value;
  if (st) q.set('status', st); if (ch) q.set('channel', ch); if (s) q.set('search', s);
  try {
    const d = await api('/tickets?' + q.toString());
    document.getElementById('ticketList').innerHTML = d.tickets.length ? d.tickets.map(t => `
      <div class="ticket-row" onclick="openTicket(${t.id})">
        <div><b>${t.number}</b> — ${t.subject}<br><span style="color:#6b7280;font-size:13px">${t.customer_name} · ${t.customer_country || ''} · ${t.channel}</span></div>
        <div style="text-align:right">${badge('b-' + t.status, t.status)} ${badge('b-' + t.priority, t.priority)}<br>${t.ai_intent ? badge('b-ai', 'AI: ' + t.ai_intent) : ''}</div>
      </div>`).join('') : '<p style="color:#6b7280">No tickets match.</p>';
  } catch (e) { showMsg(e.message, false); }
}

async function openTicket(id) {
  try {
    const t = await api('/tickets/' + id);
    const kb = await api(`/tickets/${id}/suggest-kb`);
    document.getElementById('ticketDetail').classList.remove('hidden');
    document.getElementById('ticketDetail').innerHTML = `
      <h2>${t.number} — ${t.subject}</h2>
      <p>${badge('b-' + t.status, t.status)} ${badge('b-' + t.priority, t.priority)} ${badge('b-ai', 'AI intent: ' + (t.ai_intent || '—') + ' · ' + (t.ai_sentiment || ''))} &nbsp; SLA: ${t.sla_hours}h &nbsp; Channel: ${t.channel}</p>
      <p style="margin:10px 0"><b>${t.customer_name}</b> (${t.customer_email}, ${t.customer_country})</p>
      <p>${t.body}</p>
      <h3 style="margin-top:16px">AI draft replies</h3>
      ${t.drafts.map(d => `<div style="border:1px solid #e5e7eb;border-radius:8px;padding:12px;margin:8px 0"><p>${d.body}</p>
        <p>${badge('b-ai', d.status)} ${d.status === 'drafted' ? `<button class="btn btn-primary btn-sm" onclick="draftAction(${d.id},'approved')">Approve</button> <button class="btn btn-ghost btn-sm" onclick="draftAction(${d.id},'sent')">Send</button>` : ''}</p></div>`).join('') || '<p>No drafts yet.</p>'}
      <button class="btn btn-ghost btn-sm" onclick="genDraft(${t.id})">Generate new AI draft</button>
      <h3 style="margin-top:16px">Suggested KB articles</h3>
      <p>${kb.suggestions.map(s => `📄 ${s.title} <span style="color:#6b7280">(${s.score})</span>`).join('<br>') || 'None found.'}</p>
      <h3 style="margin-top:16px">Replies</h3>
      ${t.replies.map(r => `<p style="border-left:3px solid #2563eb;padding-left:10px;margin:8px 0"><b>${r.author_name}:</b> ${r.body}</p>`).join('') || '<p style="color:#6b7280">No replies yet.</p>'}
      <textarea id="replyBody" rows="3" placeholder="Write a reply..."></textarea>
      <div style="display:flex;gap:8px;margin-top:10px;flex-wrap:wrap">
        <button class="btn btn-primary btn-sm" onclick="sendReply(${t.id})">Send reply</button>
        <button class="btn btn-ghost btn-sm" onclick="resolveTicket(${t.id})">Resolve ticket</button>
        <button class="btn btn-ghost btn-sm" onclick="acceptAi(${t.id})">Accept AI triage</button>
      </div>`;
    document.getElementById('ticketDetail').scrollIntoView();
  } catch (e) { showMsg(e.message, false); }
}

async function draftAction(id, status) { try { await api('/tickets/drafts/' + id, 'PATCH', { status }); showMsg('Draft ' + status + '.'); loadTickets(); } catch (e) { showMsg(e.message, false); } }
async function genDraft(id) { try { await api(`/tickets/${id}/drafts`, 'POST', {}); showMsg('New AI draft generated.'); openTicket(id); } catch (e) { showMsg(e.message, false); } }
async function sendReply(id) { const body = document.getElementById('replyBody').value.trim(); if (!body) return; try { await api(`/tickets/${id}/replies`, 'POST', { body }); showMsg('Reply sent.'); openTicket(id); loadTickets(); } catch (e) { showMsg(e.message, false); } }
async function resolveTicket(id) { try { await api(`/tickets/${id}/resolve`, 'POST', { csat_rating: 5 }); showMsg('Ticket resolved (CSAT 5 recorded for demo).'); openTicket(id); loadTickets(); } catch (e) { showMsg(e.message, false); } }
async function acceptAi(id) { try { await api('/tickets/' + id, 'PATCH', { ai_accepted: true }); showMsg('AI triage accepted.'); } catch (e) { showMsg(e.message, false); } }

async function createTicket() {
  const payload = { subject: document.getElementById('ntSubject').value.trim(), body: document.getElementById('ntBody').value.trim(), customer_name: document.getElementById('ntName').value.trim() || 'Customer', customer_email: document.getElementById('ntEmail').value.trim(), customer_country: document.getElementById('ntCountry').value.trim(), channel: document.getElementById('ntChannel').value };
  if (!payload.subject || !payload.body) { showMsg('Subject and message are required.', false); return; }
  try { const t = await api('/tickets', 'POST', payload); showMsg(`Ticket ${t.number} created — AI says: ${t.ai_intent} (${t.ai_sentiment}), priority ${t.priority}.`); show('inbox', document.querySelector('.sidebar button')); loadTickets(); } catch (e) { showMsg(e.message, false); }
}

async function loadKb() {
  try { const d = await api('/kb'); document.getElementById('kbList').innerHTML = d.articles.map(a => `<p><b>${a.title}</b> <span style="color:#6b7280">(${a.category})</span><br><span style="font-size:14px">${a.body}</span></p>`).join('') || 'No articles yet.'; } catch (e) {}
}
async function createKb() {
  try { await api('/kb', 'POST', { title: document.getElementById('kbTitle').value, body: document.getElementById('kbBody').value, category: document.getElementById('kbCat').value }); showMsg('Article published.'); loadKb(); } catch (e) { showMsg(e.message, false); }
}

async function loadBilling() {
  try {
    const b = await api('/billing');
    document.getElementById('billingBox').innerHTML = `
      <p>Current plan: <b>${b.plan_name}</b> ($${b.price_usd}/mo) · SLA target: ${b.sla_hours}h</p>
      <p>Tickets this month: <b>${b.tickets_used_this_month}</b> / ${b.tickets_per_month === null ? 'unlimited' : b.tickets_per_month}</p>
      <p>Agents: <b>${b.agents}</b> / ${b.max_agents === null ? 'unlimited' : b.max_agents}</p>
      <h3 style="margin-top:14px">Payment history (mock)</h3>
      ${b.payments.map(p => `<p>${p.reference} — ${p.plan} — $${p.amount_usd} — ${p.status}</p>`).join('') || '<p>No payments yet.</p>'}`;
  } catch (e) {}
}

async function checkout(plan) {
  try { const d = await api('/billing/checkout', 'POST', { plan }); showMsg(d.message + ' Reference: ' + d.reference); loadBilling(); } catch (e) { showMsg(e.message, false); }
}

async function loadAnalytics() {
  try {
    const a = await api('/analytics/summary');
    const bar = (label, val, max) => `<div class="bar-row"><span class="lbl">${label}</span><div class="bar" style="width:${max ? Math.round(val / max * 220) : 0}px"></div><b>${val}</b></div>`;
    const maxS = Math.max(1, ...Object.values(a.by_status));
    document.getElementById('analyticsBox').innerHTML = `
      <div class="cards">
        <div class="card"><div class="num">${a.total_tickets}</div><div class="lbl">Total tickets</div></div>
        <div class="card"><div class="num">${(a.resolution_rate * 100).toFixed(0)}%</div><div class="lbl">Resolution rate</div></div>
        <div class="card"><div class="num">${a.avg_first_response_hours === null ? '—' : a.avg_first_response_hours + 'h'}</div><div class="lbl">Avg first response</div></div>
        <div class="card"><div class="num">${a.avg_csat === null ? '—' : a.avg_csat + ' / 5'}</div><div class="lbl">Avg CSAT (${a.csat_responses} ratings)</div></div>
      </div>
      <h3>By status</h3>${Object.entries(a.by_status).map(([k, v]) => bar(k, v, maxS)).join('')}
      <h3 style="margin-top:14px">By intent</h3>${Object.entries(a.by_intent).map(([k, v]) => bar(k, v, Math.max(1, ...Object.values(a.by_intent)))).join('')}
      <h3 style="margin-top:14px">By channel</h3>${Object.entries(a.by_channel).map(([k, v]) => bar(k, v, Math.max(1, ...Object.values(a.by_channel)))).join('')}`;
  } catch (e) {}
}

if (token) enterApp();
if (location.hash === '#signup') { signupMode = true; document.getElementById('signupFields').classList.remove('hidden'); document.getElementById('signupBtn').textContent = 'Create workspace'; }
