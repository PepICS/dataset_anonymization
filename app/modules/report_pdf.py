"""
report_pdf.py
-------------
Genera l'informe d'anonimització en format PDF (A4) usant reportlab.
Mateix contingut que l'informe Markdown però en format professional
llest per a presentar al departament de protecció de dades.
"""

import io
from datetime import datetime, timezone

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether
)
from reportlab.platypus.flowables import Flowable

# ── Paleta de colors ─────────────────────────────────────────────────────────
C_BG        = HexColor("#080d18")
C_ACCENT    = HexColor("#00c2d4")
C_ACCENT2   = HexColor("#0a8fa0")
C_SURFACE   = HexColor("#0f1827")
C_SURFACE2  = HexColor("#162033")
C_BORDER    = HexColor("#1a2e48")
C_TEXT      = HexColor("#dde8f5")
C_MUTED     = HexColor("#4d6e8a")
C_AMBER     = HexColor("#f5a623")
C_SUCCESS   = HexColor("#24c87a")
C_DANGER    = HexColor("#f04060")
C_WHITE     = HexColor("#ffffff")
C_LIGHT_BG  = HexColor("#f4f7fb")
C_DARK_HDR  = HexColor("#1a2e48")
C_BODY_TEXT = HexColor("#1a2035")
C_SECTION   = HexColor("#003d80")

# ── Textos per idioma ────────────────────────────────────────────────────────
_LABELS = {
    "ca": {
        "title":         "Informe d'Anonimització de Dades Clíniques",
        "subtitle":      "Prepared for the Data Protection Department",
        "subtitle_ca":   "Preparat per al Departament de Protecció de Dades",
        "generated":     "Generat el",
        "file":          "Fitxer",
        "tool":          "Eina: Datathon Anonymizer v2.0",
        "confidential":  "DOCUMENT CONFIDENCIAL · ÚS INTERN",
        "toc":           "Índex de continguts",
        "s1": "1. Resum Executiu",
        "s2": "2. Dataset Original",
        "s3": "3. Marc Legal i Metodològic",
        "s4": "4. Procés d'Anonimització",
        "s4a": "4.1 Identificador de Pacient",
        "s4b": "4.2 Tractament de Dates",
        "s4c": "4.3 Imputació de Valors Absents",
        "s4d": "4.4 Classificació de Variables",
        "s4e": "4.5 Generalització de Quasi-Identificadors",
        "s4f": "4.6 Aplicació de la K-Anonimitat",
        "s5": "5. Resultats i Mètriques",
        "s6": "6. Limitacions Metodològiques",
        "s7": "7. Conclusions i Checklist",
        "param": "Paràmetre", "value": "Valor",
        "pat_orig": "Pacients originals", "pat_final": "Pacients finals",
        "pat_supp": "Pacients eliminats", "pct_supp": "Percentatge eliminat",
        "rec_orig": "Registres originals", "rec_final": "Registres finals",
        "k_val": "Valor de k", "quasi_ids": "Quasi-identificadors",
        "col_orig": "Columna original", "col_can": "Columna canònica", "col_desc": "Descripció",
        "col_patient": "Identificador únic del pacient",
        "col_date": "Data de la visita",
        "col_item": "Nom de la variable clínica",
        "col_value": "Valor observat",
        "stat_patients": "Pacients únics", "stat_records": "Registres totals",
        "stat_items": "Variables (ítems)", "stat_dates": "Rang de dates",
        "stat_visits": "Visites per pacient",
        "var": "Variable", "classif": "Classificació",
        "quasi_label": "🔍 Quasi-identificador", "nonid_label": "✅ No identificatiu",
        "direct_label": "🔑 Identificador directe (hash)", "date_label": "📅 Data (delta)",
        "gen_type": "Tipus", "gen_cuts": "Punts de tall", "gen_intervals": "Intervals",
        "gen_mapping": "Mapeig", "gen_unmapped": "No assignats",
        "gen_bins": "Intervals numèrics", "gen_map": "Mapeig de categories",
        "eq_total": "Total de grups", "eq_conform": "Grups conformes (≥k)",
        "eq_supp": "Grups suprimits (<k)", "eq_min": "Mida mínima",
        "eq_max": "Mida màxima", "eq_mean": "Mida mitjana",
        "dist_size": "Mida del grup", "dist_groups": "Nombre de grups", "dist_patients": "Pacients",
        "supp_title": "Grups suprimits (fins a 20)",
        "imp_var": "Variable", "imp_n": "Registres imputats", "imp_strat": "Estratègia",
        "no_imp": "Cap valor absent detectat als quasi-identificadors.",
        "no_supp": "Cap grup suprimit.",
        "flow_orig": "Dataset original", "flow_imp": "Després imputació",
        "flow_supp": "Suprimits", "flow_final": "Dataset final",
        "checklist_title": "Verificació per al Departament de Protecció de Dades",
        "checks": [
            "La classificació de quasi-identificadors és adequada per al context del centre.",
            "El valor de k escollit és suficient per al nivell de risc acceptat.",
            "Les generalitzacions aplicades preserven la utilitat analítica necessària.",
            "Les variables 'no identificatives' no suposen un risc addicional.",
            "El dataset final s'utilitza exclusivament per a les finalitats del datathon.",
        ],
        "legal_title": "Marc Legal Aplicable",
        "legal_items": [
            "RGPD (Reglament UE 2016/679), Art. 89 i Recital 26 — dades anonimitzades fora del seu àmbit.",
            "Llei Orgànica 3/2018 (LOPDGDD) — transposició espanyola del RGPD.",
            "Dictamen 05/2014 del Grup de Treball de l'Art. 29 — k-anonimitat com a tècnica reconeguda.",
            "ISO/IEC 29101:2018 i guies ENISA sobre anonimització de dades sanitàries.",
        ],
        "method_title": "Tècnica: K-Anonimitat",
        "method_body": (
            "La k-anonimitat garanteix que cada combinació de valors dels quasi-identificadors "
            "aparegui en almenys k registres. Això implica que, per a qualsevol perfil definit "
            "pels quasi-identificadors, existeixen com a mínim k-1 individus amb el mateix perfil, "
            "fent estadísticament difícil la singularització d'un individu concret."
        ),
        "hash_title": "Transformació Aplicada: Hash SHA-256",
        "hash_body": (
            "L'identificador de pacient s'ha transformat amb hash SHA-256 (12 caràcters hex, "
            "prefix H-). La transformació és irreversible: no és possible recuperar l'identificador "
            "original. El hash és determinista, cosa que permet el seguiment longitudinal dins del "
            "dataset però no la identificació externa."
        ),
        "hash_warning": (
            "Advertiment: el hash no és xifrat. Si un atacant disposés dels identificadors originals, "
            "podria verificar-los per força bruta. La protecció principal recau en la k-anonimitat."
        ),
        "date_title": "Transformació Aplicada: Delta de Dies",
        "date_body": (
            "Cada data s'ha convertit en el nombre de dies transcorreguts des de la primera visita "
            "de cada pacient (valor 0). Aquesta transformació preserva els intervals temporals entre "
            "visites (utilitat analítica) però destrueix la data absoluta, eliminant el risc de "
            "correlació amb fonts externes (necrologies, noticies d'hospitalitzacions, etc.)."
        ),
        "imp_title": "Estratègia d'Imputació",
        "imp_body": (
            "Els valors absents (NaN) als quasi-identificadors s'han imputat per evitar que "
            "pacients sense dada formin grups únics i siguin suprimits innecessàriament: "
            "variables categòriques → 'Desconocido'; variables numèriques → mediana observada."
        ),
        "limit_items": [
            "Dependència del context: la idoneïtat dels quasi-IDs depèn del centre i el datathon específic.",
            "La k-anonimitat no protegeix contra atacs d'homogeneïtat ni de background knowledge.",
            "Risc residual: amb k baix (k<5) el risc no és nul. Es recomana k ≥ 5 per a ús públic.",
            "Variables no identificatives mantingudes sense canvis: revisar combinacions potencialment identificatives.",
            "Dataset petit (<1.000 pacients): risc augmentat de grups únics amb QIs específics.",
            "Imputació: els valors imputats introdueixen un supòsit que pot no ser correcte clínicament.",
        ],
        "conclusion_body": lambda d: (
            f"S'ha aplicat k-anonimitat (k={d['k']}) sobre {d['n_patients_orig']} pacients originals. "
            f"El dataset final conté {d['n_patients_final']} pacients "
            f"({d['pct_suppressed']}% de pèrdua) i {d['n_records_final']} registres, "
            f"amb {len(d['quasi_ids'])} quasi-identificador(s) generalitzat(s)."
        ),
        "page": "Pàgina",
        "conform_mark": "✓", "suppress_mark": "✗",
    },
    "es": {
        "title":         "Informe de Anonimización de Datos Clínicos",
        "subtitle_ca":   "Preparado para el Departamento de Protección de Datos",
        "generated":     "Generado el",
        "file":          "Fichero",
        "tool":          "Herramienta: Datathon Anonymizer v2.0",
        "confidential":  "DOCUMENTO CONFIDENCIAL · USO INTERNO",
        "toc":           "Índice de contenidos",
        "s1": "1. Resumen Ejecutivo",
        "s2": "2. Dataset Original",
        "s3": "3. Marco Legal y Metodológico",
        "s4": "4. Proceso de Anonimización",
        "s4a": "4.1 Identificador de Paciente",
        "s4b": "4.2 Tratamiento de Fechas",
        "s4c": "4.3 Imputación de Valores Ausentes",
        "s4d": "4.4 Clasificación de Variables",
        "s4e": "4.5 Generalización de Cuasi-Identificadores",
        "s4f": "4.6 Aplicación de la K-Anonimidad",
        "s5": "5. Resultados y Métricas",
        "s6": "6. Limitaciones Metodológicas",
        "s7": "7. Conclusiones y Checklist",
        "param": "Parámetro", "value": "Valor",
        "pat_orig": "Pacientes originales", "pat_final": "Pacientes finales",
        "pat_supp": "Pacientes eliminados", "pct_supp": "Porcentaje eliminado",
        "rec_orig": "Registros originales", "rec_final": "Registros finales",
        "k_val": "Valor de k", "quasi_ids": "Cuasi-identificadores",
        "col_orig": "Columna original", "col_can": "Columna canónica", "col_desc": "Descripción",
        "col_patient": "Identificador único del paciente",
        "col_date": "Fecha de la visita",
        "col_item": "Nombre de la variable clínica",
        "col_value": "Valor observado",
        "stat_patients": "Pacientes únicos", "stat_records": "Registros totales",
        "stat_items": "Variables (ítems)", "stat_dates": "Rango de fechas",
        "stat_visits": "Visitas por paciente",
        "var": "Variable", "classif": "Clasificación",
        "quasi_label": "🔍 Cuasi-identificador", "nonid_label": "✅ No identificativo",
        "direct_label": "🔑 Identificador directo (hash)", "date_label": "📅 Fecha (delta)",
        "gen_type": "Tipo", "gen_cuts": "Puntos de corte", "gen_intervals": "Intervalos",
        "gen_mapping": "Mapeo", "gen_unmapped": "No asignados",
        "gen_bins": "Intervalos numéricos", "gen_map": "Mapeo de categorías",
        "eq_total": "Total de grupos", "eq_conform": "Grupos conformes (≥k)",
        "eq_supp": "Grupos suprimidos (<k)", "eq_min": "Tamaño mínimo",
        "eq_max": "Tamaño máximo", "eq_mean": "Tamaño medio",
        "dist_size": "Tamaño del grupo", "dist_groups": "Número de grupos", "dist_patients": "Pacientes",
        "supp_title": "Grupos suprimidos (hasta 20)",
        "imp_var": "Variable", "imp_n": "Registros imputados", "imp_strat": "Estrategia",
        "no_imp": "Ningún valor ausente detectado en los cuasi-identificadores.",
        "no_supp": "Ningún grupo suprimido.",
        "flow_orig": "Dataset original", "flow_imp": "Tras imputación",
        "flow_supp": "Suprimidos", "flow_final": "Dataset final",
        "checklist_title": "Verificación para el Departamento de Protección de Datos",
        "checks": [
            "La clasificación de cuasi-identificadores es adecuada para el contexto del centro.",
            "El valor de k elegido es suficiente para el nivel de riesgo aceptado.",
            "Las generalizaciones aplicadas preservan la utilidad analítica necesaria.",
            "Las variables 'no identificativas' no suponen un riesgo adicional.",
            "El dataset final se utiliza exclusivamente para las finalidades del datathon.",
        ],
        "legal_title": "Marco Legal Aplicable",
        "legal_items": [
            "RGPD (Reglamento UE 2016/679), Art. 89 y Considerando 26 — datos anonimizados fuera de su ámbito.",
            "Ley Orgánica 3/2018 (LOPDGDD) — transposición española del RGPD.",
            "Dictamen 05/2014 del Grupo de Trabajo del Art. 29 — k-anonimidad como técnica reconocida.",
            "ISO/IEC 29101:2018 y guías ENISA sobre anonimización de datos sanitarios.",
        ],
        "method_title": "Técnica: K-Anonimidad",
        "method_body": (
            "La k-anonimidad garantiza que cada combinación de valores de los cuasi-identificadores "
            "aparezca en al menos k registros. Esto implica que, para cualquier perfil definido "
            "por los cuasi-identificadores, existen como mínimo k-1 individuos con el mismo perfil, "
            "haciendo estadísticamente difícil la singularización de un individuo concreto."
        ),
        "hash_title": "Transformación Aplicada: Hash SHA-256",
        "hash_body": (
            "El identificador de paciente se ha transformado con hash SHA-256 (12 caracteres hex, "
            "prefijo H-). La transformación es irreversible: no es posible recuperar el identificador "
            "original. El hash es determinista, permitiendo el seguimiento longitudinal dentro del "
            "dataset pero no la identificación externa."
        ),
        "hash_warning": (
            "Advertencia: el hash no es cifrado. Si un atacante dispusiera de los identificadores "
            "originales, podría verificarlos por fuerza bruta. La protección principal recae en la k-anonimidad."
        ),
        "date_title": "Transformación Aplicada: Delta de Días",
        "date_body": (
            "Cada fecha se ha convertido en el número de días transcurridos desde la primera visita "
            "de cada paciente (valor 0). Esta transformación preserva los intervalos temporales entre "
            "visitas (utilidad analítica) pero destruye la fecha absoluta, eliminando el riesgo de "
            "correlación con fuentes externas."
        ),
        "imp_title": "Estrategia de Imputación",
        "imp_body": (
            "Los valores ausentes (NaN) en los cuasi-identificadores se han imputado para evitar que "
            "pacientes sin dato formen grupos únicos y sean suprimidos innecesariamente: "
            "variables categóricas → 'Desconocido'; variables numéricas → mediana observada."
        ),
        "limit_items": [
            "Dependencia del contexto: la idoneidad de los cuasi-IDs depende del centro y el datathon específico.",
            "La k-anonimidad no protege contra ataques de homogeneidad ni de background knowledge.",
            "Riesgo residual: con k bajo (k<5) el riesgo no es nulo. Se recomienda k ≥ 5 para uso público.",
            "Variables no identificativas mantenidas sin cambios: revisar combinaciones potencialmente identificativas.",
            "Dataset pequeño (<1.000 pacientes): riesgo aumentado de grupos únicos con QIs específicos.",
            "Imputación: los valores imputados introducen un supuesto que puede no ser correcto clínicamente.",
        ],
        "conclusion_body": lambda d: (
            f"Se ha aplicado k-anonimidad (k={d['k']}) sobre {d['n_patients_orig']} pacientes originales. "
            f"El dataset final contiene {d['n_patients_final']} pacientes "
            f"({d['pct_suppressed']}% de pérdida) y {d['n_records_final']} registros, "
            f"con {len(d['quasi_ids'])} cuasi-identificador(es) generalizado(s)."
        ),
        "page": "Página",
        "conform_mark": "✓", "suppress_mark": "✗",
    },
    "en": {
        "title":         "Clinical Data Anonymization Report",
        "subtitle_ca":   "Prepared for the Data Protection Department",
        "generated":     "Generated on",
        "file":          "File",
        "tool":          "Tool: Datathon Anonymizer v2.0",
        "confidential":  "CONFIDENTIAL DOCUMENT · INTERNAL USE",
        "toc":           "Table of Contents",
        "s1": "1. Executive Summary",
        "s2": "2. Original Dataset",
        "s3": "3. Legal and Methodological Framework",
        "s4": "4. Anonymization Process",
        "s4a": "4.1 Patient Identifier",
        "s4b": "4.2 Date Treatment",
        "s4c": "4.3 Missing Value Imputation",
        "s4d": "4.4 Variable Classification",
        "s4e": "4.5 Quasi-Identifier Generalization",
        "s4f": "4.6 K-Anonymity Application",
        "s5": "5. Results and Metrics",
        "s6": "6. Methodological Limitations",
        "s7": "7. Conclusions and Checklist",
        "param": "Parameter", "value": "Value",
        "pat_orig": "Original patients", "pat_final": "Final patients",
        "pat_supp": "Suppressed patients", "pct_supp": "Suppression rate",
        "rec_orig": "Original records", "rec_final": "Final records",
        "k_val": "K value", "quasi_ids": "Quasi-identifiers",
        "col_orig": "Original column", "col_can": "Canonical column", "col_desc": "Description",
        "col_patient": "Unique patient identifier",
        "col_date": "Visit date",
        "col_item": "Clinical variable name",
        "col_value": "Observed value",
        "stat_patients": "Unique patients", "stat_records": "Total records",
        "stat_items": "Variables (items)", "stat_dates": "Date range",
        "stat_visits": "Visits per patient",
        "var": "Variable", "classif": "Classification",
        "quasi_label": "Quasi-identifier", "nonid_label": "Non-identifying",
        "direct_label": "Direct identifier (hash)", "date_label": "Date (delta)",
        "gen_type": "Type", "gen_cuts": "Cut points", "gen_intervals": "Intervals",
        "gen_mapping": "Mapping", "gen_unmapped": "Unassigned",
        "gen_bins": "Numeric ranges", "gen_map": "Category mapping",
        "eq_total": "Total groups", "eq_conform": "Conforming groups (>=k)",
        "eq_supp": "Suppressed groups (<k)", "eq_min": "Min size",
        "eq_max": "Max size", "eq_mean": "Mean size",
        "dist_size": "Group size", "dist_groups": "Number of groups", "dist_patients": "Patients",
        "supp_title": "Suppressed groups (up to 20)",
        "imp_var": "Variable", "imp_n": "Imputed records", "imp_strat": "Strategy",
        "no_imp": "No missing values detected in quasi-identifiers.",
        "no_supp": "No groups suppressed.",
        "flow_orig": "Original dataset", "flow_imp": "After imputation",
        "flow_supp": "Suppressed", "flow_final": "Final dataset",
        "checklist_title": "Data Protection Department Verification",
        "checks": [
            "The quasi-identifier classification is appropriate for the center's context.",
            "The chosen k value is sufficient for the accepted risk level.",
            "The applied generalizations preserve the necessary analytical utility.",
            "'Non-identifying' variables do not pose additional risk.",
            "The final dataset is used exclusively for the datathon's stated purposes.",
        ],
        "legal_title": "Applicable Legal Framework",
        "legal_items": [
            "GDPR (EU Regulation 2016/679), Art. 89 and Recital 26 — anonymized data outside its scope.",
            "Article 29 Working Party Opinion 05/2014 — k-anonymity as a recognized technique.",
            "ISO/IEC 29101:2018 and ENISA guidelines on health data anonymization.",
        ],
        "method_title": "Technique: K-Anonymity",
        "method_body": (
            "K-anonymity guarantees that each combination of quasi-identifier values appears in at "
            "least k records. For any profile defined by quasi-identifiers, at least k-1 individuals "
            "share exactly the same profile, making statistical singling-out of any individual difficult."
        ),
        "hash_title": "Applied Transformation: SHA-256 Hash",
        "hash_body": (
            "The patient identifier has been transformed with SHA-256 hash (12 hex chars, prefix H-). "
            "The transformation is irreversible: the original identifier cannot be recovered. "
            "The hash is deterministic, allowing longitudinal tracking within the dataset but not external identification."
        ),
        "hash_warning": (
            "Warning: the hash is not encryption. If an attacker had access to original identifiers, "
            "they could verify them by brute force. The main protection relies on k-anonymity."
        ),
        "date_title": "Applied Transformation: Day Delta",
        "date_body": (
            "Each date has been converted to the number of days elapsed since each patient's first visit "
            "(value 0). This preserves temporal intervals between visits (analytical utility) but "
            "destroys the absolute date, eliminating correlation risk with external sources."
        ),
        "imp_title": "Imputation Strategy",
        "imp_body": (
            "Missing values (NaN) in quasi-identifiers have been imputed to prevent patients without "
            "data from forming unique groups and being unnecessarily suppressed: "
            "categorical variables -> 'Desconocido'; numeric variables -> observed median."
        ),
        "limit_items": [
            "Context dependency: quasi-ID suitability depends on the specific center and datathon.",
            "K-anonymity does not protect against homogeneity or background knowledge attacks.",
            "Residual risk: with low k (k<5) risk is reduced but not zero. k >= 5 recommended for public use.",
            "Non-identifying variables kept unchanged: review potentially identifying combinations.",
            "Small dataset (<1,000 patients): increased risk of unique groups with specific QIs.",
            "Imputation: imputed values introduce assumptions that may not be clinically correct.",
        ],
        "conclusion_body": lambda d: (
            f"K-anonymity (k={d['k']}) has been applied to {d['n_patients_orig']} original patients. "
            f"The final dataset contains {d['n_patients_final']} patients "
            f"({d['pct_suppressed']}% loss) and {d['n_records_final']} records, "
            f"with {len(d['quasi_ids'])} generalized quasi-identifier(s)."
        ),
        "page": "Page",
        "conform_mark": "✓", "suppress_mark": "✗",
    },
}


# ── Estils ────────────────────────────────────────────────────────────────────
def _build_styles():
    base = getSampleStyleSheet()
    styles = {}

    styles["cover_title"] = ParagraphStyle("cover_title",
        fontName="Helvetica-Bold", fontSize=24, textColor=C_WHITE,
        spaceAfter=12, leading=30, alignment=TA_CENTER)

    styles["cover_sub"] = ParagraphStyle("cover_sub",
        fontName="Helvetica", fontSize=11, textColor=HexColor("#94b8d0"),
        spaceAfter=8, alignment=TA_CENTER)

    styles["cover_meta"] = ParagraphStyle("cover_meta",
        fontName="Helvetica", fontSize=9, textColor=HexColor("#4d6e8a"),
        spaceAfter=4, alignment=TA_CENTER)

    styles["section"] = ParagraphStyle("section",
        fontName="Helvetica-Bold", fontSize=14, textColor=C_SECTION,
        spaceBefore=20, spaceAfter=8, leading=18,
        borderPad=4)

    styles["subsection"] = ParagraphStyle("subsection",
        fontName="Helvetica-Bold", fontSize=11, textColor=HexColor("#003366"),
        spaceBefore=14, spaceAfter=6)

    styles["body"] = ParagraphStyle("body",
        fontName="Helvetica", fontSize=9, textColor=C_BODY_TEXT,
        spaceAfter=6, leading=14)

    styles["body_bold"] = ParagraphStyle("body_bold",
        fontName="Helvetica-Bold", fontSize=9, textColor=C_BODY_TEXT,
        spaceAfter=6, leading=14)

    styles["bullet"] = ParagraphStyle("bullet",
        fontName="Helvetica", fontSize=9, textColor=C_BODY_TEXT,
        spaceAfter=4, leading=13, leftIndent=16, bulletIndent=6)

    styles["warning"] = ParagraphStyle("warning",
        fontName="Helvetica-Oblique", fontSize=8.5, textColor=HexColor("#8a5500"),
        spaceAfter=6, leading=12, leftIndent=8)

    styles["code"] = ParagraphStyle("code",
        fontName="Courier", fontSize=8, textColor=HexColor("#003d80"),
        spaceAfter=4, leading=12)

    styles["footer"] = ParagraphStyle("footer",
        fontName="Helvetica", fontSize=7.5, textColor=HexColor("#888888"),
        alignment=TA_CENTER)

    styles["check_ok"] = ParagraphStyle("check_ok",
        fontName="Helvetica", fontSize=9, textColor=HexColor("#1a5c30"),
        spaceAfter=5, leading=13, leftIndent=20)

    return styles


# ── Flowable de línia de separació ────────────────────────────────────────────
def _hr(color=C_ACCENT, thickness=1.5):
    return HRFlowable(width="100%", thickness=thickness, color=color,
                      spaceAfter=8, spaceBefore=4)


# ── Helpers de taula ──────────────────────────────────────────────────────────
def _tbl(data, col_widths, hdr_color=C_DARK_HDR, alt_color=HexColor("#eef3fa")):
    """Taula amb capçalera fosca i files alternes."""
    style = [
        ("BACKGROUND",  (0, 0), (-1, 0), hdr_color),
        ("TEXTCOLOR",   (0, 0), (-1, 0), C_WHITE),
        ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, 0), 8),
        ("FONTNAME",    (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",    (0, 1), (-1, -1), 8),
        ("TEXTCOLOR",   (0, 1), (-1, -1), C_BODY_TEXT),
        ("ROWBACKGROUND", (0, 1), (-1, -1), [C_WHITE, alt_color]),
        ("GRID",        (0, 0), (-1, -1), 0.4, HexColor("#c5d5e8")),
        ("TOPPADDING",  (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
    ]
    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle(style))
    return t


def _metric_box(label, value, color=C_ACCENT):
    """Caixa de mètrica destacada."""
    data = [[Paragraph(f'<font size="18" color="{color.hexval()}">'
                       f'<b>{value}</b></font>', getSampleStyleSheet()["Normal"]),
             Paragraph(f'<font size="8" color="#555555">{label}</font>',
                       getSampleStyleSheet()["Normal"])]]
    t = Table(data, colWidths=[3 * cm, 11 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), HexColor("#f0f6ff")),
        ("BOX",        (0, 0), (-1, -1), 1, HexColor("#c5d5e8")),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return t


# ── Capçalera i peu de pàgina ─────────────────────────────────────────────────
def _header_footer(canvas, doc, L, filename, now):
    canvas.saveState()
    w, h = A4

    # Capçalera
    canvas.setFillColor(C_DARK_HDR)
    canvas.rect(0, h - 1.5 * cm, w, 1.5 * cm, fill=1, stroke=0)
    canvas.setFillColor(C_ACCENT)
    canvas.rect(0, h - 1.5 * cm, 0.5 * cm, 1.5 * cm, fill=1, stroke=0)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.setFillColor(C_WHITE)
    canvas.drawString(1 * cm, h - 0.9 * cm, L["title"])
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(HexColor("#7a9ab8"))
    canvas.drawRightString(w - 1 * cm, h - 0.9 * cm, filename)

    # Peu
    canvas.setFillColor(HexColor("#eeeeee"))
    canvas.rect(0, 0, w, 1 * cm, fill=1, stroke=0)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(HexColor("#888888"))
    canvas.drawString(1 * cm, 0.35 * cm, L["tool"])
    canvas.drawCentredString(w / 2, 0.35 * cm, now)
    canvas.drawRightString(w - 1 * cm, 0.35 * cm,
                           f"{L['page']} {doc.page}")
    canvas.restoreState()


# ── Generació principal ───────────────────────────────────────────────────────
def generate_pdf_report(
    lang: str,
    filename: str,
    col_mapping: dict,
    classifications: dict,
    generalizations: dict,
    imputation_log: dict,
    metrics: dict,
    date_range: dict,
    all_items: list,
    orig_pacient_col: str = "patient_id",
) -> bytes:
    """Retorna els bytes del PDF generat."""

    lang = lang if lang in _LABELS else "ca"
    L    = _LABELS[lang]
    S    = _build_styles()
    now  = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    eq       = metrics.get("equivalence_classes", {})
    quasi    = metrics.get("quasi_id_items", [])
    col_inv  = {v: k for k, v in col_mapping.items()}   # canònic → original

    d = {
        "k":               metrics.get("k_used", "?"),
        "n_patients_orig": metrics.get("n_patients_orig", 0),
        "n_patients_final":metrics.get("n_patients_final", 0),
        "n_suppressed":    metrics.get("n_suppressed_patients", 0),
        "pct_suppressed":  metrics.get("pct_suppressed", 0),
        "n_records_orig":  metrics.get("n_records_orig", 0),
        "n_records_final": metrics.get("n_records_final", 0),
        "quasi_ids":       quasi,
    }

    buf  = io.BytesIO()
    PAGE_W = A4[0] - 4 * cm   # amplada útil

    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2.5 * cm, bottomMargin=1.8 * cm,
        title=L["title"], author="Datathon Anonymizer v2.0",
    )

    story = []
    on_page = lambda c, d: _header_footer(c, d, L, filename, now)

    # ── PORTADA ───────────────────────────────────────────────────────────────
    story.append(Spacer(1, 3 * cm))

    # Bloc de color de portada
    cover_data = [[
        Paragraph(L["title"], S["cover_title"]),
    ]]
    cover_tbl = Table(cover_data, colWidths=[PAGE_W])
    cover_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C_DARK_HDR),
        ("TOPPADDING", (0, 0), (-1, -1), 30),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 30),
        ("LEFTPADDING", (0, 0), (-1, -1), 20),
        ("RIGHTPADDING", (0, 0), (-1, -1), 20),
        ("LINEBELOW", (0, 0), (-1, 0), 4, C_ACCENT),
    ]))
    story.append(cover_tbl)
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph(L["subtitle_ca"], S["cover_sub"]))
    story.append(Spacer(1, 2 * cm))

    # Taula de metadades de portada
    meta_data = [
        [L["file"] + ":", filename],
        [L["generated"] + ":", now],
        [L["tool"] + ":", ""],
    ]
    meta_tbl = Table([[L["file"] + ":", Paragraph(f"<b>{filename}</b>", S["body"])],
                      [L["generated"] + ":", now],
                      ["k =", Paragraph(f"<b>{d['k']}</b>", S["body"])],
                      [L["confidential"], ""]],
                     colWidths=[5 * cm, PAGE_W - 5 * cm])
    meta_tbl.setStyle(TableStyle([
        ("FONTNAME",    (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME",    (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE",    (0, 0), (-1, -1), 9),
        ("TEXTCOLOR",   (0, 0), (-1, -2), C_BODY_TEXT),
        ("TEXTCOLOR",   (0, -1), (-1, -1), HexColor("#8a0000")),
        ("FONTNAME",    (0, -1), (-1, -1), "Helvetica-BoldOblique"),
        ("TOPPADDING",  (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(meta_tbl)
    story.append(PageBreak())

    # ── S1: RESUM EXECUTIU ────────────────────────────────────────────────────
    story.append(Paragraph(L["s1"], S["section"]))
    story.append(_hr())

    pct_color = C_SUCCESS.hexval() if d["pct_suppressed"] < 5 else \
                C_AMBER.hexval() if d["pct_suppressed"] < 20 else C_DANGER.hexval()

    summary_data = [
        [L["param"], L["value"]],
        [L["pat_orig"],  str(d["n_patients_orig"])],
        [L["pat_final"], str(d["n_patients_final"])],
        [L["pat_supp"],  f'{d["n_suppressed"]} ({d["pct_suppressed"]}%)'],
        [L["rec_orig"],  str(d["n_records_orig"])],
        [L["rec_final"], str(d["n_records_final"])],
        [L["k_val"],     str(d["k"])],
        [L["quasi_ids"], ", ".join(quasi) if quasi else "—"],
    ]
    story.append(_tbl(summary_data, [8 * cm, PAGE_W - 8 * cm]))
    story.append(Spacer(1, 0.4 * cm))

    # ── S2: DATASET ORIGINAL ─────────────────────────────────────────────────
    story.append(Paragraph(L["s2"], S["section"]))
    story.append(_hr())

    col_data = [
        [L["col_orig"], L["col_can"], L["col_desc"]],
        [col_inv.get("pacient", "pacient"), "pacient", L["col_patient"]],
        [col_inv.get("data",    "data"),    "data",    L["col_date"]],
        [col_inv.get("item",    "item"),    "item",    L["col_item"]],
        [col_inv.get("valor",   "valor"),   "valor",   L["col_value"]],
    ]
    story.append(_tbl(col_data, [5 * cm, 4 * cm, PAGE_W - 9 * cm]))
    story.append(Spacer(1, 0.3 * cm))

    dr = date_range or {}
    v  = metrics.get("visits_per_patient_orig", {})
    stats_data = [
        [L["stat_patients"],  str(d["n_patients_orig"])],
        [L["stat_records"],   str(d["n_records_orig"])],
        [L["stat_items"],     str(metrics.get("n_items", "—"))],
        [L["stat_dates"],     f'{dr.get("min","—")} → {dr.get("max","—")}'],
        [L["stat_visits"],    f'min {v.get("min","—")} / max {v.get("max","—")} / '
                              f'mean {v.get("mean","—")}'],
    ]
    story.append(_tbl(stats_data, [7 * cm, PAGE_W - 7 * cm]))
    story.append(Spacer(1, 0.3 * cm))

    # Variables incloses
    items_text = "  ·  ".join(f"`{i}`" for i in sorted(all_items))
    story.append(Paragraph(
        "<font name='Courier' size='7.5' color='#003d80'>" +
        "  ·  ".join(sorted(all_items)) + "</font>",
        S["body"]))
    story.append(Spacer(1, 0.3 * cm))

    # ── S3: MARC LEGAL ───────────────────────────────────────────────────────
    story.append(Paragraph(L["s3"], S["section"]))
    story.append(_hr())
    story.append(Paragraph(L["legal_title"], S["subsection"]))
    for item in L["legal_items"]:
        story.append(Paragraph(f"• {item}", S["bullet"]))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(L["method_title"], S["subsection"]))
    story.append(Paragraph(L["method_body"], S["body"]))

    # ── S4: PROCÉS ───────────────────────────────────────────────────────────
    story.append(Paragraph(L["s4"], S["section"]))
    story.append(_hr())

    # 4.1 Hash
    story.append(Paragraph(L["s4a"], S["subsection"]))
    story.append(Paragraph(L["hash_title"], S["body_bold"]))
    story.append(Paragraph(L["hash_body"], S["body"]))
    story.append(Paragraph(f"⚠  {L['hash_warning']}", S["warning"]))

    # 4.2 Dates
    story.append(Paragraph(L["s4b"], S["subsection"]))
    story.append(Paragraph(L["date_title"], S["body_bold"]))
    story.append(Paragraph(L["date_body"], S["body"]))

    # 4.3 Imputació
    story.append(Paragraph(L["s4c"], S["subsection"]))
    story.append(Paragraph(L["imp_title"], S["body_bold"]))
    story.append(Paragraph(L["imp_body"], S["body"]))
    if imputation_log:
        imp_data = [[L["imp_var"], L["imp_n"], L["imp_strat"]]]
        for item, info in imputation_log.items():
            imp_data.append([item, str(info["n_imputed"]), info["strategy"]])
        story.append(_tbl(imp_data, [7 * cm, 3 * cm, PAGE_W - 10 * cm]))
    else:
        story.append(Paragraph(L["no_imp"], S["body"]))

    # 4.4 Classificació
    story.append(Paragraph(L["s4d"], S["subsection"]))
    cls_data = [[L["var"], L["classif"]],
                ["pacient", L["direct_label"]],
                ["data",    L["date_label"]]]
    for item, role in sorted(classifications.items()):
        lbl = L["quasi_label"] if role == "quasi_id" else L["nonid_label"]
        cls_data.append([item, lbl])
    story.append(_tbl(cls_data, [9 * cm, PAGE_W - 9 * cm]))

    # 4.5 Generalitzacions
    story.append(Paragraph(L["s4e"], S["subsection"]))
    if not quasi:
        story.append(Paragraph(L["no_imp"], S["body"]))
    else:
        for qi in quasi:
            cfg = generalizations.get(qi, {})
            t   = cfg.get("type", "")
            story.append(Paragraph(f"<b>{qi}</b>", S["body_bold"]))
            if t == "bins":
                bins   = cfg.get("bins", [])
                labels = cfg.get("labels", [])
                gen_data = [[L["gen_cuts"], L["gen_intervals"]]]
                for i, lbl in enumerate(labels):
                    lo = bins[i] if i < len(bins) else "?"
                    hi = bins[i+1] if i+1 < len(bins) else "?"
                    gen_data.append([f"[{lo}, {hi})", lbl])
                story.append(_tbl(gen_data, [5 * cm, PAGE_W - 5 * cm]))
            elif t == "mapping":
                mapping = cfg.get("mapping", {})
                unmapped = cfg.get("unmapped_label", "Desconocido")
                map_data = [[L["gen_mapping"], "→ " + L["gen_intervals"]]]
                for orig, dest in sorted(mapping.items()):
                    map_data.append([orig, dest])
                map_data.append([f"({L['gen_unmapped']})", unmapped])
                story.append(_tbl(map_data, [8 * cm, PAGE_W - 8 * cm]))
            else:
                story.append(Paragraph("—", S["body"]))
            story.append(Spacer(1, 0.2 * cm))

    # 4.6 K-anonimitat
    story.append(Paragraph(L["s4f"], S["subsection"]))
    story.append(Paragraph(
        f"k = <b>{d['k']}</b>. " + (
            "Tots els grups amb menys de " if lang == "ca" else
            "Todos los grupos con menos de " if lang == "es" else
            "All groups with fewer than "
        ) + f"{d['k']} " + (
            "pacients han estat suprimits." if lang == "ca" else
            "pacientes han sido suprimidos." if lang == "es" else
            "patients have been suppressed."
        ), S["body"]))

    # ── S5: RESULTATS ─────────────────────────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph(L["s5"], S["section"]))
    story.append(_hr())

    # Flux de pacients
    flow_data = [
        [L["flow_orig"],  str(d["n_patients_orig"]),  str(d["n_records_orig"])],
        [L["flow_imp"],   str(d["n_patients_orig"]),  "—"],
        [L["flow_supp"],  f'-{d["n_suppressed"]}',    "—"],
        [L["flow_final"], str(d["n_patients_final"]), str(d["n_records_final"])],
    ]
    flow_tbl = Table(
        [[L["param"], L["pat_orig"].replace(" originals","").replace(" originales","").replace(" original",""),
          L["rec_orig"].replace(" originals","").replace(" originales","").replace(" original","")]] + flow_data,
        colWidths=[6 * cm, 4 * cm, PAGE_W - 10 * cm]
    )
    flow_tbl.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, 0), C_DARK_HDR),
        ("TEXTCOLOR",   (0, 0), (-1, 0), C_WHITE),
        ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME",    (0, 1), (-1, -1), "Helvetica"),
        ("FONTNAME",    (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, -1), 8.5),
        ("TEXTCOLOR",   (0, 1), (-1, -1), C_BODY_TEXT),
        ("BACKGROUND",  (0, -1), (-1, -1), HexColor("#e8f4ee")),
        ("GRID",        (0, 0), (-1, -1), 0.4, HexColor("#c5d5e8")),
        ("TOPPADDING",  (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("ALIGN",       (1, 0), (-1, -1), "CENTER"),
    ]))
    story.append(flow_tbl)
    story.append(Spacer(1, 0.4 * cm))

    # Classes d'equivalència
    eq_data = [
        [L["eq_total"],   str(eq.get("total_groups", "—"))],
        [L["eq_conform"], str(eq.get("conforming_groups", "—"))],
        [L["eq_supp"],    str(eq.get("suppressed_groups_count", "—"))],
        [L["eq_min"],     str(eq.get("min_size", "—"))],
        [L["eq_max"],     str(eq.get("max_size", "—"))],
        [L["eq_mean"],    str(eq.get("mean_size", "—"))],
    ]
    story.append(_tbl([[L["param"], L["value"]]] + eq_data,
                      [9 * cm, PAGE_W - 9 * cm]))
    story.append(Spacer(1, 0.4 * cm))

    # Distribució de mides
    dist = eq.get("size_distribution", {})
    if dist:
        k_val = int(d["k"]) if str(d["k"]).isdigit() else 5
        dist_data = [[L["dist_size"], L["dist_groups"], L["dist_patients"]]]
        for sz, cnt in sorted(dist.items(), key=lambda x: int(x[0])):
            mark = L["conform_mark"] if int(sz) >= k_val else L["suppress_mark"]
            dist_data.append([f"{mark} {sz}", str(cnt), str(int(sz) * int(cnt))])
        story.append(_tbl(dist_data,
                          [4 * cm, 5 * cm, PAGE_W - 9 * cm]))
        story.append(Spacer(1, 0.3 * cm))

    # Grups suprimits
    sg = metrics.get("suppressed_groups", [])
    if sg and quasi:
        story.append(Paragraph(L["supp_title"], S["subsection"]))
        headers = quasi + ["_count_"]
        sg_data = [headers[:]] + [
            [str(g.get(h, "—")) for h in headers]
            for g in sg[:20]
        ]
        col_w = PAGE_W / len(headers)
        story.append(_tbl(sg_data, [col_w] * len(headers)))
        story.append(Spacer(1, 0.3 * cm))

    # ── S6: LIMITACIONS ───────────────────────────────────────────────────────
    story.append(Paragraph(L["s6"], S["section"]))
    story.append(_hr())
    for i, item in enumerate(L["limit_items"], 1):
        story.append(Paragraph(f"{i}. {item}", S["bullet"]))
    story.append(Spacer(1, 0.3 * cm))

    # ── S7: CONCLUSIONS ───────────────────────────────────────────────────────
    story.append(Paragraph(L["s7"], S["section"]))
    story.append(_hr())
    story.append(Paragraph(L["conclusion_body"](d), S["body"]))
    story.append(Spacer(1, 0.4 * cm))

    # Checklist
    story.append(Paragraph(L["checklist_title"], S["subsection"]))
    for check in L["checks"]:
        story.append(Paragraph(f"☐  {check}", S["check_ok"]))

    story.append(Spacer(1, 0.5 * cm))
    story.append(_hr(color=HexColor("#cccccc"), thickness=0.5))
    story.append(Paragraph(
        f"<i>{L['tool']} · {now}</i>", S["footer"]))

    # ── Construïm el PDF ──────────────────────────────────────────────────────
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    return buf.getvalue()
