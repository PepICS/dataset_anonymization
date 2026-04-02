"""
anonymizer.py
-------------
Nucli de la lògica d'anonimització:
  - Validació del format d'entrada (4 columnes fixes)
  - Perfilat d'ítems (detecció numèric vs categòric, valors únics)
  - Transformació de dates → delta enters per pacient
  - Hash SHA-256 de l'identificador de pacient
  - Aplicació de generalitzacions sobre quasi-identificadors
  - K-anonimitat per supressió
  - Càlcul de mètriques comparatives
"""

import hashlib
import pandas as pd
import numpy as np
from typing import Any

# ── Àlies de columnes acceptades ─────────────────────────────────────────────
# Cada clau canònica pot tenir diversos noms alternatius al CSV
COL_ALIASES = {
    "pacient": {"pacient", "patient", "patient_id", "pacient_id", "nhc", "pid", "id", "id_pacient"},
    "data":    {"data", "date", "fecha", "datetime", "timestamp", "dt"},
    "item":    {"item", "variable", "var", "camp", "field", "measure"},
    "valor":   {"valor", "value", "val", "resultat", "result"},
}

# Umbral de valors únics per considerar un ítem com a numèric
NUMERIC_UNIQUE_THRESHOLD = 20


# ── Normalització de columnes ─────────────────────────────────────────────────

def normalize_columns(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    Renombra les columnes del DataFrame als noms canònics (pacient, data, item, valor)
    si es detecten àlies coneguts.

    Retorna (df_normalitzat, mapping_aplicat).
    """
    rename_map = {}
    cols_lower = {c: c.strip().lower() for c in df.columns}

    for canonical, aliases in COL_ALIASES.items():
        for orig_col, lower_col in cols_lower.items():
            if lower_col in aliases and canonical not in rename_map.values():
                rename_map[orig_col] = canonical
                break

    if rename_map:
        df = df.rename(columns=rename_map)

    return df, rename_map


# ── Validació ─────────────────────────────────────────────────────────────────

def validate_dataframe(df: pd.DataFrame) -> list[str]:
    """
    Comprova que el DataFrame tingui les 4 columnes canòniques esperades.
    Retorna una llista d'errors (buida si tot és correcte).
    """
    errors = []
    required = {"pacient", "data", "item", "valor"}
    missing  = required - set(df.columns)
    if missing:
        errors.append(
            f"Columnes no reconegudes: {', '.join(sorted(missing))}. "
            f"Cal tenir: pacient/patient_id, data/date, item/variable, valor/value."
        )
    if df.empty:
        errors.append("El fitxer és buit.")
    return errors


# ── Perfilat d'ítems ──────────────────────────────────────────────────────────

def _is_numeric_item(series: pd.Series) -> bool:
    """Comprova si una sèrie de valors és predominantment numèrica."""
    non_null = series.dropna().astype(str)
    if len(non_null) == 0:
        return False
    numeric_count = pd.to_numeric(non_null, errors='coerce').notna().sum()
    return (numeric_count / len(non_null)) > 0.8


def profile_items(df: pd.DataFrame) -> list[dict]:
    """
    Per a cada ítem únic del dataset, retorna:
      - name       : nom de l'ítem
      - type       : 'numeric' | 'categorical'
      - n_records  : nombre total de registres amb aquest ítem
      - n_unique   : nombre de valors únics
      - values     : llista de valors únics (per a categòrics) o estadístiques (per a numèrics)
      - stats      : estadístiques numèriques (min, max, mean, median) si numeric
    """
    profiles = []
    for item_name in sorted(df["item"].unique()):
        subset = df[df["item"] == item_name]["valor"]
        is_num = _is_numeric_item(subset)

        profile = {
            "name":      item_name,
            "type":      "numeric" if is_num else "categorical",
            "n_records": int(len(subset)),
            "n_unique":  int(subset.nunique()),
        }

        if is_num:
            num_series = pd.to_numeric(subset, errors="coerce").dropna()
            profile["stats"] = {
                "min":    _safe_num(num_series.min()),
                "max":    _safe_num(num_series.max()),
                "mean":   _safe_num(num_series.mean()),
                "median": _safe_num(num_series.median()),
                "std":    _safe_num(num_series.std()),
            }
            # Histograma bàsic (10 bins)
            try:
                counts, edges = np.histogram(num_series, bins=min(10, profile["n_unique"]))
                profile["histogram"] = {
                    "counts": counts.tolist(),
                    "edges":  [round(float(e), 2) for e in edges],
                }
            except Exception:
                pass
        else:
            vc = subset.value_counts()
            profile["values"]       = sorted([str(v) for v in subset.dropna().unique()])
            profile["value_counts"] = {str(k): int(v) for k, v in vc.items()}

        profiles.append(profile)
    return profiles


# ── Transformació de dates ────────────────────────────────────────────────────

def compute_date_deltas(df: pd.DataFrame) -> pd.DataFrame:
    """
    Substitueix la columna 'data' pel nombre de dies transcorreguts
    des de la primera data de cada pacient (delta enter ≥ 0).
    """
    df = df.copy()
    parsed = pd.to_datetime(df["data"], errors="coerce")
    ref    = parsed.groupby(df["pacient"]).transform("min")
    df["data"] = (parsed - ref).dt.days.astype("Int64")
    return df


# ── Hash de pacient ───────────────────────────────────────────────────────────

def hash_patient_ids(df: pd.DataFrame) -> pd.DataFrame:
    """Substitueix 'pacient' pel hash SHA-256 truncat (irreversible)."""
    df = df.copy()
    df["pacient"] = df["pacient"].apply(
        lambda v: "H-" + hashlib.sha256(str(v).encode()).hexdigest()[:12] if pd.notna(v) else v
    )
    return df


# ── Imputació de valors absents ──────────────────────────────────────────────

def impute_missing_values(df: pd.DataFrame, quasi_id_items: list[str]) -> tuple[pd.DataFrame, dict]:
    """
    Imputa els valors absents (NaN) dels quasi-identificadors abans d'aplicar
    la k-anonimitat, per evitar que pacients sense dada formin grups minúsculs
    i siguin suprimits innecessàriament.

    Estratègia:
      - Variables categòriques → "Desconocido"
      - Variables numèriques   → mediana del ítem (enter si el valor original és enter)

    Retorna el DataFrame imputat i un log de quants valors s'han imputat per ítem.
    """
    df  = df.copy()
    log = {}

    for item_name in quasi_id_items:
        mask_item = df["item"] == item_name
        if not mask_item.any():
            continue

        vals     = df.loc[mask_item, "valor"]
        n_null   = vals.isna().sum() + (vals.astype(str).str.strip().isin(["", "nan", "NaN", "None"])).sum()

        if n_null == 0:
            continue

        # Detectem si és numèric
        num_vals = pd.to_numeric(vals, errors="coerce")
        is_num   = num_vals.notna().mean() > 0.8

        if is_num:
            median_val = num_vals.median()
            # Mantenem format enter si tots els valors eren enters
            if num_vals.dropna().apply(lambda x: x == int(x)).all():
                fill_val = str(int(median_val))
            else:
                fill_val = str(round(median_val, 2))
            strategy = f"mediana ({fill_val})"
        else:
            fill_val = "Desconocido"
            strategy = "Desconocido"

        # Imputem NaN i strings buits
        null_mask = mask_item & (vals.isna() | vals.astype(str).str.strip().isin(["", "nan", "NaN", "None"]))
        df.loc[null_mask, "valor"] = fill_val

        log[item_name] = {
            "n_imputed": int(n_null),
            "strategy":  strategy,
            "is_numeric": is_num,
        }

    return df, log


# ── Aplicació de generalitzacions ────────────────────────────────────────────

def apply_generalizations(df: pd.DataFrame, configs: dict) -> pd.DataFrame:
    """
    Aplica les generalitzacions definides per l'usuari sobre els quasi-IDs.

    configs: { item_name → { type: "bins"|"mapping", ... } }
    """
    df = df.copy()

    for item_name, cfg in configs.items():
        mask = df["item"] == item_name
        if not mask.any():
            continue

        t = cfg.get("type")

        if t == "bins":
            bins   = cfg["bins"]
            labels = cfg["labels"]
            num_vals = pd.to_numeric(df.loc[mask, "valor"], errors="coerce")
            df.loc[mask, "valor"] = pd.cut(
                num_vals, bins=bins, labels=labels,
                right=False, include_lowest=True
            ).astype(str)

        elif t == "mapping":
            mapping       = cfg.get("mapping", {})
            unmapped_label = cfg.get("unmapped_label", "Altres")
            df.loc[mask, "valor"] = df.loc[mask, "valor"].astype(str).map(
                lambda v: mapping.get(v, unmapped_label)
            )

    return df


# ── K-anonimitat ──────────────────────────────────────────────────────────────

def apply_k_anonymity(df: pd.DataFrame, quasi_id_items: list[str], k: int) -> dict:
    """
    Pivota els quasi-IDs a columnes, agrupa per pacient i quasi-IDs,
    suprimeix els grups amb menys de k pacients, i retorna el dataset net.

    Retorna:
      df_anonymized   : DataFrame final (format llarg original, sense registres suprimits)
      df_suppressed   : DataFrame de registres suprimits
      stats           : estadístiques detallades
    """
    if not quasi_id_items:
        return {
            "df_anonymized":    df,
            "df_suppressed":    pd.DataFrame(),
            "n_patients_orig":  int(df["pacient"].nunique()),
            "n_patients_final": int(df["pacient"].nunique()),
            "n_records_orig":   len(df),
            "n_records_final":  len(df),
            "n_suppressed_patients": 0,
            "pct_suppressed":   0.0,
            "equivalence_classes": {},
            "suppressed_groups": [],
            "k_used": k,
            "warning": "Cap quasi-identificador definit.",
        }

    # Pivot: una fila per pacient, una columna per cada quasi-ID
    qi_df = df[df["item"].isin(quasi_id_items)].copy()
    qi_df["valor"] = qi_df["valor"].astype(str)

    pivot = (
        qi_df.groupby(["pacient", "item"])["valor"]
        .first()
        .unstack(fill_value="NaN")
        .reset_index()
    )

    # Assegurem que totes les columnes quasi-ID existeixin
    for col in quasi_id_items:
        if col not in pivot.columns:
            pivot[col] = "NaN"

    # Mida de cada grup (classe d'equivalència)
    group_cols = quasi_id_items
    group_sizes = pivot.groupby(group_cols, dropna=False)["pacient"].count().reset_index(name="_count_")

    pivot_m = pivot.merge(group_sizes, on=group_cols, how="left")

    # Pacients conformes (grup >= k)
    conform_patients  = set(pivot_m[pivot_m["_count_"] >= k]["pacient"].tolist())
    suppress_patients = set(pivot_m[pivot_m["_count_"] < k]["pacient"].tolist())

    df_anonymized = df[df["pacient"].isin(conform_patients)].copy()
    df_suppressed = df[df["pacient"].isin(suppress_patients)].copy()

    n_patients_orig  = int(df["pacient"].nunique())
    n_patients_final = int(len(conform_patients))
    n_sup_patients   = int(len(suppress_patients))
    pct_sup          = round(n_sup_patients / n_patients_orig * 100, 2) if n_patients_orig else 0.0

    # Distribució de mides de grup
    size_dist = group_sizes["_count_"].value_counts().sort_index()
    eq_stats  = {
        "total_groups":      int(len(group_sizes)),
        "conforming_groups": int((group_sizes["_count_"] >= k).sum()),
        "suppressed_groups_count": int((group_sizes["_count_"] < k).sum()),
        "size_distribution": {str(int(s)): int(c) for s, c in size_dist.items()},
        "min_size":  int(group_sizes["_count_"].min()),
        "max_size":  int(group_sizes["_count_"].max()),
        "mean_size": round(float(group_sizes["_count_"].mean()), 2),
    }

    # Grups suprimits (detall, màxim 30)
    sup_df = group_sizes[group_sizes["_count_"] < k].sort_values("_count_")
    suppressed_groups = [
        {str(kk): (int(vv) if kk == "_count_" else str(vv)) for kk, vv in row.items()}
        for row in sup_df.head(30).to_dict(orient="records")
    ]

    return {
        "df_anonymized":         df_anonymized,
        "df_suppressed":         df_suppressed,
        "n_patients_orig":       n_patients_orig,
        "n_patients_final":      n_patients_final,
        "n_records_orig":        len(df),
        "n_records_final":       len(df_anonymized),
        "n_suppressed_patients": n_sup_patients,
        "pct_suppressed":        pct_sup,
        "equivalence_classes":   eq_stats,
        "suppressed_groups":     suppressed_groups,
        "k_used":                k,
    }


# ── Mètriques comparatives ────────────────────────────────────────────────────

def compute_metrics(df_orig: pd.DataFrame, df_anon: pd.DataFrame,
                    quasi_id_items: list[str], k_result: dict) -> dict:
    """
    Calcula mètriques comparatives entre el dataset original i l'anonimitzat.
    """
    n_pat_orig  = int(df_orig["pacient"].nunique())
    n_pat_anon  = int(df_anon["pacient"].nunique()) if len(df_anon) else 0
    n_rec_orig  = len(df_orig)
    n_rec_anon  = len(df_anon)
    n_items     = int(df_orig["item"].nunique())

    # Dates úniques (visites) per pacient
    visits_orig = df_orig.groupby("pacient")["data"].nunique()
    visits_anon = df_anon.groupby("pacient")["data"].nunique() if len(df_anon) else pd.Series([], dtype=int)

    eq = k_result.get("equivalence_classes", {})

    return {
        "n_patients_orig":       n_pat_orig,
        "n_patients_final":      n_pat_anon,
        "n_suppressed_patients": k_result.get("n_suppressed_patients", 0),
        "pct_suppressed":        k_result.get("pct_suppressed", 0.0),
        "n_records_orig":        n_rec_orig,
        "n_records_final":       n_rec_anon,
        "n_items":               n_items,
        "n_quasi_ids":           len(quasi_id_items),
        "quasi_id_items":        quasi_id_items,
        "k_used":                k_result.get("k_used"),
        "visits_per_patient_orig": {
            "min":  int(visits_orig.min()) if len(visits_orig) else 0,
            "max":  int(visits_orig.max()) if len(visits_orig) else 0,
            "mean": round(float(visits_orig.mean()), 2) if len(visits_orig) else 0,
        },
        "visits_per_patient_final": {
            "min":  int(visits_anon.min()) if len(visits_anon) else 0,
            "max":  int(visits_anon.max()) if len(visits_anon) else 0,
            "mean": round(float(visits_anon.mean()), 2) if len(visits_anon) else 0,
        },
        "equivalence_classes": eq,
        "suppressed_groups":   k_result.get("suppressed_groups", []),
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _safe_num(val) -> float | None:
    try:
        v = float(val)
        return None if (np.isnan(v) or np.isinf(v)) else round(v, 4)
    except Exception:
        return None
