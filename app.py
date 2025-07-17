from flask import Flask, render_template, request, send_from_directory
import pandas as pd
import os

app = Flask(__name__)

# Path to your uploaded Excel
EXCEL_FILE = os.path.join('uploads', 'schedule.xlsx')

# Route: Home page with search
@app.route('/', methods=['GET', 'POST'])
def index():
    schedule = None
    name = None

    if request.method == 'POST':
        name = request.form['name'].strip().lower()
        df = pd.read_excel(EXCEL_FILE)

        # Make columns lowercase for matching
        df['Name_lower'] = df['Name'].str.lower()

        match = df[df['Name_lower'] == name]

        if not match.empty:
            schedule = match.drop(columns=['Name_lower']).to_dict(orient='records')[0]

    # Get list of PDFs from static folder
    pdfs = [f for f in os.listdir('static') if f.endswith('.pdf')]

    return render_template('index.html', schedule=schedule, name=name, pdfs=pdfs)


# Serve PDFs from static folder
@app.route('/pdfs/<path:filename>')
def pdfs(filename):
    return send_from_directory('static', filename)


if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
