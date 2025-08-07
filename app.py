import os
import sys
sys.stdout.flush()
from flask import Flask, render_template, request, send_from_directory, make_response
import pandas as pd

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
                            'dark pink': '#bf006e',
                            'light pink': '#ffcbf2',
                            'purple': '#5c32b2',
                            'blue': '#0093e1',
                            'lime': '#a3e44b',
                            'yellow': '#fde800',
                            'orange': '#ed6b01',
                            'red': '#e30004',
                            'dark green': '#459649',
                            'gold': '#9f8c6c',
                            'silver': '#a9b9c9'
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
