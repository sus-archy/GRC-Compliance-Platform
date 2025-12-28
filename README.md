# GRC Database Seeder and Platform

This project includes a script to seed a SQLite database with data from an Excel file containing Common Controls Framework (CCF) information, and a Streamlit web app to view and interact with the data.

## Requirements

- Python 3.8+
- Dependencies: `pip install -r requirements.txt`

## Seeding the Database

```bash
python seed_xls.py [--excel EXCEL_FILE] [--db DB_FILE] [--force]
```

- `--excel`: Path to the Excel file (default: Open_Source_CCF.xls)
- `--db`: Path to the SQLite database (default: grc.db)
- `--force`: Force recreate the database schema

## Running the Web App

```bash
streamlit run app.py
```

The app will be available at http://localhost:8501

## Database Schema

- `domains`: Control domains
- `evidence`: Evidence artifacts
- `controls`: CCF controls
- `control_evidence`: Many-to-many relationship between controls and evidence

## Notes

- The script expects specific sheet names: "CCF Open Source v5", "CCF Control Guidance", "Evidence Request List (ERL)"
- Headers are assumed to be on row 2 for the main sheet; adjust if necessary