"""
main.py — Datathon Anonymizer (v2)
-----------------------------------
Endpoints:
  POST   /api/upload              → Valida i carrega el CSV, retorna perfil d'ítems
  POST   /api/classify            → Desa classificació d'ítems (no_id / quasi_id)
  POST   /api/set-generalizations → Desa configuració de generalitzacions
  POST   /api/anonymize           → Aplica tot el procés i retorna mètriques
  GET    /api/download/csv/{sid}  → CSV anonimitzat
  GET    /api/download/report/{sid} → Informe JSON
  DELETE /api/session/{sid}       → Neteja sessió
"""

import io
import uuid
import traceback

import pandas as pd
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.modules.anonymizer import (
    normalize_columns,
    validate_dataframe,
    profile_items,
    compute_date_deltas,
    hash_patient_ids,
    impute_missing_values,
    apply_generalizations,
    apply_k_anonymity,
    compute_metrics,
)
from app.modules.report_md import generate_markdown_report
from app.modules.report_pdf import generate_pdf_report

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(title="Datathon Anonymizer", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

# ── Sessions en memòria ───────────────────────────────────────────────────────
sessions: dict[str, dict] = {}

PREVIEW_ROWS = 8


# ── Models Pydantic ───────────────────────────────────────────────────────────

class ClassifyRequest(BaseModel):
    session_id:      str
    classifications: dict[str, str]  # { item → "quasi_id" | "non_id" }

class GeneralizationConfig(BaseModel):
    session_id:     str
    generalizations: dict  # { item → { type: "bins"|"mapping", ... } }

class AnonymizeRequest(BaseModel):
    session_id: str
    k:          int
    lang:       str = "ca"   # ca | es | en


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_session(sid: str) -> dict:
    if sid not in sessions:
        raise HTTPException(404, detail=f"Sessió '{sid}' no trobada.")
    return sessions[sid]

def _df_preview(df: pd.DataFrame) -> dict:
    preview = df.head(PREVIEW_ROWS).copy().astype(str)
    return {"columns": list(preview.columns), "rows": preview.values.tolist()}


# ── Ruta arrel ────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def root():
    with open("static/index.html", encoding="utf-8") as f:
        return f.read()


# ── Endpoint 1: Càrrega ───────────────────────────────────────────────────────

@app.post("/api/upload")
async def upload(file: UploadFile = File(...)):
    try:
        content = await file.read()
        df = None
        for enc in ("utf-8", "latin-1", "cp1252"):
            try:
                df = pd.read_csv(io.BytesIO(content), encoding=enc, low_memory=False)
                # Normalitzem noms de columnes (strip + lowercase)
                df.columns = [c.strip().lower() for c in df.columns]
                break
            except UnicodeDecodeError:
                continue

        if df is None:
            raise HTTPException(400, "No s'ha pogut llegir el fitxer.")

        # Normalitzem noms de columnes als canònics (pacient, data, item, valor)
        df, col_mapping = normalize_columns(df)

        errors = validate_dataframe(df)
        if errors:
            raise HTTPException(400, detail=" | ".join(errors))

        items    = profile_items(df)
        sid      = str(uuid.uuid4())
        sessions[sid] = {
            "df_original":      df,
            "filename":         file.filename,
            "col_mapping":      col_mapping,
            "date_range":       _date_range(df),
            "items":            items,
            "classifications":  {},
            "generalizations":  {},
            "df_anonymized":    None,
            "metrics":          None,
            "imputation_log":   {},
            "report_md":        None,
            "report_pdf":       None,
        }

        return {
            "session_id":   sid,
            "filename":     file.filename,
            "n_records":    len(df),
            "n_patients":   int(df["pacient"].nunique()),
            "n_items":      len(items),
            "date_range":   _date_range(df),
            "items":        items,
            "preview":      _df_preview(df),
        }

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, detail=str(e))


# ── Endpoint 2: Classificació ─────────────────────────────────────────────────

@app.post("/api/classify")
async def classify(req: ClassifyRequest):
    sess = _get_session(req.session_id)
    sess["classifications"] = req.classifications

    quasi_names = [k for k, v in req.classifications.items() if v == "quasi_id"]
    quasi_profiles = [i for i in sess["items"] if i["name"] in quasi_names]

    return {"ok": True, "quasi_profiles": quasi_profiles}


# ── Endpoint 3: Generalitzacions ──────────────────────────────────────────────

@app.post("/api/set-generalizations")
async def set_generalizations(req: GeneralizationConfig):
    sess = _get_session(req.session_id)
    sess["generalizations"] = req.generalizations
    return {"ok": True}


# ── Endpoint 4: Anonimització ─────────────────────────────────────────────────

@app.post("/api/anonymize")
async def anonymize(req: AnonymizeRequest):
    sess = _get_session(req.session_id)
    if req.k < 2:
        raise HTTPException(400, "k ha de ser ≥ 2.")
    if not sess["classifications"]:
        raise HTTPException(400, "Cal classificar els ítems primer.")

    try:
        df = sess["df_original"].copy()
        classifications  = sess["classifications"]
        generalizations  = sess["generalizations"]
        quasi_id_items   = [k for k, v in classifications.items() if v == "quasi_id"]

        # 1. Delta de dates per pacient
        df_t = compute_date_deltas(df)

        # 2. Aplicar generalitzacions sobre quasi-IDs
        if generalizations:
            df_t = apply_generalizations(df_t, generalizations)

        # 3. Imputar NaN dels quasi-IDs (abans del hash per tenir IDs clars)
        df_t, imputation_log = impute_missing_values(df_t, quasi_id_items)

        # 4. Hash del pacient
        df_t = hash_patient_ids(df_t)

        # 4. K-anonimitat
        k_result = apply_k_anonymity(df_t, quasi_id_items, req.k)

        df_anon = k_result["df_anonymized"]
        sess["df_anonymized"] = df_anon

        # 5. Mètriques comparatives
        metrics = compute_metrics(df_t, df_anon, quasi_id_items, k_result)
        sess["metrics"]         = metrics
        sess["imputation_log"]  = imputation_log

        # 6. Generar informe Markdown
        all_item_names = [i["name"] for i in sess["items"]]
        orig_pacient   = next((orig for orig, can in sess["col_mapping"].items() if can == "pacient"), "patient_id")
        sess["report_md"] = generate_markdown_report(
            lang             = req.lang,
            filename         = sess.get("filename", "dataset.csv"),
            col_mapping      = sess["col_mapping"],
            classifications  = classifications,
            generalizations  = generalizations,
            imputation_log   = imputation_log,
            metrics          = {**metrics, "suppressed_groups": k_result.get("suppressed_groups", [])},
            date_range       = sess.get("date_range", {}),
            all_items        = all_item_names,
            orig_pacient_col = orig_pacient,
        )

        # 7. Generar informe PDF
        sess["report_pdf"] = generate_pdf_report(
            lang             = req.lang,
            filename         = sess.get("filename", "dataset.csv"),
            col_mapping      = sess["col_mapping"],
            classifications  = classifications,
            generalizations  = generalizations,
            imputation_log   = imputation_log,
            metrics          = {**metrics, "suppressed_groups": k_result.get("suppressed_groups", [])},
            date_range       = sess.get("date_range", {}),
            all_items        = all_item_names,
            orig_pacient_col = orig_pacient,
        )

        # Retornem tot (sense DataFrames)
        result = {k: v for k, v in metrics.items() if not isinstance(v, pd.DataFrame)}
        result["imputation_log"] = imputation_log
        return result

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, detail=str(e))


# ── Endpoints de descàrrega ───────────────────────────────────────────────────

@app.get("/api/download/csv/{session_id}")
async def download_csv(session_id: str):
    sess = _get_session(session_id)
    if sess["df_anonymized"] is None:
        raise HTTPException(400, "Cal executar l'anonimització primer.")
    buf = io.StringIO()
    sess["df_anonymized"].to_csv(buf, index=False)
    buf.seek(0)
    fname = sess.get("filename", "dataset").replace(".csv", "")
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{fname}_anonymized.csv"'},
    )

@app.get("/api/download/report/pdf/{session_id}")
async def download_report_pdf(session_id: str):
    """Descarrega l'informe d'anonimització en format PDF."""
    sess = _get_session(session_id)
    if not sess.get("report_pdf"):
        raise HTTPException(400, "Cal executar l'anonimització primer.")
    fname = sess.get("filename", "dataset").replace(".csv", "")
    return StreamingResponse(
        iter([sess["report_pdf"]]),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{fname}_anonymization_report.pdf"'},
    )

@app.get("/api/download/report/md/{session_id}")
async def download_report_md(session_id: str):
    """Descarrega l'informe d'anonimització en format Markdown."""
    sess = _get_session(session_id)
    if not sess.get("report_md"):
        raise HTTPException(400, "Cal executar l'anonimització primer.")
    fname = sess.get("filename", "dataset").replace(".csv", "")
    return StreamingResponse(
        iter([sess["report_md"]]),
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{fname}_anonymization_report.md"'},
    )

@app.get("/api/download/report/{session_id}")
async def download_report(session_id: str):
    import json
    sess = _get_session(session_id)
    if sess["metrics"] is None:
        raise HTTPException(400, "Cal executar l'anonimització primer.")
    report = {
        "session":          session_id,
        "filename":         sess.get("filename"),
        "classifications":  sess["classifications"],
        "generalizations":  sess["generalizations"],
        "metrics":          sess["metrics"],
    }
    return StreamingResponse(
        iter([json.dumps(report, ensure_ascii=False, indent=2)]),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="anonymization_report.json"'},
    )

@app.delete("/api/session/{session_id}")
async def delete_session(session_id: str):
    sessions.pop(session_id, None)
    return {"ok": True}


# ── Helpers interns ───────────────────────────────────────────────────────────

def _date_range(df: pd.DataFrame) -> dict:
    try:
        parsed = pd.to_datetime(df["data"], dayfirst=True, errors="coerce")
        return {"min": str(parsed.min().date()), "max": str(parsed.max().date())}
    except Exception:
        return {"min": None, "max": None}
