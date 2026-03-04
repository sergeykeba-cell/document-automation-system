# Document Automation System

A web-based tool that automates document generation and personnel management for organizations.

## Features
- 📂 **Import large Excel files** – handles datasets with 29,000+ records.
- 🔍 **Real‑time search** – instantly find employees by name, department, or position.
- 📄 **PDF generation** – create multiple types of documents using ReportLab.
- 📋 **Document registry** – keep track of generated documents, export to Excel.
- 🔐 **Role‑based access** – admins and regular users have different permissions.
- 📜 **Audit log** – monitor user actions for security.

## Tech Stack
- **Backend:** Python, FastAPI, SQLite
- **Data processing:** pandas, openpyxl
- **PDF generation:** ReportLab
- **Frontend:** HTML, CSS, JavaScript (vanilla)

## Installation
1. Clone the repository:  
   `git clone https://github.com/sergeykeba-cell/document-automation-system.git`
2. Create a virtual environment and install dependencies:  
   `pip install -r requirements.txt`
3. Run the application:  
   `uvicorn main:app --reload`
4. Open `http://localhost:8000` in your browser.

## Screenshots
*(Add screenshots here – they greatly improve readability!)*

## License
MIT
