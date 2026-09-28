const safe = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
const rangeText = zone => `${Number(zone.min_depth).toLocaleString('ru-RU')}–${Number(zone.max_depth).toLocaleString('ru-RU')} м`;
const loginForm = document.querySelector('#admin-login');
const loginStatus = document.querySelector('#login-status');
const adminContent = document.querySelector('#admin-content');
let refreshTimer;

async function loadDatabase() {
  const response = await fetch('/api/database', {cache:'no-store'});
  if (response.status === 401) {
    clearInterval(refreshTimer);
    adminContent.hidden = true;
    loginForm.hidden = false;
    return false;
  }
  if (!response.ok) throw new Error('Деректер базасын жүктеу мүмкін болмады.');
  const data = await response.json();
  adminContent.hidden = false;
  loginForm.hidden = true;
  const pending = data.visitor_entries.filter(item=>item.status==='pending').length;
  document.querySelector('#database-stats').innerHTML = `<div><b>${pending}</b><span>жаңа, тексерілмеген</span></div><div><b>${data.visitor_entries.length}</b><span>барлық жазба</span></div><div><b>${data.zones.length}</b><span>мұхит аймағы</span></div><div><b>${data.species.length}</b><span>тұрғын түрі</span></div>`;
  document.querySelector('#zones-rows').innerHTML = data.zones.map(zone => `<tr><td>${safe(zone.title)}</td><td>${rangeText(zone)}</td><td>${data.species.filter(item=>item.zone_id===zone.id).length}</td><td>${safe(zone.scientific_name)}</td></tr>`).join('');
  document.querySelector('#species-rows').innerHTML = data.species.map(item => `<tr><td>${safe(item.name)}</td><td>${safe(item.zone_title)}</td><td>${safe(item.category)}</td><td>${safe(item.description)}</td></tr>`).join('');
  document.querySelector('#condition-rows').innerHTML = data.conditions.map(item => `<tr><td>${safe(item.zone_title)}</td><td>${safe(item.pressure)}</td><td>${safe(item.body_reaction)}</td><td>${safe(item.protection)}</td><td>${safe(item.takeaway)}</td></tr>`).join('');
  document.querySelector('#entries-rows').innerHTML = data.visitor_entries.length ? data.visitor_entries.map(item => `<tr><td>${new Date(item.created_at+'Z').toLocaleString('kk-KZ')}</td><td>${item.entry_type==='question'?'Сұрақ':'Дерек'}</td><td>${safe(item.zone_title||'Барлық аймақ')}</td><td>${safe(item.visitor_name||'Қонақ')}</td><td class="entry-text">${safe(item.message)}</td><td><span class="status ${item.status}">${item.status==='pending'?'Жаңа':'Жарияланды'}</span></td><td>${item.status==='pending'?`<button class="publish-entry" data-id="${item.id}">Жариялау</button>`:''}</td></tr>`).join('') : '<tr><td colspan="7" class="empty-row">Әзірге ешкім сұрақ немесе дерек жіберген жоқ.</td></tr>';
  document.querySelectorAll('.publish-entry').forEach(button => button.addEventListener('click', async () => {
    button.disabled = true;
    const result = await fetch(`/api/entries/${button.dataset.id}/publish`, {method:'POST'});
    if (result.ok) await loadDatabase(); else { button.disabled = false; button.textContent = 'Қате'; }
  }));
  document.querySelector('#refresh-note').textContent = `Жаңартылды: ${new Date().toLocaleTimeString('kk-KZ')} · жаңа жазбалар әр 10 секунд сайын тексеріледі.`;
  return true;
}

loginForm.addEventListener('submit', async event => {
  event.preventDefault();
  const button = loginForm.querySelector('button');
  button.disabled = true;
  loginStatus.textContent = 'Тексеріліп жатыр…';
  try {
    const response = await fetch('/api/admin/login', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:document.querySelector('#admin-password').value})});
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || 'Кіру мүмкін болмады.');
    document.querySelector('#admin-password').value = '';
    if (await loadDatabase()) refreshTimer = setInterval(() => loadDatabase().catch(()=>{}), 10000);
  } catch (error) { loginStatus.textContent = error.message; }
  button.disabled = false;
});

document.querySelector('#logout-button').addEventListener('click', async () => {
  clearInterval(refreshTimer);
  await fetch('/api/admin/logout', {method:'POST'});
  adminContent.hidden = true;
  loginForm.hidden = false;
  loginStatus.textContent = 'Сайттан шықтың.';
});

loadDatabase().catch(error => { loginStatus.textContent = error.message; });
