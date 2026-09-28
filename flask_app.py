"""WSGI entry point for PythonAnywhere and other Flask-compatible hosts."""

from flask import Flask, jsonify, request, send_from_directory, session, abort
from pathlib import Path
import json
import secrets
import sqlite3

import server as ocean

ROOT = Path(__file__).resolve().parent
ocean.initialize()
app = Flask(__name__, static_folder=None)

secret_file = ROOT / "session_secret.txt"
if not secret_file.exists():
    secret_file.write_text(secrets.token_hex(32), encoding="utf-8")
app.secret_key = secret_file.read_text(encoding="utf-8").strip()
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax", SESSION_COOKIE_SECURE=True)


def admin_required():
    return bool(session.get("ocean_admin"))


def db_rows(query, parameters=()):
    with sqlite3.connect(ocean.DB) as db:
        db.row_factory = sqlite3.Row
        return [dict(row) for row in db.execute(query, parameters)]


@app.get("/")
def home():
    return send_from_directory(ROOT, "index.html")


@app.get("/database")
@app.get("/feedback")
def feedback_page():
    return send_from_directory(ROOT, "database.html")


@app.get("/api/database")
def private_database():
    if not admin_required():
        return jsonify(error="Әкімші ретінде кіріңіз."), 401
    with sqlite3.connect(ocean.DB) as db:
        db.row_factory = sqlite3.Row
        tables = {
            "zones": [dict(row) for row in db.execute("SELECT * FROM zones ORDER BY min_depth")],
            "species": [dict(row) for row in db.execute("SELECT s.*, z.title AS zone_title FROM species s JOIN zones z ON z.id=s.zone_id ORDER BY z.min_depth, s.name")],
            "facts": [dict(row) for row in db.execute("SELECT f.*, z.title AS zone_title FROM zone_facts f JOIN zones z ON z.id=f.zone_id ORDER BY z.min_depth, f.sort_order")],
            "conditions": [dict(row) for row in db.execute("SELECT h.*, z.title AS zone_title FROM human_conditions h JOIN zones z ON z.id=h.zone_id ORDER BY z.min_depth")],
            "visitor_entries": [dict(row) for row in db.execute("SELECT e.*, z.title AS zone_title FROM visitor_entries e LEFT JOIN zones z ON z.id=e.zone_id ORDER BY e.created_at DESC, e.id DESC")],
        }
    return jsonify(tables)


@app.get("/api/community")
def community():
    rows = db_rows("SELECT e.id, e.entry_type, e.message, e.created_at, z.title AS zone_title FROM visitor_entries e LEFT JOIN zones z ON z.id=e.zone_id WHERE e.status='published' ORDER BY e.created_at DESC, e.id DESC")
    return jsonify(rows)


@app.get("/api/zones")
def zones():
    result = db_rows("SELECT z.*, COUNT(s.id) AS species_count FROM zones z LEFT JOIN species s ON s.zone_id=z.id GROUP BY z.id ORDER BY z.min_depth")
    with sqlite3.connect(ocean.DB) as db:
        db.row_factory = sqlite3.Row
        for zone in result:
            zone["facts"] = [dict(row) for row in db.execute("SELECT label, detail FROM zone_facts WHERE zone_id=? ORDER BY sort_order", (zone["id"],))]
            condition = db.execute("SELECT pressure, body_reaction, protection, takeaway FROM human_conditions WHERE zone_id=?", (zone["id"],)).fetchone()
            zone["human_condition"] = dict(condition) if condition else None
    return jsonify(result)


@app.get("/api/species")
def species():
    zone_id = request.args.get("zone", "")
    search = request.args.get("q", "")
    rows = db_rows("SELECT s.*, z.title AS zone_title FROM species s JOIN zones z ON z.id=s.zone_id WHERE (?='' OR s.zone_id=?) AND (s.name LIKE ? OR s.description LIKE ? OR s.category LIKE ?) ORDER BY s.name", (zone_id, zone_id, f"%{search}%", f"%{search}%", f"%{search}%"))
    return jsonify(rows)


@app.post("/api/admin/login")
def admin_login():
    item = request.get_json(silent=True) or {}
    supplied = str(item.get("password", ""))
    if not secrets.compare_digest(supplied, ocean.get_admin_password()):
        return jsonify(error="Құпиясөз сәйкес келмеді."), 401
    session["ocean_admin"] = True
    return jsonify(ok=True)


@app.post("/api/admin/logout")
def admin_logout():
    session.clear()
    return jsonify(ok=True)


@app.post("/api/entries")
def create_entry():
    item = request.get_json(silent=True) or {}
    entry_type = item.get("entry_type", "")
    message = str(item.get("message", "")).strip()
    visitor_name = str(item.get("visitor_name", "")).strip()[:60]
    zone_id = item.get("zone_id") or None
    if entry_type not in ("question", "fact") or not 8 <= len(message) <= 800:
        return jsonify(error="Сұрағыңызды немесе ұсынысыңызды 8–800 таңба аралығында жазыңыз."), 400
    with sqlite3.connect(ocean.DB) as db:
        if zone_id and not db.execute("SELECT 1 FROM zones WHERE id=?", (zone_id,)).fetchone():
            return jsonify(error="Аймақ табылмады."), 400
        cursor = db.execute("INSERT INTO visitor_entries (zone_id, visitor_name, entry_type, message) VALUES (?, ?, ?, ?)", (zone_id, visitor_name, entry_type, message))
        entry_id = cursor.lastrowid
    return jsonify(id=entry_id, status="pending", message="Жазба тексеруге жіберілді."), 201


@app.post("/api/entries/<int:entry_id>/publish")
def publish_entry(entry_id):
    if not admin_required():
        return jsonify(error="Әкімші ретінде кіріңіз."), 401
    with sqlite3.connect(ocean.DB) as db:
        cursor = db.execute("UPDATE visitor_entries SET status='published' WHERE id=?", (entry_id,))
        if cursor.rowcount == 0:
            return jsonify(error="Жазба табылмады."), 404
    return jsonify(id=entry_id, status="published")


@app.get("/<path:filename>")
def public_files(filename):
    allowed = {".css", ".js", ".png", ".jpg", ".jpeg", ".svg", ".webp", ".ico"}
    path = Path(filename)
    if path.suffix.lower() not in allowed or ".." in path.parts:
        abort(404)
    return send_from_directory(ROOT, filename)
