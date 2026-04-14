import difflib
import os
import re
from pathlib import Path

import pandas as pd
from flask import Flask, abort, make_response, render_template, request, send_from_directory

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / 'uploads'
STATIC_DIR = BASE_DIR / 'static'

DAY_ORDER = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
SCHEDULE_SUFFIX = ' schedule.xlsx'
NAME_KEY = '_name_key'
COLOR_MAP = {
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
    'pam': '#ff008c',
}
HEX_COLOR_RE = re.compile(r'^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$')


def normalize_text(value):
    return ' '.join(str(value).split()).casefold()


def normalize_color(value):
    color = str(value).strip()
    mapped_color = COLOR_MAP.get(normalize_text(color))
    if mapped_color:
        return mapped_color
    if HEX_COLOR_RE.fullmatch(color):
        return color
    app.logger.warning('Ignoring unsupported schedule color: %s', color)
    return '#FFFFFF'


def clean_schedule_value(key, value):
    if value is None or pd.isna(value) or str(value).strip() == '':
        return None
    if key == 'Color':
        return normalize_color(value)
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def get_schedules():
    schedules = []

    if not UPLOAD_DIR.exists():
        app.logger.warning('Upload folder does not exist: %s', UPLOAD_DIR)
        return schedules

    for file_path in UPLOAD_DIR.iterdir():
        if file_path.is_file() and file_path.name.lower().endswith(SCHEDULE_SUFFIX):
            day_part = file_path.name[:-len(SCHEDULE_SUFFIX)].strip().casefold()
            if day_part in DAY_ORDER:
                schedules.append({
                    'day': day_part,
                    'path': file_path,
                })

    schedules.sort(key=lambda x: DAY_ORDER.index(x['day']))
    return schedules


def read_schedule(file_path):
    try:
        df = pd.read_excel(file_path)
    except Exception as exc:
        app.logger.warning('Skipping unreadable schedule %s: %s', file_path, exc)
        return pd.DataFrame()

    if 'Names' not in df.columns:
        app.logger.warning('Skipping schedule without a Names column: %s', file_path)
        return pd.DataFrame()

    df = df.copy()
    df[NAME_KEY] = df['Names'].fillna('').map(normalize_text)
    return df[df[NAME_KEY] != '']


def unique_display_names(loaded_schedules):
    names = {}
    for _, df in loaded_schedules:
        if df.empty or 'Names' not in df.columns or NAME_KEY not in df.columns:
            continue
        for _, row in df[['Names', NAME_KEY]].drop_duplicates(NAME_KEY).iterrows():
            names.setdefault(row[NAME_KEY], row['Names'])
    return names


def choose_name(search_key, names_by_key):
    if search_key in names_by_key:
        return search_key, []

    partial_matches = [key for key in names_by_key if search_key in key]
    if len(partial_matches) == 1:
        return partial_matches[0], []
    if partial_matches:
        return None, [names_by_key[key] for key in partial_matches]

    close_matches = difflib.get_close_matches(search_key, list(names_by_key), n=5, cutoff=0.6)
    if len(close_matches) == 1:
        return close_matches[0], []
    return None, [names_by_key[key] for key in close_matches]


def schedule_for_row(row):
    cleaned_schedule = {}
    for key, value in row.drop(labels=[NAME_KEY]).to_dict().items():
        if key == 'Names':
            continue
        cleaned_value = clean_schedule_value(key, value)
        if cleaned_value is not None:
            cleaned_schedule[key] = cleaned_value
    return cleaned_schedule


def get_pdfs():
    if not STATIC_DIR.exists():
        app.logger.warning('Static folder does not exist: %s', STATIC_DIR)
        return []
    return sorted(
        [file_path.name for file_path in STATIC_DIR.iterdir() if file_path.suffix.casefold() == '.pdf'],
        key=str.casefold,
    )


@app.route('/', methods=['GET', 'POST'])
def index():
    name = None
    suggestions = []
    matched_name = None
    schedules_for_user = []

    all_schedules = get_schedules()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        search_key = normalize_text(name)

        if search_key:
            loaded_schedules = [(sched, read_schedule(sched['path'])) for sched in all_schedules]
            names_by_key = unique_display_names(loaded_schedules)
            selected_key, suggestions = choose_name(search_key, names_by_key)

            if selected_key:
                matched_name = names_by_key[selected_key]
                for sched, df in loaded_schedules:
                    if df.empty or NAME_KEY not in df.columns:
                        continue
                    match = df[df[NAME_KEY] == selected_key]
                    if not match.empty:
                        schedules_for_user.append({
                            'day': sched['day'].capitalize(),
                            'data': schedule_for_row(match.iloc[0]),
                        })

    pdfs = get_pdfs()
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
        resp.set_cookie(
            'has_seen_welcome',
            'true',
            max_age=60 * 60 * 24,
            path='/',
            httponly=True,
            secure=request.is_secure,
            samesite='Lax',
        )

    return resp


@app.route('/pdfs/<path:filename>')
def pdfs(filename):
    if Path(filename).suffix.casefold() != '.pdf':
        abort(404)
    return send_from_directory(STATIC_DIR, filename)


@app.route('/welcome')
def welcome():
    return render_template('welcome.html')


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=os.environ.get('FLASK_DEBUG') == '1', host='0.0.0.0', port=port)
