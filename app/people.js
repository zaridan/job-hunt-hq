/* People tab: the referral contacts pipeline (contacts.json) as a kanban.
   Rules live in people-core.js. Uses these globals from index.html:
   state, today, serverMode, dataset, esc, toast, openExternal, render, setView, setDataset,
   and window.syncReady (resolves once server detection has finished). */
var People = (function () {
  var CACHE_KEY = 'jobhunt_contacts_v1';
  var COLS = PeopleCore.STAGES.concat(['Closed']);
  var contacts = [];
  var cfg = PeopleCore.withDefaults({});
  var companyFilter = '';
  var closedOpen = false;
  var editingId = null;          // set while the form is editing an existing person
  var layout = 'board';          // 'board' | 'table', set by index.html's Board/Table switch
  var tableSort = 'likelihood';
  var tableDir = -1;
  var TABLE_COLS = [['name', 'Name'], ['company', 'Company'], ['title', 'Title'], ['relation', 'Relation'],
                    ['stage', 'Stage'], ['likelihood', 'Likelihood'], ['dateFound', 'Found'],
                    ['dateRequested', 'Requested'], ['dateConnected', 'Connected'], ['dateAsked', 'Asked']];
  var ADD_FIELDS = ['pa_name', 'pa_company', 'pa_url', 'pa_title', 'pa_relation', 'pa_notes', 'pa_like'];
  var writing = false;
  var pending = false;
  var revision = '';   // last-known X-Contacts-Revision; sent back as X-Base-Revision
  var loaded = false;  // true once a server-mode load has succeeded at least once
  var lastSync = '';   // shown in the footer, e.g. "Saved to contacts.json · 15:52"
  var saveFailed = false;

  function clock() { return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }); }

  // The header chip and footer describe contacts.json while People is shown (index.html's stamp()
  // and updateFileStatus() describe data.json and take over again when Jobs is shown).
  function paintStatus() {
    if (dataset !== 'people') return;
    var chip = document.getElementById('filestat');
    if (!serverMode) { chip.textContent = 'Browser only · People needs the tracker server'; chip.className = 'filechip warn'; }
    else if (!loaded) { chip.textContent = '⚠ contacts.json · not loaded'; chip.className = 'filechip warn'; }
    else if (saveFailed) { chip.textContent = '⚠ contacts.json · last save failed'; chip.className = 'filechip warn'; }
    else { chip.textContent = '🖥 contacts.json · server-synced'; chip.className = 'filechip ok'; }
    var n = contacts.length;
    document.getElementById('foot').innerHTML = '<span>' + n + (n === 1 ? ' person' : ' people') + '</span>' +
      '<span>' + esc(lastSync || (serverMode ? 'contacts.json not loaded yet' : 'Only in this browser')) + '</span>' +
      '<span>' + (serverMode ? 'Server owns contacts.json · rolling backups in Data/backups/.'
                             : 'Start the tracker server so changes reach contacts.json.') + '</span>';
  }

  function cache() {
    try { localStorage.setItem(CACHE_KEY, JSON.stringify(contacts)); } catch (e) {}
  }

  /* (Re)fetch contacts.json and its revision. Used by init, by the 409
     conflict handler, and by the visibility/focus refresh below — so a tab
     left open picks up writes a skill run or another tab made meanwhile. */
  async function reload() {
    if (!serverMode) return;
    try {
      var r = await fetch('contacts.json', { cache: 'no-store' });
      if (!r.ok) throw new Error('HTTP ' + r.status);
      contacts = await r.json();
      revision = r.headers.get('X-Contacts-Revision') || '';
      loaded = true;
      saveFailed = false;
      lastSync = 'Loaded contacts.json · ' + clock();
      cache();
      render();
    } catch (e) {
      toast('⚠ Could not load contacts from the tracker server.');
    }
  }

  async function save() {
    cache();
    if (!serverMode) { lastSync = 'Saved in this browser only · ' + clock(); paintStatus(); return; }
    if (!loaded) {
      toast('⚠ Contacts have not loaded from the tracker server yet — not saving.');
      return;
    }
    if (writing) { pending = true; return; }
    writing = true;
    try {
      var r = await fetch('save-contacts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Base-Revision': revision },
        body: JSON.stringify(contacts)
      });
      var j = await r.json().catch(function () { return {}; });
      if (r.status === 409) {
        writing = false;
        pending = false;
        await reload();
        toast('Contacts changed elsewhere (a Claude run?) — reloaded. Please redo your last change.');
        return;
      }
      if (!r.ok) throw new Error(j.error || ('HTTP ' + r.status));
      if (j.revision) revision = j.revision;
      saveFailed = false;
      lastSync = 'Saved to contacts.json · ' + clock();
      if (j.syncWarning) toast('⚠ Saved here, but not yet to GitHub — it will retry on the next save.');
    } catch (e) {
      saveFailed = true;
      toast('⚠ Could not save contacts: ' + e.message);
    }
    paintStatus();
    writing = false;
    if (pending) { pending = false; save(); }
  }

  function commit() { save(); render(); }

  function maybeReload() {
    if (!serverMode || writing) return;
    reload();
  }

  function onVisibilityChange() {
    if (document.visibilityState === 'visible') maybeReload();
  }

  function byId(id) {
    for (var i = 0; i < contacts.length; i++) if (contacts[i].id === id) return contacts[i];
    return null;
  }

  function contactOf(el) {
    var card = el.closest('.pcard, .prow');
    return card ? byId(card.dataset.id) : null;
  }

  /* ---------- rendering ---------- */
  function notice() {
    if (!serverMode) {
      return '<div class="pwarn">People needs the tracker server. Open the tracker with the Job Tracker launcher ' +
        '(or ask Claude to open it) and reload. Without it, changes here stay in this browser and never reach contacts.json.</div>';
    }
    if (!loaded) {
      return '<div class="pwarn">Could not load contacts from the tracker server. Changes here stay in this ' +
        'browser until it loads successfully — switch back to this tab, or reload the page, to retry.</div>';
    }
    return '';
  }

  // Same cards as the Jobs page KPIs (.kpis/.kpi from index.html).
  function statsBar() {
    return '<div class="kpis">' + PeopleCore.stats(contacts, cfg, today).map(function (s) {
      return '<div class="kpi' + (s.level ? ' ' + s.level : '') + '"><div class="n">' + esc(s.value) +
        '</div><div class="l">' + esc(s.label) + '</div></div>';
    }).join('') + '</div>';
  }

  function companyOptions() {
    var seen = {};
    return state.apps.map(function (a) { return (a.company || '').trim(); })
      .filter(function (n) { var k = n.toLowerCase(); if (!n || seen[k]) return false; seen[k] = true; return true; })
      .sort()
      .map(function (n) { return '<option value="' + esc(n) + '">'; }).join('');
  }

  // The add/edit person dialog: same .modal/.sheet/.field look and behaviour as the job dialog.
  function modalHtml() {
    var rel = PeopleCore.RELATIONS.map(function (r) { return '<option>' + esc(r) + '</option>'; }).join('');
    return '<div class="modal" id="pmodal"><form class="sheet" id="padd" autocomplete="off">' +
      '<h2 id="pa_heading">Add person</h2><div class="grid">' +
      '<div class="field"><label for="pa_name">Name *</label><input id="pa_name" required></div>' +
      '<div class="field"><label for="pa_company">Company *</label><input id="pa_company" list="pa_companies" required>' +
      '<datalist id="pa_companies"></datalist></div>' +
      '<div class="field full"><label for="pa_url">LinkedIn profile URL *</label>' +
      '<input id="pa_url" placeholder="https://www.linkedin.com/in/…" required></div>' +
      '<div class="field"><label for="pa_title">Title</label><input id="pa_title"></div>' +
      '<div class="field"><label for="pa_relation">Relation</label><select id="pa_relation">' +
      '<option value="">—</option>' + rel + '</select></div>' +
      '<div class="field" id="pa_like_field"><label for="pa_like">Likelihood (0–100)</label>' +
      '<input id="pa_like" type="number" min="0" max="100"></div>' +
      '<div class="field pcheck" id="pa_connected_field"><label class="ptoggle">' +
      '<input type="checkbox" id="pa_connected"> Already connected on LinkedIn</label></div>' +
      '<div class="field full"><label for="pa_notes">Note</label>' +
      '<textarea id="pa_notes" placeholder="How you know them (optional)"></textarea></div>' +
      '</div><div class="foot"><button class="btn danger" type="button" id="pa_delete">Delete</button>' +
      '<div style="display:flex;gap:8px"><button class="btn" type="button" id="pa_cancel">Cancel</button>' +
      '<button class="btn primary" type="submit" id="pa_submit">Add person</button></div></div></form></div>';
  }

  function readAddForm() {
    var f = {};
    ADD_FIELDS.forEach(function (id) { f[id] = document.getElementById(id).value; });
    f.pa_connected = document.getElementById('pa_connected').checked;
    return f;
  }

  // c: the person to edit, or null to add someone new.
  function openModal(c) {
    var g = function (id) { return document.getElementById(id); };
    editingId = c ? c.id : null;
    g('pa_heading').textContent = c ? 'Edit ' + c.name : 'Add person';
    g('pa_submit').textContent = c ? 'Save' : 'Add person';
    g('pa_delete').style.display = c ? '' : 'none';
    g('pa_like_field').style.display = c ? '' : 'none';
    g('pa_connected_field').style.display = c ? 'none' : '';
    g('pa_companies').innerHTML = companyOptions();
    var v = c
      ? { pa_name: c.name, pa_company: c.company, pa_url: c.linkedinUrl, pa_title: c.title,
          pa_relation: c.relation, pa_notes: c.notes, pa_like: String(Number(c.likelihood) || 0) }
      : { pa_company: companyFilter };
    ADD_FIELDS.forEach(function (id) { g(id).value = v[id] || ''; });
    g('pa_connected').checked = false;
    g('pmodal').classList.add('show');
    g('pa_name').focus();
  }

  function closeModal() {
    editingId = null;
    document.getElementById('pmodal').classList.remove('show');
  }

  function filterChip() {
    if (!companyFilter) return '';
    return '<div class="pfilter">Showing people at <strong>' + esc(companyFilter) +
      '</strong><span class="minibtn" data-act="clearfilter">Show everyone</span></div>';
  }

  function relChip(c) {
    if (!c.relation) return '';
    return '<span class="prel' + (c.relation === 'ex-colleague' ? ' warm' : '') + '">' + esc(c.relation) + '</span>';
  }

  function roles(c) {
    return (c.appIds || []).map(function (id) {
      var a = state.apps.find(function (x) { return x.id === id; });
      return a ? esc(a.role) : '';
    }).filter(Boolean).join(' · ');
  }

  function stageActions(c) {
    var html = '';
    if (c.linkedinUrl) html += '<span class="minibtn" data-act="profile">Profile ↗</span>';
    html += '<span class="minibtn" data-act="edit">Edit</span>';
    if (c.stage === 'Found') html += '<span class="minibtn" data-act="approve">Approve</span>';
    if (c.stage === 'Found' || c.stage === 'Queued') html += '<span class="minibtn" data-act="skip">Skip</span>';
    return '<div class="rowbtns">' + html + '</div>';
  }

  function noteEditor(c) {
    if (cfg.noteSelection === 'off' || (c.stage !== 'Found' && c.stage !== 'Queued')) return '';
    var can = PeopleCore.canToggleNote(c, contacts, cfg, today);
    var html = '<label class="ptoggle"><input type="checkbox" data-act="usenote"' + (c.useNote ? ' checked' : '') +
      (can ? '' : ' disabled') + '> Send with a note' + (can ? '' : ' <em>(monthly budget used)</em>') + '</label>';
    if (c.useNote) {
      var n = (c.connectNote || '').length;
      html += '<textarea data-act="note" maxlength="' + cfg.noteCharLimit +
        '" placeholder="Leave empty and the next run drafts it">' + esc(c.connectNote) + '</textarea>' +
        '<div class="pcount' + (n > cfg.noteCharLimit ? ' over' : '') + '">' + n + '/' + cfg.noteCharLimit + '</div>';
    }
    return html;
  }

  function askEditor(c) {
    if (c.stage !== 'Connected') return '';
    var src = c.attachmentSource || cfg.defaultAttachment;
    function opt(v, label) { return '<option value="' + v + '"' + (src === v ? ' selected' : '') + '>' + label + '</option>'; }
    var file = c.attachment
      ? '<span class="pfile">' + esc(c.attachment.split('/').pop()) + '</span><span class="minibtn" data-act="reveal">Reveal</span>'
      : '<span class="pfile missing">' + (src === 'upload' ? 'Upload a PDF' : src === 'tailored' ? 'Resolved on the next prep run' : 'Set baseResumePath in outreach-config.json') + '</span>';
    return '<textarea data-act="ask" placeholder="Drafted by the next prep run">' + esc(c.askMessage) + '</textarea>' +
      '<div class="pattach"><select data-act="source">' + opt('tailored', 'Tailored resume') + opt('base', 'Base resume') +
      opt('upload', 'Upload PDF…') + '</select>' +
      (src === 'upload' ? '<input type="file" accept="application/pdf" data-act="upload">' : '') + file + '</div>' +
      '<label class="ptoggle"><input type="checkbox" data-act="askok"' + (c.askApproved ? ' checked' : '') +
      (PeopleCore.canApproveAsk(c) || c.askApproved ? '' : ' disabled') + '> Approve ask</label>';
  }

  function askedSection(c) {
    if (c.stage !== 'Asked') return '';
    var html = '<p class="pnotes">Sent ' + esc(c.dateAsked) + ': ' + esc(c.askMessage) + '</p>';
    if (c.followupMessage && !c.dateFollowedUp) {
      html += '<label>Follow-up draft</label><textarea data-act="followup">' + esc(c.followupMessage) + '</textarea>';
    }
    return html;
  }

  function moveSelect(c) {
    return '<select class="pmove" data-act="move"><option value="">Move to…</option>' +
      PeopleCore.ORDER.filter(function (s) { return s !== c.stage; })
        .map(function (s) { return '<option>' + s + '</option>'; }).join('') + '</select>';
  }

  function card(c) {
    return '<details class="pcard" draggable="true" data-id="' + esc(c.id) + '"><summary>' +
      '<div class="pname">' + esc(c.name) + (c.useNote ? ' <span class="pnote" title="Request goes with a note">✎</span>' : '') + '</div>' +
      '<div class="ptitle">' + esc(c.title) + ' · ' + esc(c.company) + '</div>' +
      '<div class="pmeta">' + relChip(c) + '<span class="plike">◎ ' + (Number(c.likelihood) || 0) + '</span></div>' +
      '</summary><div class="pbody">' +
      (c.why ? '<p>' + esc(c.why) + '</p>' : '') +
      (roles(c) ? '<p class="proles">For: ' + roles(c) + '</p>' : '') +
      (c.notes ? '<p class="pnotes">' + esc(c.notes) + '</p>' : '') +
      stageActions(c) + noteEditor(c) + askEditor(c) + askedSection(c) + moveSelect(c) +
      '</div></details>';
  }

  function columns(list) {
    return COLS.map(function (col) {
      var items = list.filter(function (c) { return PeopleCore.column(c.stage) === col; })
        .sort(function (a, b) { return (Number(b.likelihood) || 0) - (Number(a.likelihood) || 0); });
      var collapsed = col === 'Closed' && !closedOpen;
      var body = collapsed ? '' : (items.map(card).join('') || '<div class="drophint">drop here</div>');
      var tog = col === 'Closed' ? '<button class="ptog" type="button">' + (collapsed ? '▸' : '▾') + '</button>' : '';
      return '<div class="pcol' + (collapsed ? ' collapsed' : '') + '" data-col="' + col + '"><h2>' + tog +
        '<span class="pcolname">' + col + '</span><span class="ct">' + items.length + '</span></h2>' + body + '</div>';
    }).join('');
  }

  function tableCell(c, key) {
    if (key === 'name') return '<td><strong>' + esc(c.name) + '</strong></td>';
    if (key === 'relation') return '<td>' + relChip(c) + '</td>';
    if (key === 'likelihood') return '<td>' + (Number(c.likelihood) || 0) + '</td>';
    return '<td>' + esc(c[key]) + '</td>';
  }

  function table(list) {
    var items = list.slice().sort(function (a, b) {
      var x = a[tableSort], y = b[tableSort];
      if (tableSort === 'likelihood') { x = Number(x) || 0; y = Number(y) || 0; }
      else { x = String(x || '').toLowerCase(); y = String(y || '').toLowerCase(); }
      return (x < y ? -1 : x > y ? 1 : 0) * tableDir;
    });
    var head = TABLE_COLS.map(function (col) {
      return '<th data-sort="' + col[0] + '">' + col[1] + (tableSort === col[0] ? (tableDir > 0 ? ' ▲' : ' ▼') : '') + '</th>';
    }).join('') + '<th></th>';
    var rows = items.map(function (c) {
      return '<tr class="clickable prow" data-id="' + esc(c.id) + '" title="Edit">' +
        TABLE_COLS.map(function (col) { return tableCell(c, col[0]); }).join('') +
        '<td>' + (c.linkedinUrl ? '<span class="minibtn" data-act="profile">Profile ↗</span>' : '') + '</td></tr>';
    }).join('');
    return '<div class="ptable"><table><thead><tr>' + head + '</tr></thead><tbody>' +
      (rows || '<tr><td colspan="' + (TABLE_COLS.length + 1) + '">No people match.</td></tr>') + '</tbody></table></div>';
  }

  function view(newLayout) {
    if (newLayout) layout = newLayout;
    var root = document.getElementById('people');
    var open = new Set(Array.prototype.map.call(root.querySelectorAll('.pcard[open]'),
      function (el) { return el.dataset.id; }));
    var q = (document.getElementById('q').value || '').toLowerCase();
    var list = contacts.filter(function (c) {
      if (companyFilter && (c.company || '').trim().toLowerCase() !== companyFilter.trim().toLowerCase()) return false;
      return !q || [c.name, c.company, c.title, c.relation, c.notes].join(' ').toLowerCase().indexOf(q) >= 0;
    });
    var body = layout === 'table' ? table(list) : '<div class="pboard">' + columns(list) + '</div>';
    root.innerHTML = notice() + statsBar() + filterChip() + body;
    paintStatus();
    root.querySelectorAll('.pcard').forEach(function (el) { if (open.has(el.dataset.id)) el.open = true; });
  }

  function openAdd() { openModal(null); }

  function appIdsFor(company) {
    var key = company.trim().toLowerCase();
    return state.apps
      .filter(function (a) { return (a.company || '').trim().toLowerCase() === key; })
      .map(function (a) { return a.id; });
  }

  function deleteEditing() {
    var c = byId(editingId);
    if (!c) { closeModal(); return; }
    if (!confirm('Delete ' + c.name + ' from People? A later morning run may find and suggest them again.')) return;
    contacts = contacts.filter(function (x) { return x.id !== c.id; });
    closeModal();
    toast('Deleted ' + c.name + '.');
    commit();
  }

  function newId() {
    return 'ct-' + Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
  }

  function onSubmit(e) {
    if (e.target.id !== 'padd') return;
    e.preventDefault();
    if (serverMode && !loaded) { toast('⚠ Contacts have not loaded from the tracker server yet — try again in a moment.'); return; }
    var f = readAddForm();
    var fields = { name: f.pa_name, company: f.pa_company, linkedinUrl: f.pa_url, title: f.pa_title,
                   relation: f.pa_relation, notes: f.pa_notes, connected: f.pa_connected, likelihood: f.pa_like };
    var editing = editingId ? byId(editingId) : null;
    if (editingId && !editing) {
      closeModal();
      toast('⚠ This person was changed or removed elsewhere (a Claude run?). Nothing was saved.');
      return;
    }
    var err = PeopleCore.validateNew(fields, contacts, editing && editing.id);
    if (err) { toast('⚠ ' + err); return; }
    if (editing) {
      var sameCompany = editing.company.trim().toLowerCase() === fields.company.trim().toLowerCase();
      PeopleCore.applyEdit(editing, fields, sameCompany ? (editing.appIds || []) : appIdsFor(fields.company));
      closeModal();
      toast('Saved ' + editing.name + '.');
      commit();
      return;
    }
    var c = PeopleCore.newContact(fields, cfg, today, newId(), appIdsFor(fields.company));
    contacts.push(c);
    closeModal();
    toast('Added ' + c.name + ' to ' + c.stage + '.');
    commit();
  }

  function badge(a) {
    var list = PeopleCore.forCompany(contacts, a.company);
    if (!list.length) return '';
    return '<span class="pbadge" data-company="' + esc(a.company) + '" title="Open People for ' + esc(a.company) + '">👥 ' +
      list.length + ' · ' + esc(PeopleCore.furthest(list)) + '</span>';
  }

  /* ---------- events ---------- */
  function onClick(e) {
    var t = e.target;
    if (t.closest('.ptog')) { closedOpen = !closedOpen; view(); return; }
    if (t.closest('[data-act="clearfilter"]')) { companyFilter = ''; view(); return; }
    var th = t.closest('th[data-sort]');
    if (th) {
      if (tableSort === th.dataset.sort) tableDir = -tableDir;
      else { tableSort = th.dataset.sort; tableDir = th.dataset.sort === 'likelihood' ? -1 : 1; }
      view();
      return;
    }
    var act = t.dataset && t.dataset.act;
    var c = contactOf(t);
    if (!c) return;
    if (!act) { if (t.closest('.prow')) openModal(c); return; }
    if (act === 'profile') openExternal(c.linkedinUrl);
    else if (act === 'edit') openModal(c);
    else if (act === 'approve') { PeopleCore.approve(c, today); commit(); }
    else if (act === 'skip') { PeopleCore.moveStage(c, 'Skipped', today); commit(); }
    else if (act === 'reveal' && serverMode) fetch('reveal?path=' + encodeURIComponent(c.attachment)).catch(function () {});
  }

  function onChange(e) {
    var t = e.target;
    var act = t.dataset && t.dataset.act;
    var c = contactOf(t);
    if (!act || !c) return;
    if (act === 'usenote') c.useNote = t.checked;
    else if (act === 'note') c.connectNote = t.value.slice(0, cfg.noteCharLimit);
    else if (act === 'ask') { c.askMessage = t.value; c.askApproved = false; }
    else if (act === 'followup') c.followupMessage = t.value;
    else if (act === 'source') PeopleCore.setAttachmentSource(c, t.value, cfg);
    else if (act === 'askok') c.askApproved = t.checked && PeopleCore.canApproveAsk(c);
    else if (act === 'move' && t.value) PeopleCore.moveStage(c, t.value, today);
    else if (act === 'upload') { upload(c, t.files[0]); return; }
    else return;
    commit();
  }

  function onInput(e) {
    var t = e.target;
    if (t.dataset.act !== 'note') return;
    var el = t.nextElementSibling;
    if (!el) return;
    el.textContent = t.value.length + '/' + cfg.noteCharLimit;
    el.classList.toggle('over', t.value.length > cfg.noteCharLimit);
  }

  async function upload(c, file) {
    if (!file) return;
    if (!serverMode) { toast('Uploading needs the tracker server running.'); return; }
    try {
      var r = await fetch('upload-attachment?contact=' + encodeURIComponent(c.id) + '&name=' + encodeURIComponent(file.name),
        { method: 'POST', headers: { 'Content-Type': 'application/pdf' }, body: file });
      var j = await r.json();
      if (!r.ok || !j.ok) throw new Error(j.error || ('HTTP ' + r.status));
      c.attachmentSource = 'upload';
      c.attachment = j.path;
      c.askApproved = false;
      toast('Uploaded ' + file.name);
      commit();
    } catch (err) {
      toast('⚠ Upload failed: ' + err.message);
    }
  }

  function onDragStart(e) {
    var card = e.target.closest && e.target.closest('.pcard');
    if (card) e.dataTransfer.setData('text/x-contact', card.dataset.id);
  }

  function onDragOver(e) {
    var col = e.target.closest && e.target.closest('.pcol');
    if (col) { e.preventDefault(); col.classList.add('over'); }
  }

  function onDragLeave(e) {
    var col = e.target.closest && e.target.closest('.pcol');
    if (col) col.classList.remove('over');
  }

  function onDrop(e) {
    var col = e.target.closest && e.target.closest('.pcol');
    if (!col) return;
    e.preventDefault();
    col.classList.remove('over');
    var c = byId(e.dataTransfer.getData('text/x-contact'));
    if (!c || PeopleCore.column(c.stage) === col.dataset.col) return;
    PeopleCore.moveStage(c, col.dataset.col === 'Closed' ? 'Skipped' : col.dataset.col, today);
    commit();
  }

  function onBadgeClick(e) {
    var b = e.target.closest && e.target.closest('.pbadge');
    if (!b) return;
    e.preventDefault();
    e.stopPropagation();
    show(b.dataset.company);
  }

  function show(company) {
    companyFilter = company || '';
    setDataset('people');
  }

  async function init() {
    try { var raw = localStorage.getItem(CACHE_KEY); if (raw) contacts = JSON.parse(raw); } catch (e) {}
    if (serverMode) {
      await reload();
      try {
        var c = await fetch('outreach-config.json', { cache: 'no-store' });
        if (c.ok) cfg = PeopleCore.withDefaults(await c.json());
      } catch (e) {}
    } else {
      cache();
    }
    var root = document.getElementById('people');
    root.addEventListener('click', onClick);
    root.addEventListener('change', onChange);
    root.addEventListener('input', onInput);
    root.addEventListener('dragstart', onDragStart);
    root.addEventListener('dragover', onDragOver);
    root.addEventListener('dragleave', onDragLeave);
    root.addEventListener('drop', onDrop);
    document.body.insertAdjacentHTML('beforeend', modalHtml());
    var modal = document.getElementById('pmodal');
    document.getElementById('padd').addEventListener('submit', onSubmit);
    document.getElementById('pa_cancel').addEventListener('click', closeModal);
    document.getElementById('pa_delete').addEventListener('click', deleteEditing);
    modal.addEventListener('click', function (e) { if (e.target === modal) closeModal(); });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && modal.classList.contains('show')) closeModal();
    });
    document.addEventListener('click', onBadgeClick, true);
    document.addEventListener('visibilitychange', onVisibilityChange);
    window.addEventListener('focus', maybeReload);
    render();
  }

  return { init: init, view: view, badge: badge, show: show, openAdd: openAdd };
})();

window.syncReady.then(function () { People.init(); });
