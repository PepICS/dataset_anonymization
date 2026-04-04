"""
anonymizer.py
-------------
Nucli de la lògica d'anonimització:
  - Normalització i validació del CSV d'entrada (4 columnes)
  - Perfilat d'ítems (detecció numèric vs categòric)
  - Transformació de dates → delta enters per pacient
  - Hash SHA-256 irreversible de l'identificador de pacient
  - Imputació de NaN als quasi-identificadors
  - Generalitzacions (bins numèrics / mapeig categòric)
  - K-anonimitat per supressió
  - Càlcul de mètriques comparatives
"""

import hashlib
import pandas as pd
import numpy as np

# ── Àlies de columnes acceptades ─────────────────────────────────────────────
COL_ALIASES = {
    "pacient": {"pacient", "patient", "patient_id", "pacient_id", "nhc", "pid", "id", "id_pacient"},
    "data":    {"data", "date", "fecha", "datetime", "timestamp", "dt"},
    "item":    {"item", "variable", "var", "camp", "field", "measure"},
    "valor":   {"valor", "value", "val", "resultat", "result"},
}

_NULL_STRINGS = {"", "nan", "NaN", "None"}


# ── Normalització i validació ─────────────────────────────────────────────────

def normalize_columns(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Renombra les columnes als noms canònics. Retorna (df, mapping original→canònic)."""
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


def validate_dataframe(df: pd.DataFrame) -> list[str]:
    """Retorna una llista d'errors de validació (buida si tot és correcte)."""
    errors = []
    missing = {"pacient", "data", "item", "valor"} - set(df.columns)
    if missing:
        errors.append(
            f"Columnes no reconegudes: {', '.join(sorted(missing))}. "
            "Cal tenir: pacient/patient_id, data/date, item/variable, valor/value."
        )
    if df.empty:
        errors.append("El fitxer és buit.")
    return errors


# ── Perfilat d'ítems ──────────────────────────────────────────────────────────

def _is_numeric(series: pd.Series) -> bool:
    non_null = series.dropna().astype(str)
    if len(non_null) == 0:
        return False
    return (pd.to_numeric(non_null, errors="coerce").notna().sum() / len(non_null)) > 0.8


def profile_items(df: pd.DataFrame) -> list[dict]:
    """Retorna el perfil estadístic de cada ítem únic del dataset."""
    profiles = []
    for item_name in sorted(df["item"].unique()):
        subset  = df[df["item"] == item_name]["valor"]
        is_num  = _is_numeric(subset)
        profile = {
            "name":      item_name,
            "type":      "numeric" if is_num else "categorical",
            "n_records": int(len(subset)),
            "n_unique":  int(subset.nunique()),
        }
        if is_num:
            num = pd.to_numeric(subset, errors="coerce").dropna()
            profile["stats"] = {
                "min":    _safe_num(num.min()),
                "max":    _safe_num(num.max()),
                "mean":   _safe_num(num.mean()),
                "median": _safe_num(num.median()),
                "std":    _safe_num(num.std()),
            }
            try:
                counts, edges = np.histogram(num, bins=min(10, profile["n_unique"]))
                profile["histogram"] = {
                    "counts": counts.tolist(),
                    "edges":  [round(float(e), 2) for e in edges],
                }
            except Exception:
                pass
        else:
            vc = subset.value_counts()
            profile["values"]       = sorted(str(v) for v in subset.dropna().unique())
            profile["value_counts"] = {str(k): int(v) for k, v in vc.items()}
        profiles.append(profile)
    return profiles


# ── Transformació de dates ────────────────────────────────────────────────────

def compute_date_deltas(df: pd.DataFrame) -> pd.DataFrame:
    """Converteix 'data' a dies transcorreguts des de la primera visita de cada pacient."""
    df     = df.copy()
    parsed = pd.to_datetime(df["data"], errors="coerce")
    ref    = parsed.groupby(df["pacient"]).transform("min")
    df["data"] = (parsed - ref).dt.days.astype("Int64")
    return df


# ── Hash de pacient ───────────────────────────────────────────────────────────

def hash_patient_ids(df: pd.DataFrame) -> pd.DataFrame:
    """Substitueix 'pacient' pel hash SHA-256 truncat irreversible (prefix H-)."""
    df = df.copy()
    df["pacient"] = df["pacient"].apply(
        lambda v: "H-" + hashlib.sha256(str(v).encode()).hexdigest()[:12]
        if pd.notna(v) else v
    )
    return df


# ── Imputació de valors absents ───────────────────────────────────────────────

def impute_missing_values(df: pd.DataFrame, quasi_id_items: list[str]) -> tuple[pd.DataFrame, dict]:
    """
    Imputa NaN als quasi-identificadors per evitar supressió innecessària:
      - Categòrics → "Desconocido"
      - Numèrics   → mediana observada

    Retorna (df_imputat, log).
    """
    df  = df.copy()
    log = {}

    for item_name in quasi_id_items:
        mask = df["item"] == item_name
        if not mask.any():
            continue

        vals      = df.loc[mask, "valor"]
        null_mask = mask & (vals.isna() | vals.astype(str).str.strip().isin(_NULL_STRINGS))
        n_null    = int(null_mask.sum())

        if n_null == 0:
            continue

        num_vals = pd.to_numeric(vals, errors="coerce")
        is_num   = (num_vals.notna().sum() / len(vals)) > 0.8

        if is_num:
            median_val = num_vals.median()
            fill_val   = (str(int(median_val))
                          if num_vals.dropna().apply(lambda x: x == int(x)).all()
                          else str(round(median_val, 2)))
            strategy = f"mediana ({fill_val})"
        else:
            fill_val = "Desconocido"
            strategy = "Desconocido"

        df.loc[null_mask, "valor"] = fill_val
        log[item_name] = {"n_imputed": n_null, "strategy": strategy, "is_numeric": is_num}

    return df, log


# ── Generalitzacions ──────────────────────────────────────────────────────────

def apply_generalizations(df: pd.DataFrame, configs: dict) -> pd.DataFrame:
    """Aplica bins o mapeig categòric als quasi-IDs segons la configuració de l'usuari."""
    df = df.copy()
    for item_name, cfg in configs.items():
        mask = df["item"] == item_name
        if not mask.any():
            continue
        t = cfg.get("type")
        if t == "bins":
            df.loc[mask, "valor"] = pd.cut(
                pd.to_numeric(df.loc[mask, "valor"], errors="coerce"),
                bins=cfg["bins"], labels=cfg["labels"],
                right=False, include_lowest=True,
            ).astype(str)
        elif t == "mapping":
            unmapped = cfg.get("unmapped_label", "Altres")
            mapping  = cfg.get("mapping", {})
            df.loc[mask, "valor"] = df.loc[mask, "valor"].astype(str).map(
                lambda v: mapping.get(v, unmapped)
            )
    return df


# ── K-anonimitat ──────────────────────────────────────────────────────────────

def apply_k_anonymity(df: pd.DataFrame, quasi_id_items: list[str], k: int) -> dict:
    """
    Aplica k-anonimitat per supressió. Elimina tots els registres dels pacients
    que no pertanyen a un grup d'equivalència amb almenys k membres.
    """
    if not quasi_id_items:
        n = int(df["pacient"].nunique())
        return {
            "df_anonymized": df, "n_patients_orig": n, "n_patients_final": n,
            "n_records_orig": len(df), "n_records_final": len(df),
            "n_suppressed_patients": 0, "pct_suppressed": 0.0,
            "equivalence_classes": {}, "suppressed_groups": [], "k_used": k,
            "warning": "Cap quasi-identificador definit.",
        }

    qi_df = df[df["item"].isin(quasi_id_items)].copy()
    qi_df["valor"] = qi_df["valor"].astype(str)

    pivot = (
        qi_df.groupby(["pacient", "item"])["valor"]
        .first().unstack(fill_value="NaN").reset_index()
    )
    for col in quasi_id_items:
        if col not in pivot.columns:
            pivot[col] = "NaN"

    group_sizes = (
        pivot.groupby(quasi_id_items, dropna=False)["pacient"]
        .count().reset_index(name="_count_")
    )
    pivot_m = pivot.merge(group_sizes, on=quasi_id_items, how="left")

    conform  = set(pivot_m[pivot_m["_count_"] >= k]["pacient"])
    suppress = set(pivot_m[pivot_m["_count_"] <  k]["pacient"])

    df_anon  = df[df["pacient"].isin(conform)].copy()
    n_orig   = int(df["pacient"].nunique())
    n_supp   = len(suppress)
    pct_supp = round(n_supp / n_orig * 100, 2) if n_orig else 0.0

    size_dist = group_sizes["_count_"].value_counts().sort_index()
    eq_stats  = {
        "total_groups":            int(len(group_sizes)),
        "conforming_groups":       int((group_sizes["_count_"] >= k).sum()),
        "suppressed_groups_count": int((group_sizes["_count_"] <  k).sum()),
        "size_distribution":       {str(int(s)): int(c) for s, c in size_dist.items()},
        "min_size":                int(group_sizes["_count_"].min()),
        "max_size":                int(group_sizes["_count_"].max()),
        "mean_size":               round(float(group_sizes["_count_"].mean()), 2),
    }

    suppressed_groups = [
        {str(kk): (int(vv) if kk == "_count_" else str(vv)) for kk, vv in row.items()}
        for row in group_sizes[group_sizes["_count_"] < k]
            .sort_values("_count_").head(30).to_dict(orient="records")
    ]

    return {
        "df_anonymized":          df_anon,
        "n_patients_orig":        n_orig,
        "n_patients_final":       len(conform),
        "n_records_orig":         len(df),
        "n_records_final":        len(df_anon),
        "n_suppressed_patients":  n_supp,
        "pct_suppressed":         pct_supp,
        "equivalence_classes":    eq_stats,
        "suppressed_groups":      suppressed_groups,
        "k_used":                 k,
    }


# ── Mètriques comparatives ────────────────────────────────────────────────────

def compute_metrics(df_orig: pd.DataFrame, df_anon: pd.DataFrame,
                    quasi_id_items: list[str], k_result: dict) -> dict:
    """Mètriques comparatives entre el dataset original i l'anonimitzat."""
    visits_orig = df_orig.groupby("pacient")["data"].nunique()
    return {
        "n_patients_orig":       int(df_orig["pacient"].nunique()),
        "n_patients_final":      int(df_anon["pacient"].nunique()) if len(df_anon) else 0,
        "n_suppressed_patients": k_result.get("n_suppressed_patients", 0),
        "pct_suppressed":        k_result.get("pct_suppressed", 0.0),
        "n_records_orig":        len(df_orig),
        "n_records_final":       len(df_anon),
        "n_items":               int(df_orig["item"].nunique()),
        "n_quasi_ids":           len(quasi_id_items),
        "quasi_id_items":        quasi_id_items,
        "k_used":                k_result.get("k_used"),
        "visits_per_patient_orig": {
            "min":  int(visits_orig.min())              if len(visits_orig) else 0,
            "max":  int(visits_orig.max())              if len(visits_orig) else 0,
            "mean": round(float(visits_orig.mean()), 2) if len(visits_orig) else 0,
        },
        "equivalence_classes": k_result.get("equivalence_classes", {}),
        "suppressed_groups":   k_result.get("suppressed_groups", []),
    }


# ── Helper ────────────────────────────────────────────────────────────────────

def _safe_num(val) -> float | None:
    try:
        v = float(val)
        return None if (np.isnan(v) or np.isinf(v)) else round(v, 4)
    except Exception:
        return None
