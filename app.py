import os
import sys
sys.stdout.flush()
from flask import Flask, render_template, request, send_from_directory, make_response
import pandas as pd

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EXCEL_FILE = os.path.join(BASE_DIR, 'uploads', 'schedule.xlsx')

import math

import difflib


@app.route('/', methods=['GET', 'POST'])
def index():
    schedule = None
    name = None
    suggestions = []  # NEW: holds possible suggestions
    matched_name = None

    if request.method == 'POST':
        name = request.form['name'].strip().lower()

        if not os.path.exists(EXCEL_FILE):
            print(f"Excel file not found at {EXCEL_FILE}")
            schedule = None
        else:
            df = pd.read_excel(EXCEL_FILE)
            df['Name_lower'] = df['Names'].str.strip().str.lower()

            # Exact match
            match = df[df['Name_lower'] == name]

            if match.empty:
                # Partial match
                partial_match = df[df['Name_lower'].str.contains(name)]
                if not partial_match.empty:
                    if len(partial_match) == 1:
                        match = partial_match
                    else:
                        suggestions = partial_match['Names'].tolist()
                else:
                    # Fuzzy fallback
                    all_names = df['Name_lower'].tolist()
                    close_matches = difflib.get_close_matches(name, all_names, n=5, cutoff=0.6)

                    if len(close_matches) == 1:
                        match = df[df['Name_lower'] == close_matches[0]]
                    elif len(close_matches) > 1:
                        for m in close_matches:
                            matches = df[df['Name_lower'] == m]['Names'].tolist()
                            suggestions.extend(matches)
                        suggestions = list(set(suggestions))



            if not match.empty:
                matched_name = match.iloc[0]['Names']
                raw_schedule = match.iloc[0].drop(labels=['Name_lower']).to_dict()

                cleaned_schedule = {}
                for key, value in raw_schedule.items():
                    if key == 'Names':
                        continue
                    if value is None:
                        continue
                    if isinstance(value, float):
                        if math.isnan(value):
                            continue
                        if value.is_integer():
                            value = int(value)
                    if str(value).strip().lower() == 'nan':
                        continue
                    if str(value).strip() == '':
                        continue
                    cleaned_schedule[key] = value

                schedule = cleaned_schedule

    pdfs = [f for f in os.listdir('static') if f.endswith('.pdf')]
    has_seen_welcome = request.cookies.get('has_seen_welcome', 'false') == 'true'

    resp = make_response(render_template(
        'index.html',
        schedule=schedule,
        name=name,
        matched_name=matched_name,
        pdfs=pdfs,
        suggestions=suggestions,  # Pass to template
        show_welcome=not has_seen_welcome
    ))

    if not has_seen_welcome:
        resp.set_cookie('has_seen_welcome', 'true', max_age=60*60*24*1, path='/', samesite='Lax')

    print(f"Cookie seen? {has_seen_welcome}", flush=True)

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
