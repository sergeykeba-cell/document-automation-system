# Document Automation System

A web-based document management system with automated PDF generation,
personnel search, and registry management.

## Features

- 🔍 Real-time personnel search by name or phone number
- 📄 Automated PDF generation (5 document types)
- 📊 Import personnel data from Excel (29,000+ records)
- 🗂️ Document registry with export to .xlsx
- 🔐 Role-based access control (admin / operator)
- 📝 Audit log of all actions

## Tech Stack

- **Backend:** Python 3.11, FastAPI, SQLite
- **Data:** pandas, openpyxl
- **PDF:** ReportLab
- **Frontend:** HTML, CSS, Vanilla JS
- **Auth:** HTTP Basic Auth + bcrypt

## Quick Start

### Requirements
- Python 3.11+

### Windows
\```
start.bat
\```

### Linux / Mac
\```bash
chmod +x start.sh && ./start.sh
\```

Open browser: **http://localhost:8000**

Default credentials:
- `admin` / `admin123` — import, export, audit
- `operator` / `op123` — search and document creation

> ⚠️ Change passwords after first login

## API Endpoints

| Method | URL | Access | Description |
|--------|-----|--------|-------------|
| GET | `/api/health` | all | Status + record count |
| GET | `/api/search?mode=pib\|phone&q=` | all | Search personnel |
| POST | `/api/documents` | all | Create document + PDF |
| GET | `/api/registry?doc_type=` | all | Document registry |
| GET | `/api/files/{doc_id}` | all | Download PDF |
| POST | `/api/import` | admin | Import .xlsx |
| GET | `/api/export?doc_type=` | admin | Export registry |
| GET | `/api/audit` | admin | Action log |

## Project Structure

\```
├── app/
│   ├── main.py            # FastAPI — all endpoints
│   ├── database.py        # SQLite + schema
│   ├── security.py        # Auth + roles
│   ├── import_service.py  # Excel import
│   ├── pdf_gen.py         # PDF generation
│   ├── export_service.py  # Registry export
│   └── static/
│       └── index.html     # Frontend UI
├── pdfs/                  # Generated PDFs
├── requirements.txt
├── start.bat
└── start.sh
\```

## Built With

Developed using [Claude AI](https://claude.ai) as a development tool —
requirements analysis, architecture design, code generation and debugging.
