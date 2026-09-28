from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs
import json
import os
import secrets
import sqlite3

ROOT = Path(__file__).resolve().parent
DB = ROOT / "ocean.db"
ADMIN_PASSWORD_FILE = ROOT / "admin_password.txt"
ADMIN_SESSIONS = set()

def get_admin_password():
    if not ADMIN_PASSWORD_FILE.exists():
        ADMIN_PASSWORD_FILE.write_text(secrets.token_urlsafe(9), encoding="utf-8")
    return ADMIN_PASSWORD_FILE.read_text(encoding="utf-8").strip()

ZONES = [
    ("sunlight", "Күн сәулелі аймақ", "Эпипелагиаль", 0, 200, "Жарық мол түсетін, фотосинтез жүретін жоғарғы қабат."),
    ("twilight", "Ымыртты аймақ", "Мезопелагиаль", 200, 1000, "Күн сәулесі әлсіреп, тереңдеген сайын қараңғылық қоюланады."),
    ("midnight", "Қараңғы аймақ", "Батипелагиаль", 1000, 4000, "Күн сәулесі жетпейтін суық әрі қараңғы кеңістік."),
    ("abyss", "Бездна / Тұңғиық аймағы", "Абиссаль", 4000, 6000, "Мұхит түбіне жақын, қысымы өте жоғары аймақ."),
    ("hadal", "Шыңырау / Мариан шұңғымасы", "Хадаль", 6000, 11000, "Ең терең науалар мен Мариан шұңғымасын қамтиды."),
]

SPECIES = [
    ("sunlight", "Дельфин", "Күн сәулелі аймақтың жылдам әрі әлеуметтік сүтқоректісі.", "Сүтқоректі"),
    ("sunlight", "Көк кит", "Жер бетіндегі ең ірі жануар; крильмен қоректенеді.", "Сүтқоректі"),
    ("sunlight", "Теңіз тасбақасы", "Мұхиттың жылы беткі сулары мен жағалауларында кездеседі.", "Бауырымен жорғалаушы"),
    ("sunlight", "Планктон", "Мұхит қоректік тізбегінің негізін құрайтын ұсақ ағзалар.", "Ұсақ ағзалар"),
    ("twilight", "Кальмар", "Ымыртты қабатта тіршілік ететін жұмсақ денелі жыртқыш.", "Басаяқты"),
    ("twilight", "Жарқырауық балық", "Биолюминесценция арқылы әлсіз жарық шығара алады.", "Балық"),
    ("twilight", "Медуза", "Ағыспен қозғалатын, денесі мөлдір теңіз жануары.", "Омыртқасыз"),
    ("midnight", "Мұхит шайтаны", "Қармақ тәрізді жарқыраған мүшесімен жемтігін тартады.", "Балық"),
    ("midnight", "Кашалот", "Тереңге сүңгіп, кальмар аулайтын ірі тісті кит.", "Сүтқоректі"),
    ("midnight", "Пеликан-балық", "Үлкен аузы бар тереңсу балығы.", "Балық"),
    ("abyss", "Дамбо сегізаяғы", "Құлаққа ұқсас жүзбеқанаттарымен баяу қозғалады.", "Басаяқты"),
    ("abyss", "Теңіз қияры", "Теңіз түбіндегі шөгінділерді өңдеуге қатысады.", "Омыртқасыз"),
    ("abyss", "Ксенофиофор", "Терең теңіз түбінде кездесетін біржасушалы ағза.", "Біржасушалы"),
    ("hadal", "Мариана ұлу-балығы", "Шыңырау жағдайына бейімделген тереңсу балығы.", "Балық"),
    ("hadal", "Амфипод", "Мариан шұңғымасында кездесетін ұсақ шаянтәрізді.", "Шаянтәрізді"),
    ("hadal", "Бактериялар", "Терең мұхитта химиялық энергияны пайдалана алады.", "Микроағза"),
]

ZONE_FACTS = {
    "sunlight": [
        ("0–200 м", "Жарық мол түсетін қабат. Күн сәулесі фотосинтезге жағдай жасайды."),
        ("Фитопланктон", "Мұхиттағы қоректік тізбектің маңызды негізін құрайды."),
        ("Бай тіршілік", "Киттер, дельфиндер, тасбақалар мен көптеген балықтар осы қабатта кездеседі."),
    ],
    "twilight": [
        ("200–1 000 м", "Күн сәулесі әлсіреп, тереңдеген сайын қараңғылық қоюланады."),
        ("Өсімдіксіз қабат", "Жарық фотосинтезге жеткіліксіз болғандықтан, мұнда өсімдіктер өспейді."),
        ("Жарқырау", "Кейбір жануарлар биолюминесценция арқылы өз жарығын шығарады."),
    ],
    "midnight": [
        ("1 000–4 000 м", "Күн сәулесі мұнда жетпейді, сондықтан бұл аймақта мәңгі түнек орнаған."),
        ("Жоғары қысым", "Тереңдік артқан сайын судың қысымы да күшейеді."),
        ("Қорек іздеу", "Тұрғындары сирек қорекке бейімделіп, баяу энергия жұмсайды."),
    ],
    "abyss": [
        ("4 000–6 000 м", "Мұхит түбіне жақын жатқан суық әрі қараңғы аймақ."),
        ("Тұңғиық жазығы", "Кең жазықтар мен мұхит түбіндегі шөгінділер осы қабатқа тән."),
        ("Ерекше тіршілік", "Кей ағзалар күн сәулесінсіз, теңіз түбіндегі қорекке сүйеніп өмір сүреді."),
    ],
    "hadal": [
        ("6 000–11 000 м", "Мұхиттың ең терең науалары мен Мариан шұңғымасын қамтиды."),
        ("Қатты қысым", "Бұл тереңдіктегі қысым жер бетімен салыстырғанда орасан жоғары."),
        ("Бейімделген ағзалар", "Шыңырауда тіршілік ететін жануарлар суық пен қысымға бейімделген."),
    ],
}

HUMAN_CONDITIONS = {
    "sunlight": {
        "pressure": "Абсолюттік қысым шамамен 1–21 атмосфера. Мұхитта қысым әр 10 метр сайын шамамен 1 атмосфераға артады.",
        "body_reaction": "Қысым өзгергенде құлаққа әсер етуі мүмкін. Терең еркін сүңгуде өкпе көлемі азайып, өкпе жарақатының қаупі артады; жүрек соғысы баяулауы мүмкін.",
        "protection": "Дайындық пен тереңдікке сәйкес сүңгуір жабдығы қажет. Қарапайым маска қысымнан қорғамайды.",
        "takeaway": "Жарық бар, бірақ тереңдеген сайын қысым да өседі. Терең сүңгу — арнайы дайындықты қажет ететін іс.",
    },
    "twilight": {
        "pressure": "Абсолюттік қысым шамамен 21–101 атмосфера (200–1 000 м). Нақты қысым тереңдікке байланысты.",
        "body_reaction": "Жарық тез азаяды, фотосинтез жүрмейді. Суық пен қысым күшейеді; қысымды тыныс алу газымен сүңгуде азот наркозы қаупі болуы мүмкін.",
        "protection": "Адам тек осы тереңдікке есептелген, қысымнан қорғайтын герметикалық аппаратта бола алады.",
        "takeaway": "Бұл — көмескі жарық пен жоғары қысым аймағы. Қарапайым сүңгуір жабдығы мұнда жарамайды.",
    },
    "midnight": {
        "pressure": "Абсолюттік қысым шамамен 101–401 атмосфера (1 000–4 000 м).",
        "body_reaction": "Күн сәулесі жетпейді; мұхит суық әрі қараңғы. Адам қоршаған ортаны тек аппарат шамымен көре алады.",
        "protection": "Адам мінетін тереңсу аппаратының берік, герметикалық кабинасы мен тіршілікті қамтамасыз ету жүйесі керек.",
        "takeaway": "Адам сыртқы қысымды кабина ішінде сезбейді — оны аппараттың корпусы көтереді.",
    },
    "abyss": {
        "pressure": "Абсолюттік қысым шамамен 401–601 атмосфера (4 000–6 000 м).",
        "body_reaction": "Бұл тереңдікте қараңғылық, суық және орасан қысым болады. Адам аппарат ішінде жарық пен байланыс жүйесіне тәуелді.",
        "protection": "Тек осы қысымға есептелген арнайы тереңсу аппараты мен зерттеу кемесінің қолдауы қажет.",
        "takeaway": "Мұхит түбіне жақын аймаққа арнайы зерттеу аппаратымен ғана баруға болады.",
    },
    "hadal": {
        "pressure": "Абсолюттік қысым шамамен 601–1 101 атмосфера (6 000–11 000 м).",
        "body_reaction": "Сыртта жарық жоқ, суық және қысым өте жоғары. Қорғалған кабинада адам аппараттың құралдары арқылы ғана бақылайды.",
        "protection": "Хадаль тереңдігіне арналған күшейтілген корпус пен автономды тіршілікті қамтамасыз ету жүйесі бар аппарат керек.",
        "takeaway": "Бұл — мұхиттың ең терең қабаты; оған арнайы жасалған аппараттар ғана жетеді.",
    },
}

def initialize():
    with sqlite3.connect(DB) as db:
        db.execute("PRAGMA foreign_keys = ON")
        db.execute("CREATE TABLE IF NOT EXISTS zones (id TEXT PRIMARY KEY, title TEXT NOT NULL, scientific_name TEXT NOT NULL, min_depth INTEGER NOT NULL, max_depth INTEGER NOT NULL, description TEXT NOT NULL)")
        db.execute("CREATE TABLE IF NOT EXISTS species (id INTEGER PRIMARY KEY AUTOINCREMENT, zone_id TEXT NOT NULL REFERENCES zones(id), name TEXT NOT NULL, description TEXT NOT NULL, category TEXT NOT NULL)")
        db.execute("CREATE TABLE IF NOT EXISTS zone_facts (id INTEGER PRIMARY KEY AUTOINCREMENT, zone_id TEXT NOT NULL REFERENCES zones(id), label TEXT NOT NULL, detail TEXT NOT NULL, sort_order INTEGER NOT NULL)")
        db.execute("CREATE TABLE IF NOT EXISTS human_conditions (zone_id TEXT PRIMARY KEY REFERENCES zones(id), environment TEXT NOT NULL DEFAULT '', experience TEXT NOT NULL DEFAULT '', equipment TEXT NOT NULL DEFAULT '', pressure TEXT NOT NULL DEFAULT '', body_reaction TEXT NOT NULL DEFAULT '', protection TEXT NOT NULL DEFAULT '', takeaway TEXT NOT NULL DEFAULT '')")
        db.execute("CREATE TABLE IF NOT EXISTS visitor_entries (id INTEGER PRIMARY KEY AUTOINCREMENT, zone_id TEXT REFERENCES zones(id), visitor_name TEXT NOT NULL DEFAULT '', entry_type TEXT NOT NULL CHECK(entry_type IN ('question','fact')), message TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','published')))")
        columns = {row[1] for row in db.execute("PRAGMA table_info(human_conditions)")}
        for column in ("pressure", "body_reaction", "protection", "takeaway"):
            if column not in columns:
                db.execute(f"ALTER TABLE human_conditions ADD COLUMN {column} TEXT NOT NULL DEFAULT ''")
        if db.execute("SELECT COUNT(*) FROM zones").fetchone()[0] == 0:
            db.executemany("INSERT INTO zones VALUES (?, ?, ?, ?, ?, ?)", ZONES)
            db.executemany("INSERT INTO species (zone_id, name, description, category) VALUES (?, ?, ?, ?)", SPECIES)
        if db.execute("SELECT COUNT(*) FROM zone_facts").fetchone()[0] == 0:
            for zone_id, facts in ZONE_FACTS.items():
                db.executemany("INSERT INTO zone_facts (zone_id, label, detail, sort_order) VALUES (?, ?, ?, ?)", [(zone_id, label, detail, order) for order, (label, detail) in enumerate(facts)])
        for zone_id, condition in HUMAN_CONDITIONS.items():
            db.execute("""INSERT INTO human_conditions (zone_id, environment, experience, equipment, pressure, body_reaction, protection, takeaway)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(zone_id) DO UPDATE SET
                environment=excluded.environment, experience=excluded.experience, equipment=excluded.equipment,
                pressure=excluded.pressure, body_reaction=excluded.body_reaction,
                protection=excluded.protection, takeaway=excluded.takeaway""",
                (zone_id, condition["body_reaction"], condition["body_reaction"], condition["protection"], condition["pressure"], condition["body_reaction"], condition["protection"], condition["takeaway"]))

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/database":
            if not self.is_admin():
                self.send_json({"error": "Әкімші ретінде кіріңіз."}, 401)
                return
            with sqlite3.connect(DB) as db:
                db.row_factory = sqlite3.Row
                tables = {
                    "zones": [dict(row) for row in db.execute("SELECT * FROM zones ORDER BY min_depth")],
                    "species": [dict(row) for row in db.execute("SELECT s.*, z.title AS zone_title FROM species s JOIN zones z ON z.id=s.zone_id ORDER BY z.min_depth, s.name")],
                    "facts": [dict(row) for row in db.execute("SELECT f.*, z.title AS zone_title FROM zone_facts f JOIN zones z ON z.id=f.zone_id ORDER BY z.min_depth, f.sort_order")],
                    "conditions": [dict(row) for row in db.execute("SELECT h.*, z.title AS zone_title FROM human_conditions h JOIN zones z ON z.id=h.zone_id ORDER BY z.min_depth")],
                    "visitor_entries": [dict(row) for row in db.execute("SELECT e.*, z.title AS zone_title FROM visitor_entries e LEFT JOIN zones z ON z.id=e.zone_id ORDER BY e.created_at DESC, e.id DESC")],
                }
                self.send_json(tables)
            return
        if parsed.path == "/api/community":
            with sqlite3.connect(DB) as db:
                db.row_factory = sqlite3.Row
                rows = db.execute("SELECT e.id, e.entry_type, e.message, e.created_at, z.title AS zone_title FROM visitor_entries e LEFT JOIN zones z ON z.id=e.zone_id WHERE e.status='published' ORDER BY e.created_at DESC, e.id DESC").fetchall()
                self.send_json([dict(row) for row in rows])
            return
        if parsed.path == "/admin_password.txt":
            self.send_error(404)
            return
        if parsed.path == "/api/zones":
            with sqlite3.connect(DB) as db:
                db.row_factory = sqlite3.Row
                rows = db.execute("SELECT z.*, COUNT(s.id) AS species_count FROM zones z LEFT JOIN species s ON s.zone_id=z.id GROUP BY z.id ORDER BY z.min_depth").fetchall()
                result = []
                for row in rows:
                    zone = dict(row)
                    zone["facts"] = [dict(fact) for fact in db.execute("SELECT label, detail FROM zone_facts WHERE zone_id=? ORDER BY sort_order", (zone["id"],))]
                    condition = db.execute("SELECT pressure, body_reaction, protection, takeaway FROM human_conditions WHERE zone_id=?", (zone["id"],)).fetchone()
                    zone["human_condition"] = dict(condition) if condition else None
                    result.append(zone)
                self.send_json(result)
            return
        if parsed.path == "/api/species":
            params = parse_qs(parsed.query)
            zone_id = params.get("zone", [""])[0]
            search = params.get("q", [""])[0]
            with sqlite3.connect(DB) as db:
                db.row_factory = sqlite3.Row
                rows = db.execute("SELECT s.*, z.title AS zone_title FROM species s JOIN zones z ON z.id=s.zone_id WHERE (?='' OR s.zone_id=?) AND (s.name LIKE ? OR s.description LIKE ? OR s.category LIKE ?) ORDER BY s.name", (zone_id, zone_id, f"%{search}%", f"%{search}%", f"%{search}%")).fetchall()
                self.send_json([dict(row) for row in rows])
            return
        if parsed.path == "/":
            self.path = "/index.html"
        elif parsed.path == "/zones":
            self.send_response(302)
            self.send_header("Location", "/#zone-sections")
            self.end_headers()
            return
        elif parsed.path == "/database":
            self.path = "/database.html"
        elif parsed.path == "/feedback":
            self.send_response(302)
            self.send_header("Location", "/database.html#entries")
            self.end_headers()
            return
        return super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/admin/login":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                item = json.loads(self.rfile.read(length).decode("utf-8"))
            except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
                self.send_json({"error": "Құпиясөзді енгізіңіз."}, 400)
                return
            if not secrets.compare_digest(str(item.get("password", "")), get_admin_password()):
                self.send_json({"error": "Құпиясөз сәйкес келмеді."}, 401)
                return
            token = secrets.token_urlsafe(32)
            ADMIN_SESSIONS.add(token)
            self.send_json({"ok": True}, headers={"Set-Cookie": f"ocean_admin={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=86400"})
            return
        if parsed.path == "/api/admin/logout":
            ADMIN_SESSIONS.discard(self.admin_token())
            self.send_json({"ok": True}, headers={"Set-Cookie": "ocean_admin=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0"})
            return
        if parsed.path == "/api/entries":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0 or length > 6000:
                    self.send_json({"error": "Өтінім көлемі дұрыс емес."}, 400)
                    return
                item = json.loads(self.rfile.read(length).decode("utf-8"))
                entry_type = item.get("entry_type", "")
                message = str(item.get("message", "")).strip()
                visitor_name = str(item.get("visitor_name", "")).strip()[:60]
                zone_id = item.get("zone_id") or None
                if entry_type not in ("question", "fact") or len(message) < 8 or len(message) > 800:
                    self.send_json({"error": "Сұрағыңызды немесе ұсынысыңызды 8–800 таңба аралығында жазыңыз."}, 400)
                    return
                with sqlite3.connect(DB) as db:
                    if zone_id and not db.execute("SELECT 1 FROM zones WHERE id=?", (zone_id,)).fetchone():
                        self.send_json({"error": "Аймақ табылмады."}, 400)
                        return
                    cursor = db.execute("INSERT INTO visitor_entries (zone_id, visitor_name, entry_type, message) VALUES (?, ?, ?, ?)", (zone_id, visitor_name, entry_type, message))
                    entry_id = cursor.lastrowid
                self.send_json({"id": entry_id, "status": "pending", "message": "Жазба тексеруге жіберілді."}, 201)
            except (UnicodeDecodeError, json.JSONDecodeError, AttributeError, TypeError):
                self.send_json({"error": "Өтінім пішімі дұрыс емес."}, 400)
            return
        parts = parsed.path.strip("/").split("/")
        if len(parts) == 4 and parts[:2] == ["api", "entries"] and parts[3] == "publish":
            if not self.is_admin():
                self.send_json({"error": "Әкімші ретінде кіріңіз."}, 401)
                return
            try:
                entry_id = int(parts[2])
            except ValueError:
                self.send_json({"error": "Жазба табылмады."}, 404)
                return
            with sqlite3.connect(DB) as db:
                cursor = db.execute("UPDATE visitor_entries SET status='published' WHERE id=?", (entry_id,))
                if cursor.rowcount == 0:
                    self.send_json({"error": "Жазба табылмады."}, 404)
                    return
            self.send_json({"id": entry_id, "status": "published"})
            return
        self.send_json({"error": "API endpoint табылмады."}, 404)

    def admin_token(self):
        for cookie in self.headers.get("Cookie", "").split(";"):
            name, separator, value = cookie.strip().partition("=")
            if separator and name == "ocean_admin":
                return value
        return ""

    def is_admin(self):
        token = self.admin_token()
        return bool(token) and token in ADMIN_SESSIONS

    def send_json(self, data, status=200, headers=None):
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(payload)

if __name__ == "__main__":
    initialize()
    admin_password = get_admin_password()
    requested_port = os.environ.get("OCEAN_PORT")
    ports = [int(requested_port)] if requested_port else [8000, 8080, 5500, 0]
    server = None
    for port in ports:
        try:
            server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
            break
        except OSError as error:
            if port == ports[-1]:
                raise
            print(f"Порт {port} недоступен ({error}); пробую другой…")
    print(f"Сайт запущен: http://127.0.0.1:{server.server_port}")
    print(f"Входящие вопросы: http://127.0.0.1:{server.server_port}/feedback")
    print(f"Пароль для просмотра: {admin_password}")
    server.serve_forever()
