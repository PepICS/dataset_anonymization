"""
main.py — Datathon Anonymizer v3
---------------------------------
Endpoints:
  POST   /api/upload              → Càrrega de múltiples CSVs, normalització i perfilat
  POST   /api/classify            → Classificació d'ítems (quasi_id / non_id)
  POST   /api/set-generalizations → Configuració de generalitzacions
  POST   /api/simulate-k          → Simulació de supressió per k=2..5
  POST   /api/anonymize           → Procés complet + generació d'informes
  GET    /api/download/csv/{sid}       → ZIP amb un CSV anonimitzat per fitxer original
  GET    /api/download/report/html/{sid} → Informe HTML
  GET    /api/download/report/md/{sid}   → Informe Markdown
  GET    /api/download/report/{sid}      → Informe JSON
  DELETE /api/session/{sid}        → Neteja sessió
"""

import io
import json
import uuid
import zipfile
import traceback
from datetime import datetime, timezone
from typing import List

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
    detect_date_format, DATE_FORMATS,
)
from app.modules.report_md   import generate_markdown_report
from app.modules.report_html import generate_html_report

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(title="Datathon Anonymizer", version="3.0.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory="static"), name="static")

sessions: dict[str, dict] = {}
PREVIEW_ROWS = 8
_SOURCE_COL  = "_source_file"   # columna interna que recorda l'origen de cada fila

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
    lang:       str = "es"

class SimulateKRequest(BaseModel):
    session_id: str

class DateFormatRequest(BaseModel):
    session_id:  str
    date_format: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_session(sid: str) -> dict:
    if sid not in sessions:
        raise HTTPException(404, detail=f"Sessió '{sid}' no trobada.")
    return sessions[sid]

def _df_preview(df: pd.DataFrame) -> dict:
    cols = [c for c in df.columns if c != _SOURCE_COL]
    preview = df[cols].head(PREVIEW_ROWS).copy().astype(str)
    return {"columns": list(preview.columns), "rows": preview.values.tolist()}

def _date_range(df: pd.DataFrame, date_format: str = "iso") -> dict:
    try:
        from app.modules.anonymizer import _parse_dates
        parsed = _parse_dates(df["data"], date_format)
        if parsed.notna().sum() == 0:
            return {"min": None, "max": None}
        return {"min": str(parsed.min().date()), "max": str(parsed.max().date())}
    except Exception:
        return {"min": None, "max": None}

def _read_csv(content: bytes) -> pd.DataFrame:
    """Llegeix un CSV provant diverses codificacions."""
    for enc in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
        try:
            df = pd.read_csv(io.BytesIO(content), encoding=enc, low_memory=False)
            df.columns = [c.strip().lower() for c in df.columns]
            return df
        except UnicodeDecodeError:
            continue
    raise ValueError("No s'ha pogut llegir el fitxer (encoding no reconegut).")

def _stream(content: str | bytes, media_type: str, filename: str) -> StreamingResponse:
    return StreamingResponse(
        iter([content]),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

def _build_zip(csv_map: dict[str, str]) -> bytes:
    """Construeix un ZIP en memòria amb un CSV per entrada del dict."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for fname, csv_content in csv_map.items():
            zf.writestr(fname, csv_content)
    return buf.getvalue()


# ── Ruta arrel ────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def root():
    with open("static/index.html", encoding="utf-8") as f:
        return f.read()


# ── Endpoint 1: Càrrega (múltiples fitxers) ───────────────────────────────────

@app.post("/api/upload")
async def upload(files: List[UploadFile] = File(...)):
    """
    Accepta un o més fitxers CSV en format llarg estàndard (4 columnes).
    Els concatena internament afegint una columna '_source_file' per
    identificar l'origen de cada fila. El perfilat d'ítems és global
    sobre el dataset combinat.
    """
    try:
        if not files:
            raise HTTPException(400, "Cal adjuntar almenys un fitxer CSV.")

        dfs        = []
        filenames  = []
        col_mapping_global = {}

        for upload_file in files:
            content = await upload_file.read()
            df_raw  = _read_csv(content)
            df_raw, col_mapping = normalize_columns(df_raw)

            errors = validate_dataframe(df_raw)
            if errors:
                raise HTTPException(
                    400,
                    detail=f"Fitxer '{upload_file.filename}': {' | '.join(errors)}"
                )

            df_raw[_SOURCE_COL] = upload_file.filename
            dfs.append(df_raw)
            filenames.append(upload_file.filename)

            # Merge col_mapping (el primer fitxer que mapeja una columna és el referent)
            for orig, canon in col_mapping.items():
                if canon not in col_mapping_global.values():
                    col_mapping_global[orig] = canon

        # Dataset combinat
        df = pd.concat(dfs, ignore_index=True)

        # ── Diagnòstic de relació entre fitxers ───────────────────────────────
        # Es retorna al frontend perquè l'usuari pugui confirmar (quan N>1)
        # si els fitxers pertanyen al mateix dataset o són datasets independents.
        per_file_stats = []
        per_file_patient_sets: list[set] = []
        per_file_item_sets:    list[set] = []
        for raw_df, fname in zip(dfs, filenames):
            pset = set(raw_df["pacient"].dropna().astype(str).unique())
            iset = set(raw_df["item"].dropna().astype(str).unique())
            per_file_patient_sets.append(pset)
            per_file_item_sets.append(iset)
            per_file_stats.append({
                "filename":   fname,
                "n_records":  int(len(raw_df)),
                "n_patients": int(len(pset)),
                "n_items":    int(len(iset)),
            })

        if len(filenames) > 1:
            shared_all = set.intersection(*per_file_patient_sets) if per_file_patient_sets else set()
            union_all  = set.union(*per_file_patient_sets)       if per_file_patient_sets else set()
            n_shared_all = len(shared_all)
            n_union      = len(union_all)
            pct_shared   = round(n_shared_all / n_union * 100, 1) if n_union else 0.0

            # Variables que apareixen en més d'un fitxer
            from collections import Counter
            item_counter = Counter()
            for iset in per_file_item_sets:
                for it in iset:
                    item_counter[it] += 1
            overlapping_items = sorted([i for i, c in item_counter.items() if c > 1])

            relationship = {
                "n_patients_shared_all": n_shared_all,
                "n_patients_union":      n_union,
                "pct_patients_shared":   pct_shared,
                "overlapping_items":     overlapping_items,
                "n_overlapping_items":   len(overlapping_items),
            }
        else:
            relationship = None

        items = profile_items(df)

        # Detecció del format de timestamp (es pot sobreescriure des del front)
        date_detection = detect_date_format(df["data"])
        date_format    = date_detection["best"]
        dr             = _date_range(df, date_format)
        sid            = str(uuid.uuid4())

        sessions[sid] = {
            "df_original":     df,
            "filenames":       filenames,          # llista de noms originals
            "col_mapping":     col_mapping_global,
            "date_range":      dr,
            "date_format":     date_format,
            "date_detection":  date_detection,
            "items":           items,
            "classifications": {},
            "generalizations": {},
            "dfs_anonymized":  None,               # dict {filename → df} després d'anonimitzar
            "metrics":         None,
            "imputation_log":  {},
            "report_md":       None,
            "report_html":     None,
        }

        return {
            "session_id":      sid,
            "filenames":       filenames,
            "n_files":         len(filenames),
            "n_records":       len(df),
            "n_patients":      int(df["pacient"].nunique()),
            "n_items":         len(items),
            "date_range":      dr,
            "date_format":     date_format,
            "date_detection":  date_detection,
            "items":           items,
            "preview":         _df_preview(df),
            "per_file_stats":  per_file_stats,
            "relationship":    relationship,
        }

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, detail=str(e))


# ── Endpoint 1b: Override del format de timestamp ────────────────────────────

@app.post("/api/set-date-format")
async def set_date_format(req: DateFormatRequest):
    sess = _get_session(req.session_id)
    if req.date_format not in DATE_FORMATS:
        raise HTTPException(
            400,
            detail=f"date_format ha de ser un de: {', '.join(DATE_FORMATS)}",
        )
    sess["date_format"] = req.date_format

    # Recalculem el rang de dates i mostres parsejades amb el nou format
    sess["date_range"] = _date_range(sess["df_original"], req.date_format)
    redetection = detect_date_format(sess["df_original"]["data"])
    redetection["best"] = req.date_format     # respectem la tria manual
    # Regenerem mostres amb el format escollit per l'usuari
    from app.modules.anonymizer import _parse_dates
    s = sess["df_original"]["data"]
    parsed_user = _parse_dates(s, req.date_format)
    non_null = s.notna() & ~s.astype(str).str.strip().isin({"", "nan", "NaN", "None"})
    sample_idx = s[non_null].index[:5]
    samples = []
    for i in sample_idx:
        out = parsed_user.loc[i]
        samples.append({
            "raw":    str(s.loc[i]),
            "parsed": "" if pd.isna(out) else out.strftime("%Y-%m-%d %H:%M:%S"),
            "ok":     bool(pd.notna(out)),
        })
    redetection["samples"] = samples
    sess["date_detection"] = redetection

    return {
        "ok":             True,
        "date_format":    req.date_format,
        "date_range":     sess["date_range"],
        "date_detection": redetection,
    }


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
        # Simulem sobre el dataset combinat (sense la columna interna)
        df_t  = sess["df_original"].drop(columns=[_SOURCE_COL], errors="ignore")
        df_t  = compute_date_deltas(df_t, date_format=sess.get("date_format", "iso"))
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

        # ── Procés sobre el dataset combinat ──────────────────────────────────
        # Conservem la columna _source_file durant tot el procés
        df_t = sess["df_original"].copy()
        df_core = df_t.drop(columns=[_SOURCE_COL])

        df_core = compute_date_deltas(df_core, date_format=sess.get("date_format", "iso"))
        if generalizations:
            df_core = apply_generalizations(df_core, generalizations)
        df_core, imputation_log = impute_missing_values(df_core, quasi)
        df_core = hash_patient_ids(df_core)

        k_result = apply_k_anonymity(df_core, quasi, req.k)
        df_anon  = k_result["df_anonymized"]
        metrics  = compute_metrics(df_core, df_anon, quasi, k_result)

        # Recuperem la columna d'origen sobre el df anonimitzat
        # (els índexos es conserven de pd.concat, podem fer join per índex)
        df_anon_with_src = df_anon.copy()
        df_anon_with_src[_SOURCE_COL] = df_t.loc[df_anon.index, _SOURCE_COL].values

        # ── Separar per fitxer original ───────────────────────────────────────
        dfs_anonymized = {}
        for fname in sess["filenames"]:
            dfs_anonymized[fname] = (
                df_anon_with_src[df_anon_with_src[_SOURCE_COL] == fname]
                .drop(columns=[_SOURCE_COL])
                .reset_index(drop=True)
            )

        sess["dfs_anonymized"] = dfs_anonymized
        sess["metrics"]        = metrics
        sess["imputation_log"] = imputation_log

        # ── Generar informes ──────────────────────────────────────────────────
        now_str      = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        all_items    = [i["name"] for i in sess["items"]]
        orig_pacient = next(
            (o for o, c in sess["col_mapping"].items() if c == "pacient"), "patient_id"
        )
        filenames_str = ", ".join(sess["filenames"])

        report_kwargs = dict(
            lang             = req.lang,
            filename         = filenames_str,
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
            title              = _REPORT_TITLES.get(req.lang, _REPORT_TITLES["es"]),
            filename           = filenames_str,
            generated_at       = now_str,
            confidential_label = _CONFIDENTIAL.get(req.lang, _CONFIDENTIAL["es"]),
        )

        result = {k: v for k, v in metrics.items() if not isinstance(v, pd.DataFrame)}
        result["imputation_log"] = imputation_log
        result["n_files"]        = len(sess["filenames"])
        result["filenames"]      = sess["filenames"]
        return result

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, detail=str(e))


# ── Descàrregues ──────────────────────────────────────────────────────────────

@app.get("/api/download/csv/{session_id}")
async def download_csv(session_id: str):
    """
    Si hi ha un sol fitxer retorna un CSV directament.
    Si n'hi ha més d'un, retorna un ZIP amb un CSV anonimitzat per fitxer original.
    """
    sess = _get_session(session_id)
    if sess["dfs_anonymized"] is None:
        raise HTTPException(400, "Cal executar l'anonimització primer.")

    dfs = sess["dfs_anonymized"]

    if len(dfs) == 1:
        fname, df = next(iter(dfs.items()))
        buf = io.StringIO()
        df.to_csv(buf, index=False)
        out_name = fname.replace(".csv", "") + "_anonymized.csv"
        return _stream(buf.getvalue(), "text/csv", out_name)
    else:
        csv_map = {}
        for fname, df in dfs.items():
            buf = io.StringIO()
            df.to_csv(buf, index=False)
            out_name = fname.replace(".csv", "") + "_anonymized.csv"
            csv_map[out_name] = buf.getvalue()
        zip_bytes = _build_zip(csv_map)
        return _stream(zip_bytes, "application/zip", "datasets_anonymized.zip")


def _report_filename(filenames: list[str], ext: str) -> str:
    """
    Per a un sol fitxer pujat, l'informe pren el seu nom («dataset_X_report.html»).
    Per a multi-fitxer, un nom genèric («anonymization_report.html») per evitar
    que sembli que l'informe només cobreix el primer fitxer.
    """
    if filenames and len(filenames) == 1:
        return filenames[0].replace(".csv", "") + f"_report.{ext}"
    return f"anonymization_report.{ext}"


@app.get("/api/download/report/html/{session_id}")
async def download_html(session_id: str):
    sess = _get_session(session_id)
    if not sess.get("report_html"):
        raise HTTPException(400, "Cal executar l'anonimització primer.")
    return _stream(sess["report_html"], "text/html",
                   _report_filename(sess["filenames"], "html"))


@app.get("/api/download/report/md/{session_id}")
async def download_md(session_id: str):
    sess = _get_session(session_id)
    if not sess.get("report_md"):
        raise HTTPException(400, "Cal executar l'anonimització primer.")
    return _stream(sess["report_md"], "text/markdown",
                   _report_filename(sess["filenames"], "md"))


@app.get("/api/download/report/{session_id}")
async def download_json(session_id: str):
    sess = _get_session(session_id)
    if sess["metrics"] is None:
        raise HTTPException(400, "Cal executar l'anonimització primer.")
    report = {
        "filenames":       sess["filenames"],
        "date_format":     sess.get("date_format"),
        "date_range":      sess.get("date_range"),
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
