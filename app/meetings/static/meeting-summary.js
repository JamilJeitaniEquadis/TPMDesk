/* <meeting-summary task-id="…" api-base=""> : "Summarize latest meeting" + summary cards for a task.
   Talks to the Meeting Summary API (same origin by default; cookies carry the session). */
const CSS = `
meeting-summary{display:block;font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif;color:var(--ms-ink)}
meeting-summary *{box-sizing:border-box}
.ms-bar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:0 0 12px}
.ms-btn{font:inherit;font-size:14px;font-weight:600;border:0;border-radius:8px;padding:9px 14px;cursor:pointer;background:var(--ms-btn);color:var(--ms-btn-ink)}
.ms-btn.ghost{background:none;color:var(--ms-soft);border:1px solid var(--ms-rule)}
.ms-btn[disabled]{opacity:.5;cursor:not-allowed}
.ms-btn:focus-visible,.ms-url:focus-visible,.ms-ai input:focus-visible{outline:2px solid var(--ms-accent);outline-offset:2px}
.ms-form{display:flex;flex-wrap:wrap;gap:8px;width:100%}
.ms-url{flex:1 1 280px;min-width:0;font:inherit;font-size:14px;padding:8px 10px;border-radius:8px;border:1px solid var(--ms-rule);background:var(--ms-paper);color:var(--ms-ink)}
.ms-note{font-size:13px;color:var(--ms-soft)}
.ms-msg{border-radius:10px;padding:10px 14px;margin:0 0 12px;font-size:14px}
.ms-msg.ko{background:var(--ms-stop-bg);color:var(--ms-stop);border:1px solid var(--ms-stop)}
.ms-msg.load{background:var(--ms-card);border:1px solid var(--ms-rule);display:flex;gap:10px;align-items:center}
.ms-dot{width:9px;height:9px;border-radius:50%;background:var(--ms-accent);flex:none;animation:ms-p 1s infinite alternate}
@keyframes ms-p{to{opacity:.3}} @media (prefers-reduced-motion:reduce){.ms-dot{animation:none}}
.ms-card{background:var(--ms-card);border:1px solid var(--ms-rule);border-radius:12px;padding:14px 16px;margin:0 0 12px}
.ms-card h3{margin:0;font-size:16px} .ms-card h4{margin:14px 0 4px;font-size:12.5px;letter-spacing:.3px;text-transform:uppercase;color:var(--ms-soft)}
.ms-card p{margin:6px 0 0} .ms-card ul{margin:4px 0 0;padding-left:20px} .ms-card li{margin:2px 0;overflow-wrap:anywhere}
.ms-ai{list-style:none;padding:0!important} .ms-ai li{display:flex;gap:8px;align-items:flex-start;margin:4px 0}
.ms-ai input{margin-top:4px;width:16px;height:16px;flex:none;accent-color:var(--ms-accent)}
.ms-ai .done span{text-decoration:line-through;color:var(--ms-soft)}
.ms-ai em{font-style:normal;font-size:13px;color:var(--ms-soft)}
.ms-meta{display:flex;flex-wrap:wrap;gap:4px 12px;font-size:13px;color:var(--ms-soft);margin-top:2px}
.ms-meta a{color:inherit}
meeting-summary{--ms-ink:#16202B;--ms-soft:#56636F;--ms-rule:#D5DBE1;--ms-card:#F8FAFB;--ms-paper:#fff;--ms-btn:#16202B;--ms-btn-ink:#fff;--ms-accent:#1F9D63;--ms-stop:#A63A2B;--ms-stop-bg:#F4E1DD}
@media (prefers-color-scheme:dark){meeting-summary{--ms-ink:#E7ECF1;--ms-soft:#9AA7B3;--ms-rule:#2E3A46;--ms-card:#18212A;--ms-paper:#11181F;--ms-btn:#E7ECF1;--ms-btn-ink:#11181F;--ms-accent:#58EA9D;--ms-stop:#F09A8A;--ms-stop-bg:#2E1E1B}}`;

const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));

class MeetingSummary extends HTMLElement {
  connectedCallback() {
    if (!document.getElementById('ms-css')) {
      const st = document.createElement('style'); st.id = 'ms-css'; st.textContent = CSS; document.head.appendChild(st);
    }
    this.api = (this.getAttribute('api-base') || '').replace(/\/$/, '');
    this.innerHTML = `<div class="ms-bar"><button class="ms-btn" data-a="open">Summarize latest meeting</button>
      <span class="ms-note" data-r="hint">Reads the transcript Teams produced (transcription must have been on).</span></div>
      <div data-r="form" hidden></div><div data-r="msg" aria-live="polite"></div><div data-r="cards"></div>`;
    this.$ = s => this.querySelector(`[data-r="${s}"]`);
    this.querySelector('[data-a="open"]').onclick = () => this.openForm();
    this.load();
  }
  static get observedAttributes() { return ['task-id']; }
  attributeChangedCallback() { if (this.$) this.load(); }
  get taskId() { return this.getAttribute('task-id'); }

  async call(path, opts = {}) {
    const r = await fetch(this.api + path, {credentials: 'same-origin', ...opts,
      headers: {'Content-Type': 'application/json', ...(opts.headers || {})}});
    let body = null; try { body = await r.json(); } catch (e) {}
    if (!r.ok) {
      const err = new Error(body?.error?.message || body?.detail || `Request failed (${r.status})`);
      err.code = body?.error?.code; err.status = r.status; throw err;
    }
    return body;
  }
  show(kind, html) { this.$('msg').innerHTML = kind ? `<div class="ms-msg ${kind}">${html}</div>` : ''; }
  fail(e) {
    if (e.code === 'reauth') {
      const next = encodeURIComponent(location.pathname + location.search);
      this.show('ko', `${esc(e.message)} <a href="${this.api}/auth/login?next=${next}">Sign in with Microsoft</a>`);
    } else this.show('ko', esc(e.message));
  }

  async load() {
    if (!this.taskId) return;
    try { this.render(await this.call(`/api/tasks/${encodeURIComponent(this.taskId)}/summaries`)); this.show(); }
    catch (e) { if (e.code !== 'task_not_found') this.fail(e); }
  }

  async openForm() {
    const f = this.$('form'); f.hidden = false;
    f.innerHTML = `<form class="ms-form" novalidate>
        <label class="ms-note" for="ms-url-${this.taskId}" style="width:100%">Teams join link</label>
        <input class="ms-url" id="ms-url-${this.taskId}" type="url" required placeholder="https://teams.microsoft.com/l/meetup-join/…" autocomplete="off">
        <button class="ms-btn" type="submit">Summarize</button><button class="ms-btn ghost" type="button" data-a="cancel">Cancel</button>
        <span class="ms-note" data-r="fill" style="width:100%"></span></form>`;
    const form = f.querySelector('form'), url = f.querySelector('input');
    f.querySelector('[data-a="cancel"]').onclick = () => { f.hidden = true; f.innerHTML = ''; };
    form.onsubmit = e => { e.preventDefault(); this.run(url.value.trim()); };
    url.focus();
    try {                                   // auto-fill with the most recent past Teams meeting
      const m = await this.call('/api/meetings/latest');
      if (m?.joinUrl && !url.value) {
        url.value = m.joinUrl;
        this.$('fill').textContent = `Latest meeting: ${m.subject || 'Teams meeting'}${m.start ? ' · ' + new Date(m.start + 'Z').toLocaleString() : ''}`;
      }
    } catch (e) { if (e.code === 'reauth') this.fail(e); }
  }

  async run(joinUrl) {
    if (!/^https:\/\//i.test(joinUrl)) { this.show('ko', 'Paste the meeting’s Teams join link (it starts with https://).'); return; }
    const btns = this.querySelectorAll('.ms-btn'); btns.forEach(b => b.disabled = true);
    const t0 = Date.now();
    const tick = () => this.show('load', `<span class="ms-dot" aria-hidden="true"></span><span>Reading the transcript and writing the summary… ${Math.round((Date.now() - t0) / 1000)} s</span>`);
    tick(); const timer = setInterval(tick, 1000);
    try {
      await this.call('/api/summarize-meeting', {method: 'POST', body: JSON.stringify({taskId: this.taskId, joinUrl})});
      this.$('form').hidden = true; this.$('form').innerHTML = '';
      this.show(); await this.load();
    } catch (e) { this.fail(e); }
    finally { clearInterval(timer); btns.forEach(b => b.disabled = false); }
  }

  render(list) {
    const c = this.$('cards');
    c.innerHTML = list.map(s => `<article class="ms-card" aria-label="Meeting summary: ${esc(s.meetingTitle)}">
      <h3>${esc(s.meetingTitle)}</h3>
      <div class="ms-meta"><span>${s.date ? esc(new Date(s.date.endsWith('Z') ? s.date : s.date + 'Z').toLocaleString()) : ''}</span>
        <span>${s.actionItems.filter(a => a.done).length}/${s.actionItems.length} actions done</span>
        <a href="${this.api}/api/transcripts/${encodeURIComponent(s.rawTranscriptRef)}" target="_blank" rel="noopener">Transcript</a></div>
      <p>${esc(s.overview)}</p>
      ${s.decisions.length ? `<h4>Decisions</h4><ul>${s.decisions.map(d => `<li>${esc(d)}</li>`).join('')}</ul>` : ''}
      ${s.actionItems.length ? `<h4>Action items</h4><ul class="ms-ai">${s.actionItems.map(a => `
        <li class="${a.done ? 'done' : ''}"><input type="checkbox" data-id="${esc(a.id)}" ${a.done ? 'checked' : ''} id="ms-${esc(a.id)}">
          <label for="ms-${esc(a.id)}"><span>${esc(a.task)}</span> <em>${[a.owner, a.dueDate && 'due ' + a.dueDate].filter(Boolean).map(esc).join(' · ')}</em></label></li>`).join('')}</ul>` : ''}
      ${s.openQuestions.length ? `<h4>Open questions</h4><ul>${s.openQuestions.map(q => `<li>${esc(q)}</li>`).join('')}</ul>` : ''}
    </article>`).join('');
    c.querySelectorAll('.ms-ai input').forEach(box => box.onchange = async () => {
      const li = box.closest('li'); li.classList.toggle('done', box.checked);
      try { await this.call(`/api/action-items/${encodeURIComponent(box.dataset.id)}`, {method: 'PATCH', body: JSON.stringify({done: box.checked})}); }
      catch (e) { box.checked = !box.checked; li.classList.toggle('done', box.checked); this.fail(e); }
    });
  }
}
customElements.define('meeting-summary', MeetingSummary);
