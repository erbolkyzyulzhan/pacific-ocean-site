const storyList = document.querySelector('#story-list');
const escapeHtml = (value) => String(value).replace(/[&<>"']/g, (char) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
const depthRange = (zone) => `${Number(zone.min_depth).toLocaleString('ru-RU')}–${Number(zone.max_depth).toLocaleString('ru-RU')} м`;
let loadedZones = [];
const conditionFallbacks = {
  sunlight: {pressure:'Абсолюттік қысым шамамен 1–21 атмосфера.',body_reaction:'Қысым құлаққа әсер етуі мүмкін. Терең еркін сүңгуде өкпе көлемі азайып, жарақат қаупі артады.',protection:'Дайындық пен тереңдікке сәйкес жабдық қажет; қарапайым маска қысымнан қорғамайды.',takeaway:'Жарық бар, бірақ тереңдеген сайын қысым да өседі.'},
  twilight: {pressure:'Абсолюттік қысым шамамен 21–101 атмосфера.',body_reaction:'Жарық азаяды, фотосинтез жүрмейді. Қысымды тыныс алу газымен сүңгуде азот наркозы қаупі болуы мүмкін.',protection:'Осы тереңдікке есептелген герметикалық аппарат керек.',takeaway:'Бұл — көмескі жарық пен жоғары қысым аймағы.'},
  midnight: {pressure:'Абсолюттік қысым шамамен 101–401 атмосфера.',body_reaction:'Күн сәулесі жетпейді; адам айналаны тек аппарат шамымен көреді.',protection:'Берік кабинасы мен тіршілікті қамтамасыз ету жүйесі бар аппарат қажет.',takeaway:'Сыртқы қысымды аппараттың корпусы көтереді.'},
  abyss: {pressure:'Абсолюттік қысым шамамен 401–601 атмосфера.',body_reaction:'Қараңғылық, суық және орасан қысым болады; адам аппарат жүйелеріне тәуелді.',protection:'Арнайы тереңсу аппараты мен зерттеу кемесінің қолдауы қажет.',takeaway:'Бұл аймаққа тек арнайы зерттеу аппаратымен жетуге болады.'},
  hadal: {pressure:'Абсолюттік қысым шамамен 601–1 101 атмосфера.',body_reaction:'Сыртта жарық жоқ; қорғалған кабинада адам айналаны аппарат құралдары арқылы бақылайды.',protection:'Хадаль тереңдігіне арналған күшейтілген корпус пен дербес тіршілік жүйесі қажет.',takeaway:'Мұхиттың ең терең қабатына арнайы аппараттар ғана жетеді.'}
};

async function buildZoneStories() {
  const zones = await fetch('/api/zones').then(response => response.json());
  loadedZones = zones;
  const species = await fetch('/api/species').then(response => response.json());
  storyList.innerHTML = zones.map((zone, index) => {
    const residents = species.filter(item => item.zone_id === zone.id);
    const facts = (zone.facts || []).map(fact => `<article class="story-fact"><b>${escapeHtml(fact.label)}</b><p>${escapeHtml(fact.detail)}</p></article>`).join('');
    const animals = residents.map(item => `<article class="resident"><span class="resident-mark">✦</span><div><h3>${escapeHtml(item.name)}</h3><p>${escapeHtml(item.description)}</p><small>${escapeHtml(item.category)}</small></div></article>`).join('');
    return `<section class="zone-story zone-${escapeHtml(zone.id)}" id="${escapeHtml(zone.id)}" style="--story-depth:${Math.round(index * 24)}%">
      <div class="story-image"></div><div class="story-tint"></div>
      <div class="story-inner"><header class="story-heading"><span class="story-index">0${index + 1} / 05</span><p class="eyebrow">${escapeHtml(zone.scientific_name)}</p><h2>${escapeHtml(zone.title)}</h2><p class="story-description">${escapeHtml(zone.description)}</p><div class="story-depth">${depthRange(zone)}</div><button class="condition-trigger" type="button" data-zone="${escapeHtml(zone.id)}" title="Адамға осы тереңдікте қандай жағдай болатынын қараңыз">АДАМҒА ҚАНДАЙ ЖАҒДАЙ БОЛАДЫ? <span>↗</span></button></header>
        <div class="story-columns"><div class="facts-panel"><h3>АЙМАҚ ЕРЕКШЕЛІКТЕРІ</h3>${facts}</div><div class="residents-panel"><h3>МҰХИТ ТҰРҒЫНДАРЫ</h3>${animals || '<p>Бұл аймақ туралы мәлімет әзірге енгізілмеген.</p>'}</div></div>
      </div>
    </section>`;
  }).join('') + `<dialog class="human-dialog" id="human-dialog"><button class="dialog-close" type="button" aria-label="Жабу">×</button><p class="eyebrow">АДАМҒА ҚАНДАЙ ЖАҒДАЙ БОЛАДЫ?</p><h2 id="dialog-zone-title"></h2><p class="dialog-range" id="dialog-zone-range"></p><div class="dialog-details"><article><b>ҚЫСЫМ</b><p id="dialog-pressure"></p></article><article><b>ДЕНЕ РЕАКЦИЯСЫ</b><p id="dialog-body-reaction"></p></article><article><b>ҚОРҒАНЫС</b><p id="dialog-protection"></p></article><article class="dialog-takeaway"><b>ТҮЙІН</b><p id="dialog-takeaway"></p></article></div><p class="dialog-note">Бұл — оқу материалы. Терең сүңгу өмірге қауіпті; тек арнайы дайындық пен жабдық қажет.</p></dialog>`;
  const dialog = document.querySelector('#human-dialog');
  storyList.querySelectorAll('.condition-trigger').forEach(button => button.addEventListener('click', () => {
    const zone = loadedZones.find(item => item.id === button.dataset.zone);
    if (!zone) return;
    const condition = zone.human_condition || conditionFallbacks[zone.id];
    if (!condition) return;
    document.querySelector('#dialog-zone-title').textContent = zone.title;
    document.querySelector('#dialog-zone-range').textContent = depthRange(zone);
    document.querySelector('#dialog-pressure').textContent = condition.pressure;
    document.querySelector('#dialog-body-reaction').textContent = condition.body_reaction;
    document.querySelector('#dialog-protection').textContent = condition.protection;
    document.querySelector('#dialog-takeaway').textContent = condition.takeaway;
    if (typeof dialog.showModal === 'function') dialog.showModal(); else dialog.setAttribute('open', '');
  }));
  dialog.querySelector('.dialog-close').addEventListener('click', () => { if (typeof dialog.close === 'function') dialog.close(); else dialog.removeAttribute('open'); });
  dialog.addEventListener('click', event => { if (event.target === dialog) { if (typeof dialog.close === 'function') dialog.close(); else dialog.removeAttribute('open'); } });
}

buildZoneStories().catch(() => { storyList.innerHTML = '<p class="stories-loading">Аймақтарды жүктеу мүмкін болмады. Серверді іске қосып, бетті жаңартыңыз.</p>'; });
