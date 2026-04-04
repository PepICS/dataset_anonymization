"""
main.py — Datathon Anonymizer v2
---------------------------------
Endpoints:
  POST   /api/upload              → Càrrega CSV, normalització i perfilat
  POST   /api/classify            → Classificació d'ítems (quasi_id / non_id)
  POST   /api/set-generalizations → Configuració de generalitzacions
  POST   /api/simulate-k          → Simulació de supressió per k=2..5
  POST   /api/anonymize           → Procés complet + generació d'informes
  GET    /api/download/csv/{sid}       → CSV anonimitzat
  GET    /api/download/report/html/{sid} → Informe HTML
  GET    /api/download/report/md/{sid}   → Informe Markdown
  GET    /api/download/report/{sid}      → Informe JSON
  DELETE /api/session/{sid}        → Neteja sessió
"""

import io
import json
import uuid
import traceback
from datetime import datetime, timezone

import pandas as pd
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.modules.anonymizer import (
    normalize_columns, validate_dataframe, profile_items,
    compute_date_deltas, hash_patient_ids, impute_missing_values,
    apply_generalizations, apply_k_anonymity, compute_metrics,
)
from app.modules.report_md   import generate_markdown_report
from app.modules.report_html import generate_html_report

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(title="Datathon Anonymizer", version="2.0.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory="static"), name="static")

sessions: dict[str, dict] = {}
PREVIEW_ROWS = 8

_REPORT_TITLES = {
    "ca": "Informe d'Anonimització de Dades Clíniques",
    "es": "Informe de Anonimización de Datos Clínicos",
    "en": "Clinical Data Anonymization Report",
}
_CONFIDENTIAL = {
    "ca": "DOCUMENT CONFIDENCIAL · ÚS INTERN",
    "es": "DOCUMENTO CONFIDENCIAL · USO INTERNO",
    "en": "CONFIDENTIAL DOCUMENT · INTERNAL USE",
}


# ── Models Pydantic ───────────────────────────────────────────────────────────

class ClassifyRequest(BaseModel):
    session_id:      str
    classifications: dict[str, str]

class GeneralizationConfig(BaseModel):
    session_id:      str
    generalizations: dict

class AnonymizeRequest(BaseModel):
    session_id: str
    k:          int
    lang:       str = "ca"

class SimulateKRequest(BaseModel):
    session_id: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_session(sid: str) -> dict:
    if sid not in sessions:
        raise HTTPException(404, detail=f"Sessió '{sid}' no trobada.")
    return sessions[sid]

def _df_preview(df: pd.DataFrame) -> dict:
    preview = df.head(PREVIEW_ROWS).copy().astype(str)
    return {"columns": list(preview.columns), "rows": preview.values.tolist()}

def _date_range(df: pd.DataFrame) -> dict:
    try:
        parsed = pd.to_datetime(df["data"], errors="coerce")
        return {"min": str(parsed.min().date()), "max": str(parsed.max().date())}
    except Exception:
        return {"min": None, "max": None}

def _stream(content: str | bytes, media_type: str, filename: str) -> StreamingResponse:
    return StreamingResponse(
        iter([content]),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


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
                df.columns = [c.strip().lower() for c in df.columns]
                break
            except UnicodeDecodeError:
                continue
        if df is None:
            raise HTTPException(400, "No s'ha pogut llegir el fitxer.")

        df, col_mapping = normalize_columns(df)
        errors = validate_dataframe(df)
        if errors:
            raise HTTPException(400, detail=" | ".join(errors))

        items  = profile_items(df)
        dr     = _date_range(df)
        sid    = str(uuid.uuid4())
        sessions[sid] = {
            "df_original":     df,
            "filename":        file.filename,
            "col_mapping":     col_mapping,
            "date_range":      dr,
            "items":           items,
            "classifications": {},
            "generalizations": {},
            "df_anonymized":   None,
            "metrics":         None,
            "imputation_log":  {},
            "report_md":       None,
            "report_html":     None,
        }
        return {
            "session_id": sid,
            "filename":   file.filename,
            "n_records":  len(df),
            "n_patients": int(df["pacient"].nunique()),
            "n_items":    len(items),
            "date_range": dr,
            "items":      items,
            "preview":    _df_preview(df),
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
    quasi = [k for k, v in req.classifications.items() if v == "quasi_id"]
    return {"ok": True, "quasi_profiles": [i for i in sess["items"] if i["name"] in quasi]}


# ── Endpoint 3: Generalitzacions ──────────────────────────────────────────────

@app.post("/api/set-generalizations")
async def set_generalizations(req: GeneralizationConfig):
    _get_session(req.session_id)["generalizations"] = req.generalizations
    return {"ok": True}


# ── Endpoint 4: Simulació de k ────────────────────────────────────────────────

@app.post("/api/simulate-k")
async def simulate_k(req: SimulateKRequest):
    sess = _get_session(req.session_id)
    if not sess["classifications"]:
        raise HTTPException(400, "Cal classificar els ítems primer.")
    try:
        quasi = [k for k, v in sess["classifications"].items() if v == "quasi_id"]
        df_t  = compute_date_deltas(sess["df_original"])
        if sess["generalizations"]:
            df_t = apply_generalizations(df_t, sess["generalizations"])
        df_t, _ = impute_missing_values(df_t, quasi)

        simulations = []
        for k in [2, 3, 4, 5]:
            kr = apply_k_anonymity(df_t, quasi, k)
            eq = kr["equivalence_classes"]
            simulations.append({
                "k":                k,
                "n_patients_orig":  kr["n_patients_orig"],
                "n_patients_final": kr["n_patients_final"],
                "n_suppressed":     kr["n_suppressed_patients"],
                "pct_suppressed":   kr["pct_suppressed"],
                "n_groups":         eq.get("total_groups", 0),
                "conforming_groups":eq.get("conforming_groups", 0),
                "size_distribution":eq.get("size_distribution", {}),
            })
        return {"quasi_ids": quasi, "simulations": simulations}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, detail=str(e))


# ── Endpoint 5: Anonimització ─────────────────────────────────────────────────

@app.post("/api/anonymize")
async def anonymize(req: AnonymizeRequest):
    sess = _get_session(req.session_id)
    if req.k < 2:
        raise HTTPException(400, "k ha de ser ≥ 2.")
    if not sess["classifications"]:
        raise HTTPException(400, "Cal classificar els ítems primer.")
    try:
        classifications = sess["classifications"]
        generalizations = sess["generalizations"]
        quasi           = [k for k, v in classifications.items() if v == "quasi_id"]

        df_t = compute_date_deltas(sess["df_original"])
        if generalizations:
            df_t = apply_generalizations(df_t, generalizations)
        df_t, imputation_log = impute_missing_values(df_t, quasi)
        df_t = hash_patient_ids(df_t)

        k_result = apply_k_anonymity(df_t, quasi, req.k)
        df_anon  = k_result["df_anonymized"]
        metrics  = compute_metrics(df_t, df_anon, quasi, k_result)

        sess["df_anonymized"]  = df_anon
        sess["metrics"]        = metrics
        sess["imputation_log"] = imputation_log

        # Generar informes
        now_str      = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        all_items    = [i["name"] for i in sess["items"]]
        orig_pacient = next(
            (o for o, c in sess["col_mapping"].items() if c == "pacient"), "patient_id"
        )
        report_kwargs = dict(
            lang             = req.lang,
            filename         = sess["filename"],
            col_mapping      = sess["col_mapping"],
            classifications  = classifications,
            generalizations  = generalizations,
            imputation_log   = imputation_log,
            metrics          = {**metrics, "suppressed_groups": k_result.get("suppressed_groups", [])},
            date_range       = sess["date_range"],
            all_items        = all_items,
            orig_pacient_col = orig_pacient,
        )
        sess["report_md"]   = generate_markdown_report(**report_kwargs)
        sess["report_html"] = generate_html_report(
            markdown_text      = sess["report_md"],
            title              = _REPORT_TITLES.get(req.lang, _REPORT_TITLES["ca"]),
            filename           = sess["filename"],
            generated_at       = now_str,
            confidential_label = _CONFIDENTIAL.get(req.lang, _CONFIDENTIAL["ca"]),
        )

        result = {k: v for k, v in metrics.items() if not isinstance(v, pd.DataFrame)}
        result["imputation_log"] = imputation_log
        return result

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, detail=str(e))


# ── Descàrregues ──────────────────────────────────────────────────────────────

@app.get("/api/download/csv/{session_id}")
async def download_csv(session_id: str):
    sess = _get_session(session_id)
    if sess["df_anonymized"] is None:
        raise HTTPException(400, "Cal executar l'anonimització primer.")
    buf = io.StringIO()
    sess["df_anonymized"].to_csv(buf, index=False)
    fname = sess["filename"].replace(".csv", "")
    return _stream(buf.getvalue(), "text/csv", f"{fname}_anonymized.csv")

@app.get("/api/download/report/html/{session_id}")
async def download_html(session_id: str):
    sess = _get_session(session_id)
    if not sess.get("report_html"):
        raise HTTPException(400, "Cal executar l'anonimització primer.")
    fname = sess["filename"].replace(".csv", "")
    return _stream(sess["report_html"], "text/html", f"{fname}_report.html")

@app.get("/api/download/report/md/{session_id}")
async def download_md(session_id: str):
    sess = _get_session(session_id)
    if not sess.get("report_md"):
        raise HTTPException(400, "Cal executar l'anonimització primer.")
    fname = sess["filename"].replace(".csv", "")
    return _stream(sess["report_md"], "text/markdown", f"{fname}_report.md")

@app.get("/api/download/report/{session_id}")
async def download_json(session_id: str):
    sess = _get_session(session_id)
    if sess["metrics"] is None:
        raise HTTPException(400, "Cal executar l'anonimització primer.")
    report = {
        "filename":        sess["filename"],
        "classifications": sess["classifications"],
        "generalizations": sess["generalizations"],
        "metrics":         sess["metrics"],
    }
    return _stream(
        json.dumps(report, ensure_ascii=False, indent=2),
        "application/json", "anonymization_report.json",
    )

@app.delete("/api/session/{session_id}")
async def delete_session(session_id: str):
    sessions.pop(session_id, None)
    return {"ok": True}
