"""
main.py — FastAPI додаток В/Ч А7020
Python 3.11+
"""
import io
import os
from contextlib import asynccontextmanager
from pathlib import Path
from datetime import date
from typing import Optional

from fastapi import (
    FastAPI, Depends, HTTPException, UploadFile, File, Query
)
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator

from app.database import init_db, get_conn
from app.security import get_current_user, require_admin, create_user
from app.import_service import import_xls
from app.pdf_gen import generate_pdf, get_versioned_path
from app.export_service import export_registry

# ── Папка для PDF-файлів ──────────────────────────────────────────────────────
PDF_DIR = Path("pdfs")
PDF_DIR.mkdir(exist_ok=True)

# ── Lifespan (замість deprecated @app.on_event) ───────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    with get_conn() as conn:
        if not conn.execute("SELECT 1 FROM users LIMIT 1").fetchone():
            create_user("admin", "admin123", role="admin")
            create_user("operator", "op123", role="operator")
            print("[AUTH] Default users: admin/admin123, operator/op123")
            print("[AUTH] Change passwords after first login!")
    yield

# ── FastAPI ───────────────────────────────────────────────────────────────────
app = FastAPI(title="В/Ч А7020 · СЗЧ", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Статичні файли — монтуються в кінці файлу, після всіх /api/ маршрутів ────
STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR.mkdir(exist_ok=True)



# ══════════════════════════════════════════════════════════════════════════════
# HEALTH
# ══════════════════════════════════════════════════════════════════════════════
@app.get("/api/health")
def health(user=Depends(get_current_user)):
    with get_conn() as conn:
        p_count = conn.execute("SELECT COUNT(*) FROM personnel").fetchone()[0]
        d_count = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    return {
        "status": "ok",
        "personnel_count": p_count,
        "documents_count": d_count,
        "user": user["username"],
        "role": user["role"],
    }


# ══════════════════════════════════════════════════════════════════════════════
# ПОШУК  GET /api/search?mode=pib|phone&q=...
# ══════════════════════════════════════════════════════════════════════════════
@app.get("/api/search")
def search(
    mode: str = Query("pib", pattern="^(pib|phone)$"),
    q: str = Query(..., min_length=1, max_length=200),
    user=Depends(get_current_user),
):
    if mode == "pib":
        sql = """
            SELECT id, pib, phone, rank, birth_date,
                   location, subdivision, arrival_date, enroll_date
            FROM personnel
            WHERE pib LIKE ? COLLATE NOCASE
            ORDER BY pib
            LIMIT 100
        """
        param = f"%{q}%"
    else:
        # Телефон: шукаємо по нормалізованих цифрах
        digits = "".join(c for c in q if c.isdigit())
        if not digits:
            return []
        sql = """
            SELECT id, pib, phone, rank, birth_date,
                   location, subdivision, arrival_date, enroll_date
            FROM personnel
            WHERE phone LIKE ?
            ORDER BY pib
            LIMIT 100
        """
        param = f"%{digits}%"

    with get_conn() as conn:
        rows = conn.execute(sql, (param,)).fetchall()

    return [dict(r) for r in rows]


# ══════════════════════════════════════════════════════════════════════════════
# СТВОРЕННЯ ДОКУМЕНТА  POST /api/documents
# ══════════════════════════════════════════════════════════════════════════════
class CreateDocRequest(BaseModel):
    personnel_id: int
    doc_type: str
    diagnosis: str

    @field_validator("doc_type")
    @classmethod
    def check_doc_type(cls, v):
        allowed = {"аналізи", "влк", "стаціонар", "характеристика", "рапорт"}
        if v not in allowed:
            raise ValueError(f"doc_type має бути одним з: {allowed}")
        return v

    @field_validator("diagnosis")
    @classmethod
    def check_diagnosis(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Діагноз не може бути порожнім")
        if len(v) > 1000:
            raise ValueError("Діагноз не може бути довшим за 1000 символів")
        return v


@app.post("/api/documents", status_code=201)
def create_document(
    req: CreateDocRequest,
    user=Depends(get_current_user),
):
    # Отримати дані особи
    with get_conn() as conn:
        person = conn.execute(
            "SELECT * FROM personnel WHERE id=?", (req.personnel_id,)
        ).fetchone()

    if not person:
        raise HTTPException(404, "Особу не знайдено")

    record = dict(person)

    # Генерація PDF
    try:
        file_path = get_versioned_path(record["pib"], req.doc_type, PDF_DIR)
        generate_pdf(record, req.diagnosis, req.doc_type, file_path)
    except Exception as e:
        raise HTTPException(500, f"Помилка генерації PDF: {e}")

    # Запис в БД — атомарно
    try:
        with get_conn() as conn:
            cursor = conn.execute("""
                INSERT INTO documents
                    (personnel_id, doc_type, diagnosis, file_path, created_by)
                VALUES (?,?,?,?,?)
            """, (
                req.personnel_id,
                req.doc_type,
                req.diagnosis,
                str(file_path),
                user["username"],
            ))
            doc_id = cursor.lastrowid

            conn.execute(
                "INSERT INTO audit_log (action, detail, username) VALUES (?,?,?)",
                (
                    "create_doc",
                    f"id={doc_id} тип={req.doc_type} особа={record['pib']}",
                    user["username"],
                ),
            )
    except Exception as e:
        # Відкат: видалити PDF якщо реєстр не зберігся
        file_path.unlink(missing_ok=True)
        raise HTTPException(500, f"Помилка запису в БД: {e}")

    return {
        "id":         doc_id,
        "file_path":  str(file_path),
        "created_at": date.today().isoformat(),
        "created_by": user["username"],
    }


# ══════════════════════════════════════════════════════════════════════════════
# РЕЄСТР  GET /api/registry?doc_type=аналізи
# ══════════════════════════════════════════════════════════════════════════════
@app.get("/api/registry")
def get_registry(
    doc_type: str = Query(...),
    limit: int = Query(200, le=1000),
    user=Depends(get_current_user),
):
    allowed = {"аналізи", "влк", "стаціонар", "характеристика", "рапорт"}
    if doc_type not in allowed:
        raise HTTPException(400, f"Невідомий тип: {doc_type}")

    with get_conn() as conn:
        rows = conn.execute("""
            SELECT
                d.id,
                p.pib,
                p.phone,
                p.rank,
                p.birth_date,
                p.enroll_date,
                p.location,
                d.diagnosis,
                d.created_at,
                d.file_path,
                d.created_by
            FROM documents d
            JOIN personnel p ON p.id = d.personnel_id
            WHERE d.doc_type = ?
            ORDER BY d.id DESC
            LIMIT ?
        """, (doc_type, limit)).fetchall()

    return [dict(r) for r in rows]


# ══════════════════════════════════════════════════════════════════════════════
# СКАЧАТИ PDF  GET /api/files/{doc_id}
# ══════════════════════════════════════════════════════════════════════════════
@app.get("/api/files/{doc_id}")
def get_file(doc_id: int, user=Depends(get_current_user)):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT file_path, doc_type FROM documents WHERE id=?", (doc_id,)
        ).fetchone()

    if not row:
        raise HTTPException(404, "Документ не знайдено")

    path = Path(row["file_path"])
    if not path.exists():
        raise HTTPException(404, "Файл відсутній на диску")

    return FileResponse(
        path=str(path),
        media_type="application/pdf",
        filename=path.name,
    )


# ══════════════════════════════════════════════════════════════════════════════
# ІМПОРТ XLS  POST /api/import  [admin]
# ══════════════════════════════════════════════════════════════════════════════
@app.post("/api/import")
async def import_file(
    file: UploadFile = File(...),
    user=Depends(require_admin),
):
    if not file.filename.endswith((".xls", ".xlsx")):
        raise HTTPException(400, "Тільки .xls або .xlsx файли")

    MAX_SIZE = 50 * 1024 * 1024  # 50 МБ
    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(413, "Файл занадто великий (макс. 50 МБ)")

    try:
        result = import_xls(io.BytesIO(content), file.filename, user["username"])
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Помилка імпорту: {e}")

    return result


# ══════════════════════════════════════════════════════════════════════════════
# ЕКСПОРТ .XLSX  GET /api/export?doc_type=...  [admin]
# ══════════════════════════════════════════════════════════════════════════════
@app.get("/api/export")
def export(
    doc_type: Optional[str] = Query(None),
    user=Depends(require_admin),
):
    allowed = {"аналізи", "влк", "стаціонар", "характеристика", "рапорт"}
    if doc_type and doc_type not in allowed:
        raise HTTPException(400, f"Невідомий тип: {doc_type}")

    with get_conn() as conn:
        conn.execute(
            "INSERT INTO audit_log (action, detail, username) VALUES (?,?,?)",
            ("export", f"doc_type={doc_type or 'all'}", user["username"]),
        )

    xlsx_bytes = export_registry(doc_type)
    fname = f"реєстр_{doc_type or 'all'}_{date.today()}.xlsx"

    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


# ══════════════════════════════════════════════════════════════════════════════
# АУДИТ  GET /api/audit  [admin]
# ══════════════════════════════════════════════════════════════════════════════
@app.get("/api/audit")
def get_audit(limit: int = Query(100, le=500), user=Depends(require_admin)):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


# ══════════════════════════════════════════════════════════════════════════════
# ДІАГНОСТИКА ІМПОРТУ  POST /api/import/preview  [admin]
# Показує як прочиталися колонки БЕЗ запису в БД
# ══════════════════════════════════════════════════════════════════════════════
@app.post("/api/import/preview")
async def import_preview(
    file: UploadFile = File(...),
    user=Depends(require_admin),
):
    import pandas as pd
    from app.import_service import COL_MAP, _find_col

    content = await file.read()
    try:
        df = pd.read_excel(io.BytesIO(content), sheet_name="СЗЧ", dtype=str, header=0)
    except Exception as e:
        raise HTTPException(400, f"Помилка читання: {e}")

    fields = ["pib", "phone", "rank", "birth_date", "location",
              "subdivision", "arrival_date", "enroll_date"]
    mapping = {f: _find_col(list(df.columns), f) for f in fields}

    # Перший рядок як приклад
    sample = {}
    if len(df) > 0:
        row = df.iloc[0]
        for field, col in mapping.items():
            sample[field] = str(row[col]).strip() if col and col in row.index else "—"

    return {
        "total_columns": len(df.columns),
        "all_columns":   list(df.columns),
        "mapping":       mapping,
        "sample_row":    sample,
        "total_rows":    len(df),
    }


# ── StaticFiles ЗАВЖДИ монтується ПІСЛЯ всіх /api/ маршрутів ─────────────────
# Якщо змонтувати раніше — перехоплює POST/PUT запити і повертає 405
if (STATIC_DIR / "index.html").exists():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
