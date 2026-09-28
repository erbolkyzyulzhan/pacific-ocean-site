const entryForm = document.querySelector('#entry-form');
const entryZone = document.querySelector('#entry-zone');
const formStatus = document.querySelector('#form-status');
const communityList = document.querySelector('#community-list');
const safeText = value => String(value).replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));

async function loadEntryZones() {
  const zones = await fetch('/api/zones').then(response => response.json());
  entryZone.innerHTML = '<option value="">Барлық аймақ</option>' + zones.map(zone => `<option value="${safeText(zone.id)}">${safeText(zone.title)}</option>`).join('');
}

async function loadCommunity() {
  const entries = await fetch('/api/community').then(response => response.json());
  communityList.innerHTML = entries.length ? entries.map(entry => `<article class="community-entry"><span>${entry.entry_type === 'question' ? 'СҰРАҚ' : 'ҰСЫНЫЛҒАН ДЕРЕК'} · ${safeText(entry.zone_title || 'Барлық аймақ')}</span><p>${safeText(entry.message)}</p><small>${new Date(entry.created_at + 'Z').toLocaleDateString('kk-KZ')}</small></article>`).join('') : '<p>Жарияланған қонақ жазбалары әзірге жоқ.</p>';
}

entryForm.addEventListener('submit', async event => {
  event.preventDefault();
  const data = new FormData(entryForm);
  const payload = Object.fromEntries(data.entries());
  formStatus.textContent = 'Жіберіліп жатыр…';
  try {
    const response = await fetch('/api/entries', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || 'Қайта байқап көріңіз.');
    entryForm.reset();
    formStatus.textContent = 'Жазба сақталды. Тексерілгеннен кейін сайтта жарияланады.';
  } catch (error) {
    formStatus.textContent = error.message || 'Жіберу мүмкін болмады. Серверді тексеріңіз.';
  }
});

loadEntryZones().catch(() => { formStatus.textContent = 'Аймақтарды жүктеу мүмкін болмады.'; });
loadCommunity().catch(() => {});
