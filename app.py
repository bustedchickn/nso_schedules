import os
from flask import Flask, render_template, request, send_from_directory
import pandas as pd

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EXCEL_FILE = os.path.join(BASE_DIR, 'uploads', 'schedule.xlsx')

import math

@app.route('/', methods=['GET', 'POST'])
def index():
    schedule = None
    name = None

    if request.method == 'POST':
        name = request.form['name'].strip().lower()

        if not os.path.exists(EXCEL_FILE):
            print(f"Excel file not found at {EXCEL_FILE}")
            schedule = None
        else:
            df = pd.read_excel(EXCEL_FILE)
            df['Name_lower'] = df['Names'].str.strip().str.lower()
            match = df[df['Name_lower'] == name]

            if not match.empty:
                raw_schedule = match.drop(columns=['Name_lower']).to_dict(orient='records')[0]

                # ✅ Clean the dict
                cleaned_schedule = {}
                for key, value in raw_schedule.items():
                    if key == 'Names':
                        continue  # skip Names key
                    if value is None:
                        continue
                    if isinstance(value, float) and math.isnan(value):
                        continue
                    if str(value).strip().lower() == 'nan':
                        continue
                    if str(value).strip() == '':
                        continue
                    cleaned_schedule[key] = value

                schedule = cleaned_schedule

    pdfs = [f for f in os.listdir('static') if f.endswith('.pdf')]
    return render_template('index.html', schedule=schedule, name=name, pdfs=pdfs)




@app.route('/pdfs/<path:filename>')
def pdfs(filename):
    return send_from_directory('static', filename)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
