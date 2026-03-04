"""
import_service.py — імпорт .xls / .xlsx аркуша СЗЧ
"""
import hashlib
import io
import pandas as pd
from app.database import get_conn

SHEET_NAME = "СЗЧ"

# Очікувані назви колонок → внутрішня назва поля
# Ключі у нижньому регістрі без зайвих пробілів — для нечіткого пошуку
COL_MAP = {
    # П.І.Б.
    "п.і.б.":                           "pib",
    "піб":                              "pib",
    "прізвище":                         "pib",
    "прізвище ім'я по батькові":        "pib",
    "пib":                              "pib",

    # Телефон
    "номер телефону":                   "phone",
    "телефон":                          "phone",
    "номер тел":                        "phone",
    "тел":                              "phone",

    # Звання
    "військове звання":                 "rank",
    "військове зва":                    "rank",
    "звання":                           "rank",

    # Дата народження
    "дата народження":                  "birth_date",
    "дата народжен":                    "birth_date",
    "дата нар":                         "birth_date",
    "народження":                       "birth_date",

    # Розміщення — варіанти написання
    "розміщення о/с":                   "location",
    "розміщена о/с":                    "location",   # з фото
    "розміщено о/с":                    "location",
    "розміщення":                       "location",
    "розміщена":                        "location",
    "розміщеня о/с":                    "location",
    "розміщеня":                        "location",
    "розміщеня о/с":                    "location",
    "розміщення о/с":                   "location",

    # Підрозділ
    "підрозділ":                        "subdivision",
    "підрозд":                          "subdivision",
    "рота":                             "subdivision",

    # Прибув
    "прибув у в/ч":                     "arrival_date",
    "прибув у вч":                      "arrival_date",
    "прибув":                           "arrival_date",
    "дата прибуття":                    "arrival_date",

    # Дата зарахування
    "дата зарахування у в/ч а7020":     "enroll_date",
    "дата зарахування у вч а7020":      "enroll_date",
    "дата зарахування":                 "enroll_date",
    "зарахування":                      "enroll_date",
    "дата зарах":                       "enroll_date",
}


def _find_col(df_cols: list, field: str) -> str | None:
    """Знаходить колонку по нечіткому збігу (trim + lowercase + частковий збіг)."""
    # Нормалізуємо назви колонок з XLS: trim, lowercase, прибираємо зайві пробіли
    normalized = {" ".join(str(c).strip().lower().split()): c for c in df_cols}

    # 1. Пряме співпадіння по COL_MAP
    for norm_key, original in normalized.items():
        if COL_MAP.get(norm_key) == field:
            return original

    # 2. Часткове: назва колонки містить патерн або патерн містить назву колонки
    for norm_key, original in normalized.items():
        for pattern, mapped_field in COL_MAP.items():
            if mapped_field != field:
                continue
            if pattern in norm_key or norm_key in pattern:
                return original
            # Ще агресивніше: перші N символів збігаються
            min_len = min(len(pattern), len(norm_key))
            if min_len >= 5 and pattern[:min_len] == norm_key[:min_len]:
                return original

    return None


def _get_val(row, col_name: str | None) -> str:
    if col_name is None or col_name not in row.index:
        return ""
    val = row[col_name]
    if pd.isna(val):
        return ""
    return str(val).strip()


def _normalize_phone(val: str) -> str:
    return "".join(c for c in val if c.isdigit())


def _normalize_date(val) -> str:
    try:
        ts = pd.to_datetime(val, errors="coerce", dayfirst=True)
        if pd.isna(ts):
            return "Невідомо"
        return ts.strftime("%Y-%m-%d")
    except Exception:
        return "Невідомо"


def _row_hash(pib: str, birth_date: str, phone: str) -> str:
    key = f"{pib}|{birth_date}|{phone}"
    return hashlib.md5(key.encode("utf-8")).hexdigest()


def import_xls(file_bytes, filename: str, username: str) -> dict:
    # ── Читання — всі колонки, без фільтрації ────────────────────────────────
    try:
        df = pd.read_excel(
            file_bytes,
            sheet_name=SHEET_NAME,
            dtype=str,
            header=0,
        )
    except Exception as e:
        raise ValueError(f"Не вдалося прочитати файл: {e}")

    # Логуємо знайдені колонки для діагностики
    print(f"[IMPORT] Знайдено {len(df.columns)} колонок: {list(df.columns[:10])}...")

    # ── Маппінг колонок ───────────────────────────────────────────────────────
    fields = ["pib", "phone", "rank", "birth_date", "location",
              "subdivision", "arrival_date", "enroll_date"]
    col_mapping = {f: _find_col(list(df.columns), f) for f in fields}

    print(f"[IMPORT] Маппінг: { {k: v for k, v in col_mapping.items()} }")

    # Перевірка обов'язкових
    if col_mapping["pib"] is None:
        raise ValueError(
            f"Колонка П.І.Б. не знайдена. Доступні: {list(df.columns[:15])}"
        )

    # ── Нормалізація і UPSERT ─────────────────────────────────────────────────
    inserted = updated = errors = 0

    with get_conn() as conn:
        for _, row in df.iterrows():
            try:
                pib = _get_val(row, col_mapping["pib"])
                pib = " ".join(pib.split())
                if not pib:
                    continue

                phone      = _normalize_phone(_get_val(row, col_mapping["phone"]))
                rank       = _get_val(row, col_mapping["rank"])
                birth_date = _normalize_date(_get_val(row, col_mapping["birth_date"]))
                location   = _get_val(row, col_mapping["location"])
                subdivision= _get_val(row, col_mapping["subdivision"])
                arrival_date = _normalize_date(_get_val(row, col_mapping["arrival_date"]))
                enroll_date  = _normalize_date(_get_val(row, col_mapping["enroll_date"]))

                src_hash = _row_hash(pib, birth_date, phone)

                existing = conn.execute(
                    "SELECT id FROM personnel WHERE source_hash=?", (src_hash,)
                ).fetchone()

                if existing:
                    conn.execute("""
                        UPDATE personnel SET
                            pib=?, phone=?, rank=?, birth_date=?,
                            location=?, subdivision=?, arrival_date=?, enroll_date=?
                        WHERE source_hash=?
                    """, (pib, phone, rank, birth_date,
                          location, subdivision, arrival_date, enroll_date, src_hash))
                    updated += 1
                else:
                    conn.execute("""
                        INSERT INTO personnel
                            (pib, phone, rank, birth_date, location,
                             subdivision, arrival_date, enroll_date, source_hash)
                        VALUES (?,?,?,?,?,?,?,?,?)
                    """, (pib, phone, rank, birth_date,
                          location, subdivision, arrival_date, enroll_date, src_hash))
                    inserted += 1

            except Exception as e:
                errors += 1
                print(f"[IMPORT] Помилка рядка: {e}")

        conn.execute(
            "INSERT INTO audit_log (action, detail, username) VALUES (?,?,?)",
            ("import", f"{filename}: +{inserted} нових, ~{updated} оновлено, {errors} помилок", username),
        )

    print(f"[IMPORT] Готово: +{inserted} нових, ~{updated} оновлено, {errors} помилок")
    return {"inserted": inserted, "updated": updated, "skipped": 0, "errors": errors}
