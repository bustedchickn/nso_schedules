# NSO Schedules

This is a small Flask app for New Student Orientation schedule lookup. Team members search their name, and the app shows their schedule details from the Excel files in `uploads/`. The home page also lists PDFs from `static/` and displays the check-in QR code.

## Project Structure

```text
nso_schedules/
├── app.py
├── requirements.txt
├── Procfile
├── uploads/
│   ├── monday schedule.xlsx
│   ├── tuesday schedule.xlsx
│   └── friday schedule.xlsx
├── static/
│   ├── checkin_code.png
│   ├── *.pdf
│   ├── style.css
│   └── js/main.js
└── templates/
    ├── index.html
    └── welcome.html
```

## Run Locally

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Start the app:

```powershell
python app.py
```

Open the site at:

```text
http://localhost:5000
```

To enable Flask debug mode locally:

```powershell
$env:FLASK_DEBUG='1'
python app.py
```

## Uploading Schedule Files

Put schedule spreadsheets in:

```text
uploads/
```

The app automatically scans this folder each time the schedule page loads. No code change is needed after adding or replacing a schedule file.

### Schedule File Naming

Schedule files must follow this exact pattern:

```text
<day> schedule.xlsx
```

Use lowercase day names for consistency:

```text
monday schedule.xlsx
tuesday schedule.xlsx
wednesday schedule.xlsx
thursday schedule.xlsx
friday schedule.xlsx
saturday schedule.xlsx
sunday schedule.xlsx
```

Only files ending in ` schedule.xlsx` are treated as schedule files. The day name must be one of:

```text
monday, tuesday, wednesday, thursday, friday, saturday, sunday
```

Examples that will not be loaded:

```text
Monday.xlsx
monday_schedule.xlsx
schedule monday.xlsx
monday schedule.xls
```

## Schedule Spreadsheet Format

Each schedule spreadsheet must include a column named:

```text
Names
```

The `Names` column is used for search. Names are matched case-insensitively, and the app can also suggest close matches.

Every other non-empty column in the matched row is displayed as part of that person's schedule.

Example:

| Names | Color | 8:00 AM | 9:00 AM | 10:00 AM |
| --- | --- | --- | --- | --- |
| Jane Smith | Blue | Check-in | Campus Tour | Mentor Group |
| John Doe | Yellow | Breakfast | Training | Check-in |

### Optional Color Column

If a spreadsheet has a `Color` column, the app uses it as the left border color for that person's schedule cards.

Supported color names:

```text
white
black
magenta
light pink
purple
blue
lime green
yellow
orange
red
dark green
gold
silver
pam
```

Hex colors are also accepted:

```text
#0093e1
#fff
```

Unsupported color values are ignored and shown as white.

## Uploading PDFs

Put PDF files in:

```text
static/
```

Any file ending in `.pdf` inside `static/` is listed on the home page under "Available PDFs". Users can preview PDFs on the page or open them directly.

PDF names are shown using the filename without `.pdf`, so this:

```text
Winter 2026 Maps.pdf
```

appears as:

```text
Winter 2026 Maps
```

## Updating the Check-in Code

Replace this file:

```text
static/checkin_code.png
```

Keep the same filename so the page can find it automatically.

## Deployment Notes

The included `Procfile` is set up for a Gunicorn-based deployment:

```text
web: gunicorn app:app
```

The app reads the port from the `PORT` environment variable when deployed. Locally, it defaults to port `5000`.

## Quick Troubleshooting

If a schedule does not appear:

- Confirm the file is in `uploads/`.
- Confirm the filename matches `<day> schedule.xlsx`.
- Confirm it is an `.xlsx` file, not `.xls` or `.csv`.
- Confirm the spreadsheet has a `Names` column spelled exactly like that.
- Confirm the name row is not blank.

If a PDF does not appear:

- Confirm the file is in `static/`.
- Confirm the file extension is `.pdf`.

If a PDF preview does not load:

- Use the "Open PDF" link on the page.
- Check whether the browser can access the PDF.js CDN.

If the wrong person appears:

- Search the full name from the `Names` column.
- Check for duplicate or very similar names across schedule files.
