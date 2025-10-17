import os
import sys
sys.stdout.flush()
from flask import Flask, render_template, request, send_from_directory, make_response
from nfc_tracking import log_visit, fetch_logs, set_token_active, token_active, ADMIN_TOKEN
from flask import jsonify, abort, make_response
import pandas as pd


import uuid
from nfc_tracking import log_visit, fetch_logs, set_token_active, token_active, ADMIN_TOKEN

@app.route("/log_client", methods=["POST"])
def log_client():
    try:
        data = request.get_json() or {}
    except Exception:
        data = {}
    # generate device id if not present
    device_id = request.cookies.get("nfc_device_id") or str(uuid.uuid4())
    # log visit with client_info
    try:
        log_visit(request, token=request.args.get("nfc") or None, device_id=device_id, client_info=data)
    except Exception as e:
        print("log_client error:", e)
    resp = jsonify({"ok": True, "device_id": device_id})
    # set cookie if not present
    if not request.cookies.get("nfc_device_id"):
        resp.set_cookie("nfc_device_id", device_id, max_age=60*60*24*365, samesite='Lax', path='/')
    return resp

# Simple admin view (protected by ADMIN_TOKEN in header 'X-Admin-Token')
@app.route("/admin/nfc_logs")
def admin_nfc_logs():
    token = request.headers.get("X-Admin-Token") or request.args.get("admin_token")
    if token != ADMIN_TOKEN:
        return abort(401)
    logs = fetch_logs(300)
    # minimal HTML table - you can replace with a template later
    rows = []
    for r in logs:
        ci = r.get("client_info") or {}
        rows.append(f"<tr><td>{r.get('created_at')}</td><td>{r.get('token') or ''}</td><td>{r.get('ip')}</td><td>{r.get('country')}/{r.get('region')}</td><td>{r.get('user_agent')[:120]}</td><td>{ci}</td></tr>")
    html = f"""
    <html><head><title>NFC Logs</title></head><body>
    <h1>NFC Usage Logs</h1>
    <p>Protect this page. Use header X-Admin-Token or ?admin_token=...</p>
    <table border="1" cellpadding="4"><thead><tr><th>Time</th><th>Token</th><th>IP</th><th>Geo</th><th>User-Agent</th><th>Client Info</th></tr></thead>
    <tbody>{''.join(rows)}</tbody></table>
    </body></html>
    """
    return html

# Admin endpoints to toggle token active state
@app.route("/admin/set_token", methods=["POST"])
def admin_set_token():
    token = request.args.get("token") or (request.get_json() or {}).get("token")
    active = request.args.get("active")
    admin_token = request.headers.get("X-Admin-Token") or request.args.get("admin_token")
    if admin_token != ADMIN_TOKEN:
        return abort(401)
    if token is None:
        return jsonify({"error":"missing token"}), 400
    active_flag = True if str(active) in ['1','true','True','yes','y'] else False
    set_token_active(token, active_flag)
    return jsonify({"ok": True, "token": token, "active": active_flag})


app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# EXCEL_FILE = os.path.join(BASE_DIR, 'uploads', 'schedule.xlsx')

import math

import difflib


DAY_ORDER = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']

def get_schedules():
    schedules = []
    upload_folder = os.path.join(BASE_DIR, 'uploads')

    for filename in os.listdir(upload_folder):
        if filename.lower().endswith('schedule.xlsx'):
            day_part = filename.lower().replace(' schedule.xlsx', '').strip()
            if day_part in DAY_ORDER:
                schedules.append({
                    'day': day_part,
                    'path': os.path.join(upload_folder, filename)
                })

    # Sort schedules based on DAY_ORDER
    schedules.sort(key=lambda x: DAY_ORDER.index(x['day']))
    return schedules


@app.route('/', methods=['GET', 'POST'])
def index():
    name = None
    suggestions = []
    matched_name = None
    schedules_for_user = []

    # -- LOG VISIT: try to capture token from query param if present (works if your tags include ?nfc=abc)
    # Also read device cookie if available
    token = request.args.get("nfc") or request.args.get("token")  # common query param names
    device_id = request.cookies.get("nfc_device_id")
    # We DO NOT block here — we just log.
    try:
        # client_info from JS may be posted separately to /log_client; pass None here
        log_visit(request, token=token, device_id=device_id, client_info=None)
    except Exception as e:
        # don't break app if logging fails
        print("Logging error:", e)

    all_schedules = get_schedules()

    if request.method == 'POST':
        name = request.form['name'].strip().lower()

        for sched in all_schedules:
            file_path = sched['path']

            if not os.path.exists(file_path):
                continue

            df = pd.read_excel(file_path)
            df['Name_lower'] = df['Names'].str.strip().str.lower()

            match = df[df['Name_lower'] == name]

            if match.empty:
                partial_match = df[df['Name_lower'].str.contains(name)]
                if not partial_match.empty:
                    if len(partial_match) == 1:
                        match = partial_match
                    else:
                        suggestions += partial_match['Names'].tolist()
                else:
                    all_names = df['Name_lower'].tolist()
                    close_matches = difflib.get_close_matches(name, all_names, n=5, cutoff=0.6)
                    if len(close_matches) == 1:
                        match = df[df['Name_lower'] == close_matches[0]]
                    elif len(close_matches) > 1:
                        for m in close_matches:
                            matches = df[df['Name_lower'] == m]['Names'].tolist()
                            suggestions += matches
                        suggestions = list(set(suggestions))

            if not match.empty:
                matched_name = match.iloc[0]['Names']
                raw_schedule = match.iloc[0].drop(labels=['Name_lower']).to_dict()

                cleaned_schedule = {}
                for key, value in raw_schedule.items():
                    if key == 'Names':
                        continue
                    if value is None or str(value).strip().lower() in ['nan', '']:
                        continue
                    if key == 'Color':
                        value = {
                            'white': '#FFFFFF',
                            'black': '#000000',
                            'magenta': '#bf006e',
                            'light pink': '#ffcbf2',
                            'purple': '#5c32b2',
                            'blue': '#0093e1',
                            'lime green': '#a3e44b',
                            'yellow': '#fde800',
                            'orange': '#ed6b01',
                            'red': '#e30004',
                            'dark green': '#459649',
                            'gold': '#9f8c6c',
                            'silver': '#a9b9c9',
                            'pam':"#ff008c"
                        }.get(str(value).strip().lower(), value)
                    if isinstance(value, float) and value.is_integer():
                        value = int(value)
                    cleaned_schedule[key] = value

                schedules_for_user.append({
                    'day': sched['day'].capitalize(),
                    'data': cleaned_schedule
                })

    pdfs = [f for f in os.listdir('static') if f.endswith('.pdf')]
    has_seen_welcome = request.cookies.get('has_seen_welcome', 'false') == 'true'

    resp = make_response(render_template(
        'index.html',
        name=name,
        matched_name=matched_name,
        schedules_for_user=schedules_for_user,
        pdfs=pdfs,
        suggestions=suggestions,
        show_welcome=not has_seen_welcome
    ))

    if not has_seen_welcome:
        resp.set_cookie('has_seen_welcome', 'true', max_age=60*60*24*1, path='/', samesite='Lax')

    return resp






@app.route('/pdfs/<path:filename>')
def pdfs(filename):
    return send_from_directory('static', filename)

@app.route('/welcome')
def welcome():
    return render_template('welcome.html')


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
