"""
generate_synthetic.py
---------------------
Genera un dataset sintètic de 500 pacients amb 2 visites cada un,
amb les mateixes 65 variables del dataset original.
Format: patient_id, data, variable, valor
"""

import random
import csv
from datetime import date, timedelta

random.seed(42)

# ── Definició de variables i dominis ─────────────────────────────────────────

VARIABLES = {
    # Numèriques
    "edad":                     ("numeric", 18, 95),
    "dolor_agudo":              ("numeric", 0, 10),
    "dolor_cronico":            ("numeric", 0, 10),
    "indice_de_comorbilidad":   ("numeric", 0, 8),
    "presencia_e_intensidad_de_sintomas": ("numeric", 0, 10),
    "valoracion_antropometrica": ("numeric", 40, 120),   # pes en kg aprox

    # Binàries si/no
    "ansiedad":                 ("binary",),
    "anticoagulacion":          ("binary",),
    "agitacion":                ("binary",),
    "agresividad":              ("binary",),
    "barrera_idiomatica":       ("binary",),
    "conducta_erratica":        ("binary",),
    "consumo_de_otras_sustancias_adictivas": ("binary",),
    "cuidadora_informal_asalariada_disponible": ("binary",),
    "cuidadora_informal_no_asalariada_disponible": ("binary",),
    "cuidados_paliativos":      ("binary",),
    "deshidratacion":           ("binary",),
    "desbalance_hipoglucemico_significativo": ("binary",),
    "disfagia":                 ("binary",),
    "enfermedad_neoplasica":    ("binary",),
    "inmunodepresion":          ("binary",),
    "inestabilidad_hemodinamica": ("binary",),
    "infeccion_activa_en_curso": ("binary",),
    "insuficiencia_cronica_de_aparato": ("binary",),
    "insuficiencia_cronica_de_organo":  ("binary",),
    "insuficiencia_cronica_de_sistema": ("binary",),
    "medicacion_de_alto_riesgo": ("binary",),
    "migracion":                ("binary",),
    "polifarmacia":             ("binary",),
    "riesgo_de_delirium":       ("binary",),
    "riesgo_hemorragico_relevante":    ("binary",),
    "riesgo_tromboembolico_relevante": ("binary",),
    "soledad_no_deseada":       ("binary",),
    "tabaquismo":               ("binary",),
    "depresion":                ("binary",),

    # Categòriques multivalue
    "actividades_basicas_de_la_vida_diaria": (
        "categorical", ["independiente", "dependencia_leve", "dependencia_moderada", "dependencia_severa", "dependencia_total"]),
    "actividades_instrumentales_de_la_vida_diaria": (
        "categorical", ["independiente", "dependencia_leve", "dependencia_moderada", "dependencia_severa"]),
    "adherencia_terapeutica": (
        "categorical", ["alta", "media", "baja"]),
    "alfabetizacion_en_salud": (
        "categorical", ["alta", "media", "baja"]),
    "alteracion_del_patron_respiratorio_asma_epoc_disnea_etc": (
        "categorical", ["no", "leve", "moderada", "grave"]),
    "comunicacion_verbal": (
        "categorical", ["normal", "moderada", "limitada", "nula"]),
    "consumo_de_alcohol": (
        "categorical", ["no", "moderado", "riesgo", "perjudicial"]),
    "continencia": (
        "categorical", ["continente", "parcial", "incontinencia"]),
    "cribado_de_pobreza": (
        "categorical", ["negativo", "positivo"]),
    "cribado_nutricional": (
        "categorical", ["sin_riesgo", "riesgo_leve", "riesgo_moderado", "riesgo_alto"]),
    "deficit_de_audicion": (
        "categorical", ["no", "leve", "moderada", "grave"]),
    "deficit_de_vision": (
        "categorical", ["no", "leve", "moderada", "grave"]),
    "deterioro_global": (
        "categorical", ["no", "leve", "moderado", "grave"]),
    "diversidad_funcional": (
        "categorical", ["no", "fisica", "sensorial", "cognitiva", "multiple"]),
    "estado_cognitivo": (
        "categorical", ["sin_deterioro", "deterioro_leve", "deterioro_moderado", "deterioro_severo"]),
    "etapa_vital_depresion_postparto_periodo_de_lactancia_duelo_signos_y_sintomas_de_la_menopausia_etc": (
        "categorical", ["no", "si"]),
    "fragilidad": (
        "categorical", ["robusta", "prefragil", "fragil"]),
    "movilidad_deambulacion_transferencia": (
        "categorical", ["independiente", "ayuda_tecnica", "supervision", "dependiente"]),
    "nivel_de_autocuidado": (
        "categorical", ["alto", "medio", "bajo"]),
    "nivel_de_socioeconomico": (
        "categorical", ["alto", "medio", "bajo"]),
    "nivel_educativo": (
        "categorical", ["sin_estudios", "primaria", "secundaria", "universitaria"]),
    "origen": (
        "categorical", ["espanya", "ue", "america_latina", "africa", "asia", "altres"]),
    "percepcion_sobre_la_salud_o_la_enfermedad": (
        "categorical", ["positiva", "neutra", "negativa"]),
    "red_de_apoyo_aislamiento_social": (
        "categorical", ["buena", "moderada", "escasa", "aislamiento"]),
    "riesgo_de_caidas": (
        "categorical", ["bajo", "medio", "alto"]),
    "riesgo_de_lesiones_por_presion_lesiones_relacionadas_con_la_dependencia": (
        "categorical", ["bajo", "medio", "alto"]),
    "sexo_y_o_genero": (
        "categorical", ["hombre", "mujer", "no_binario"]),
    "situacion_de_convivencia": (
        "categorical", ["solo", "familia", "pareja", "residencia", "otros"]),
    "sobrecarga_del_cuidador": (
        "categorical", ["no", "leve", "moderada", "severa"]),
    "valoracion_de_riesgos_en_el_domicilio": (
        "categorical", ["bajo", "medio", "alto"]),
}

# Pesos per als binaris (prob de "si")
BINARY_PROBS = {
    "ansiedad": 0.35, "anticoagulacion": 0.25, "agitacion": 0.15,
    "agresividad": 0.10, "barrera_idiomatica": 0.12, "conducta_erratica": 0.12,
    "consumo_de_otras_sustancias_adictivas": 0.08, "cuidadora_informal_asalariada_disponible": 0.20,
    "cuidadora_informal_no_asalariada_disponible": 0.45, "cuidados_paliativos": 0.15,
    "deshidratacion": 0.10, "desbalance_hipoglucemico_significativo": 0.08,
    "disfagia": 0.18, "enfermedad_neoplasica": 0.22, "inmunodepresion": 0.12,
    "inestabilidad_hemodinamica": 0.08, "infeccion_activa_en_curso": 0.15,
    "insuficiencia_cronica_de_aparato": 0.30, "insuficiencia_cronica_de_organo": 0.25,
    "insuficiencia_cronica_de_sistema": 0.20, "medicacion_de_alto_riesgo": 0.40,
    "migracion": 0.15, "polifarmacia": 0.55, "riesgo_de_delirium": 0.20,
    "riesgo_hemorragico_relevante": 0.18, "riesgo_tromboembolico_relevante": 0.22,
    "soledad_no_deseada": 0.28, "tabaquismo": 0.20, "depresion": 0.30,
}

# Introduïm NaN de forma realista (alguns ítems no sempre es registren)
NAN_PROBS = {
    "valoracion_de_riesgos_en_el_domicilio": 0.25,
    "sobrecarga_del_cuidador": 0.30,
    "alfabetizacion_en_salud": 0.20,
    "etapa_vital_depresion_postparto_periodo_de_lactancia_duelo_signos_y_sintomas_de_la_menopausia_etc": 0.15,
    "cribado_de_pobreza": 0.20,
    "barrera_idiomatica": 0.10,
    "valoracion_antropometrica": 0.15,
    "dolor_cronico": 0.12,
    "red_de_apoyo_aislamiento_social": 0.10,
}


def gen_value(var_name, var_def, patient_profile):
    """Genera un valor per a la variable, coherent amb el perfil del pacient."""

    # NaN probabilístic
    if random.random() < NAN_PROBS.get(var_name, 0.0):
        return None

    kind = var_def[0]

    if kind == "numeric":
        lo, hi = var_def[1], var_def[2]
        if var_name == "edad":
            return patient_profile["edad"]
        val = random.gauss((lo + hi) / 2, (hi - lo) / 5)
        return max(lo, min(hi, round(val)))

    elif kind == "binary":
        prob = BINARY_PROBS.get(var_name, 0.25)
        return "si" if random.random() < prob else "no"

    elif kind == "categorical":
        choices = var_def[1]
        # Alguns ítems correlacionen amb l'edat
        edad = patient_profile.get("edad", 50)
        if var_name == "fragilidad":
            if edad < 40:   weights = [0.70, 0.25, 0.05]
            elif edad < 65: weights = [0.40, 0.40, 0.20]
            else:           weights = [0.15, 0.35, 0.50]
            return random.choices(choices, weights=weights)[0]
        if var_name == "estado_cognitivo":
            if edad < 60:   weights = [0.75, 0.15, 0.07, 0.03]
            elif edad < 75: weights = [0.45, 0.30, 0.17, 0.08]
            else:           weights = [0.20, 0.30, 0.30, 0.20]
            return random.choices(choices, weights=weights)[0]
        return random.choice(choices)

    return None


def generate_dataset(n_patients=500, visits_per_patient=2, output_path="sample_data/dataset_500p.csv"):
    rows = []
    base_date = date(2023, 1, 1)

    for i in range(1, n_patients + 1):
        pid = f"P{i:04d}"

        # Perfil fix del pacient
        profile = {
            "edad":   random.randint(18, 92),
            "sexe":   random.choice(["hombre", "mujer", "no_binario"]),
            "origen": random.choice(["espanya", "ue", "america_latina", "africa", "asia", "altres"]),
        }

        # Generem dates de visita (separades almenys 20 dies)
        first_visit = base_date + timedelta(days=random.randint(0, 365))
        visit_dates = [first_visit]
        for _ in range(visits_per_patient - 1):
            gap = timedelta(days=random.randint(20, 180))
            visit_dates.append(visit_dates[-1] + gap)

        for visit_date in visit_dates:
            date_str = visit_date.strftime("%Y-%m-%d")
            for var_name, var_def in VARIABLES.items():
                value = gen_value(var_name, var_def, profile)
                rows.append({
                    "patient_id": pid,
                    "data":       date_str,
                    "variable":   var_name,
                    "valor":      value if value is not None else "",
                })

    # Barregem per realisme
    random.shuffle(rows)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["patient_id", "data", "variable", "valor"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"✅ Dataset generat: {len(rows)} registres, {n_patients} pacients, {visits_per_patient} visites/pacient")
    print(f"   → {output_path}")


if __name__ == "__main__":
    import os
    os.makedirs("sample_data", exist_ok=True)
    generate_dataset(n_patients=500, visits_per_patient=2)
