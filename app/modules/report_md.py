"""
report_md.py  —  Genera l'informe d'anonimització en Markdown (ca/es/en)
"""
import datetime

T = {
"ca": {
"title":"Informe d'Anonimització de Dades Clíniques",
"subtitle":"Document tècnic per al Delegat/ada de Protecció de Dades",
"generated":"Generat el","tool":"Eina","version":"Versió",
"filename":"Fitxer processat","lang":"Idioma de l'informe","lang_val":"Català",
"s_summary":"1. Resum executiu",
"s_dataset":"2. Descripció del dataset original",
"s_methodology":"3. Metodologia d'anonimització",
"s_classification":"4. Classificació dels ítems",
"s_generalizations":"5. Generalitzacions aplicades als quasi-identificadors",
"s_imputation":"6. Tractament dels valors absents (NaN)",
"s_kanon":"7. Aplicació de la k-anonimitat",
"s_results":"8. Resultats i mètriques comparatives",
"s_eq_classes":"9. Anàlisi de les classes d'equivalència",
"s_limitations":"10. Limitacions i advertiments metodològics",
"s_conclusions":"11. Conclusions i recomanacions",
"summary_intro":("Aquest informe documenta el procés d'anonimització aplicat al dataset indicat, "
"seguint els principis de minimització de dades i protecció de la privacitat "
"establerts pel Reglament General de Protecció de Dades (RGPD, Reglament UE 2016/679) "
"i la Llei Orgànica 3/2018 de Protecció de Dades Personals i garantia dels drets digitals (LOPDGDD). "
"El procés ha estat realitzat mitjançant l'eina **Datathon Anonymizer**, "
"que opera íntegrament en local sense transmetre cap dada a serveis externs."),
"summary_method":("La tècnica principal aplicada és la **k-anonimitat**, que garanteix que cada "
"combinació de quasi-identificadors aparegui en almenys **k** registres, "
"fent estadísticament impossible la singularització d'un individu. "
"Complementàriament, s'han aplicat hash irreversible als identificadors directes "
"i conversió a delta temporal de les dates."),
"summary_result":"El resultat del procés ha estat:",
"ds_patients":"Pacients únics","ds_records":"Registres totals","ds_items":"Variables (ítems)",
"ds_date_range":"Rang de dates","ds_col_mapping":"Correspondència de columnes detectada",
"ds_original_col":"Columna original al CSV","ds_canonical_col":"Columna canònica interna",
"meth_intro":("El procés d'anonimització s'ha estructurat en les fases següents, "
"aplicades de forma seqüencial sobre el dataset:"),
"meth_step1_title":"Fase 1 — Normalització de columnes",
"meth_step1_body":("El sistema ha detectat automàticament les columnes del CSV i les ha mapejat "
"als noms canònics interns (`pacient`, `data`, `item`, `valor`), "
"acceptant variantes habituals com `patient_id`, `variable`, `value`, etc."),
"meth_step2_title":"Fase 2 — Transformació de dates",
"meth_step2_body":("Totes les dates absolutes han estat substituïdes per un **delta enter de dies** "
"calculat com la diferència respecte a la primera visita de cada pacient. "
"Això preserva els intervals temporals clínicament rellevants sense revelar dates absolutes.\n\n"
"- Primera visita de cada pacient → valor `0`\n"
"- Visites posteriors → nombre de dies transcorreguts des de la primera\n"
"- Les dates originals no es conserven en cap forma al dataset de sortida"),
"meth_step3_title":"Fase 3 — Pseudonimització de l'identificador de pacient",
"meth_step3_body":("L'identificador de pacient ha estat substituït per un **hash SHA-256** "
"truncat als primers 12 caràcters hexadecimals, amb el prefix `H-`. "
"Aquesta transformació és **irreversible**.\n\n"
"> ⚠️ Nota tècnica: El hash SHA-256 és una pseudonimització, no una anonimització "
"completa per si sola. Actua com a capa addicional de protecció sobre els identificadors directes."),
"meth_step4_title":"Fase 4 — Generalització de quasi-identificadors",
"meth_step4_body":("Els ítems classificats com a **quasi-identificadors** han estat generalitzats "
"per reduir la seva granularitat i limitar el risc de reidentificació per creuament. "
"Per a variables numèriques s'han definit intervals (binning); "
"per a variables categòriques s'han agrupat valors en categories de major amplitud."),
"meth_step5_title":"Fase 5 — Imputació de valors absents",
"meth_step5_body":("Abans d'aplicar la k-anonimitat, els valors absents (NaN) dels quasi-identificadors "
"han estat imputats:\n\n"
"- **Variables categòriques**: substituïts per `Desconocido`\n"
"- **Variables numèriques**: substituïts per la mediana del ítem al dataset"),
"meth_step6_title":"Fase 6 — K-anonimitat per supressió",
"meth_step6_body":("S'ha aplicat el model de **k-anonimitat** (Sweeney, 2002) sobre les combinacions "
"de quasi-identificadors generalitzats.\n\n"
"1. Agrupa els registres per la combinació única de valors dels quasi-identificadors\n"
"2. Identifica els grups (classes d'equivalència) amb menys de **k** pacients\n"
"3. Elimina tots els registres dels pacients en grups no conformes\n\n"
"La supressió s'aplica a nivell de **pacient complet** per preservar la coherència del dataset."),
"cls_intro":"L'usuari ha classificat cada ítem del dataset en una de les categories següents:",
"cls_quasi":"Quasi-identificadors","cls_nonid":"No identificatius (sense canvis)",
"cls_quasi_desc":("Atributs que, tot sols o combinats amb d'altres, podrien permetre la "
"reidentificació d'un individu per creuament amb fonts externes. "
"Han estat generalitzats i inclosos en el model de k-anonimitat."),
"cls_nonid_desc":("Atributs amb nul·la o molt baixa capacitat de reidentificació. "
"Es mantenen sense modificació al dataset de sortida."),
"gen_intro":"Per a cada quasi-identificador s'ha aplicat la transformació següent:",
"gen_type_bins":"Binning numèric (intervals)","gen_type_mapping":"Mapeig de categories",
"gen_bins_label":"Punts de tall","gen_labels_label":"Etiquetes resultants",
"gen_mapping_label":"Mapeig de valors","gen_unmapped":"Valors no assignats",
"gen_none":"Sense transformació (valor original)",
"imp_intro":"S'han imputat els valors absents als quasi-identificadors següents:",
"imp_none":"No s'ha detectat cap valor absent als quasi-identificadors. No s'ha aplicat imputació.",
"imp_item":"Ítem","imp_n":"Registres imputats","imp_strat":"Estratègia",
"kan_k_used":"Valor de k utilitzat","kan_quasi_items":"Quasi-identificadors considerats",
"kan_note":("La k-anonimitat garanteix que cada individu al dataset sigui "
"indistingible d'almenys **k−1** altres individus. Un valor de k={k} implica que "
"un adversari té una probabilitat màxima d'1/{k} de reidentificar un individu."),
"res_before":"Abans de l'anonimització","res_after":"Després de l'anonimització",
"res_patients":"Pacients","res_records":"Registres",
"res_suppressed_p":"Pacients suprimits","res_suppressed_r":"Registres suprimits",
"res_pct":"Percentatge de pèrdua",
"res_visits_min":"Mínim de visites/pacient","res_visits_max":"Màxim de visites/pacient",
"res_visits_mean":"Mitjana de visites/pacient",
"eq_total":"Total de grups (classes d'equivalència)","eq_conforming":"Grups conformes (≥ k)",
"eq_suppressed":"Grups suprimits (< k)","eq_min":"Mida mínima de grup",
"eq_max":"Mida màxima de grup","eq_mean":"Mida mitjana de grup",
"eq_dist_title":"Distribució de mides de grup","eq_size":"Mida del grup","eq_ngroups":"Nombre de grups",
"eq_suppressed_detail":"Detall dels grups suprimits (fins a 20)",
"eq_none_suppressed":"Cap grup ha estat suprimit. Tots els pacients compleixen el criteri de k-anonimitat.",
"lim_intro":"El procés d'anonimització presenta les limitacions inherents següents que el DPD/DPO ha de tenir en compte:",
"limitations":[
"**La k-anonimitat no protegeix contra tots els atacs de reidentificació.** En particular, no protegeix davant atacs d'homogeneïtat ni davant el coneixement de fons (background knowledge attacks). Per a protecció addicional caldria considerar l-diversitat o t-closeness.",
"**La classificació dels quasi-identificadors és contextual.** La decisió sobre quins atributs actuen com a quasi-identificadors és responsabilitat de l'organització i depèn del context d'ús del dataset i de les fonts externes potencialment accessibles per un adversari.",
"**La pseudonimització de l'identificador de pacient no és anonimització completa.** L'hash SHA-256 és irreversible sense la taula original, però si un adversari disposa d'una llista d'identificadors candidats pot verificar-los per força bruta.",
"**La imputació de valors absents pot introduir biaix analític.** La substitució per 'Desconocido' o la mediana modifica la distribució original i pot afectar anàlisis estadístiques posteriors.",
"**Les variables no identificatives no han estat modificades.** Algunes combinacions podrien contribuir a la reidentificació indirecta en determinats contextos.",
"**El dataset resultant és un dataset derivat.** No és equivalent al dataset original i no ha de ser utilitzat per a preses de decisions clíniques individuals.",
],
"con_intro":("El dataset resultant ha estat processat seguint les tècniques estàndard "
"d'anonimització estadística i és adequat per als usos previstos en el marc "
"d'un datathon o recerca amb dades de baixa sensibilitat, **sota les condicions i "
"limitacions descrites en aquest informe**."),
"con_recommendations":"Es recomana:",
"recommendations":[
"Revisar la classificació dels quasi-identificadors amb el responsable clínic i el DPD/DPO abans de compartir el dataset.",
"Documentar els usos previstos del dataset i assegurar-se que els participants signen un acord de confidencialitat i ús responsable.",
"No combinar el dataset anonimitzat amb d'altres fonts de dades sense una nova avaluació del risc de reidentificació.",
"Considerar l'augment del valor de k si el dataset es fa públic o es comparteix amb un nombre elevat de participants.",
"Conservar aquest informe juntament amb el dataset anonimitzat com a part de la documentació del tractament de dades.",
],
"con_closing":("Aquest informe ha estat generat automàticament per l'eina Datathon Anonymizer. "
"La validació final del procés d'anonimització és responsabilitat del "
"Delegat/ada de Protecció de Dades de l'organització."),
},
}

# Spanish and English copy the same structure — build them programmatically to keep file manageable
T["es"] = {
"title":"Informe de Anonimización de Datos Clínicos",
"subtitle":"Documento técnico para el Delegado/a de Protección de Datos",
"generated":"Generado el","tool":"Herramienta","version":"Versión",
"filename":"Fichero procesado","lang":"Idioma del informe","lang_val":"Castellano",
"s_summary":"1. Resumen ejecutivo","s_dataset":"2. Descripción del dataset original",
"s_methodology":"3. Metodología de anonimización","s_classification":"4. Clasificación de los ítems",
"s_generalizations":"5. Generalizaciones aplicadas a los cuasi-identificadores",
"s_imputation":"6. Tratamiento de los valores ausentes (NaN)",
"s_kanon":"7. Aplicación de la k-anonimidad","s_results":"8. Resultados y métricas comparativas",
"s_eq_classes":"9. Análisis de las clases de equivalencia",
"s_limitations":"10. Limitaciones y advertencias metodológicas",
"s_conclusions":"11. Conclusiones y recomendaciones",
"summary_intro":("Este informe documenta el proceso de anonimización aplicado al dataset indicado, "
"siguiendo los principios de minimización de datos y protección de la privacidad "
"establecidos por el Reglamento General de Protección de Datos (RGPD, Reglamento UE 2016/679) "
"y la Ley Orgánica 3/2018 de Protección de Datos Personales y garantía de los derechos digitales (LOPDGDD). "
"El proceso ha sido realizado mediante la herramienta **Datathon Anonymizer**, "
"que opera íntegramente en local sin transmitir ningún dato a servicios externos."),
"summary_method":("La técnica principal aplicada es la **k-anonimidad**, que garantiza que cada "
"combinación de cuasi-identificadores aparezca en al menos **k** registros, "
"haciendo estadísticamente imposible la singularización de un individuo."),
"summary_result":"El resultado del proceso ha sido:",
"ds_patients":"Pacientes únicos","ds_records":"Registros totales","ds_items":"Variables (ítems)",
"ds_date_range":"Rango de fechas","ds_col_mapping":"Correspondencia de columnas detectada",
"ds_original_col":"Columna original en el CSV","ds_canonical_col":"Columna canónica interna",
"meth_intro":"El proceso de anonimización se ha estructurado en las siguientes fases:",
"meth_step1_title":"Fase 1 — Normalización de columnas",
"meth_step1_body":"El sistema detectó automáticamente las columnas del CSV y las mapeó a los nombres canónicos internos, aceptando variantes habituales.",
"meth_step2_title":"Fase 2 — Transformación de fechas",
"meth_step2_body":("Todas las fechas absolutas han sido sustituidas por un **delta entero de días** "
"calculado como la diferencia respecto a la primera visita de cada paciente.\n\n"
"- Primera visita → valor `0`\n- Visitas posteriores → días transcurridos\n- Las fechas originales no se conservan"),
"meth_step3_title":"Fase 3 — Seudonimización del identificador de paciente",
"meth_step3_body":("El identificador de paciente ha sido sustituido por un **hash SHA-256** truncado (12 hex, prefijo `H-`). "
"Transformación **irreversible**.\n\n> ⚠️ El hash SHA-256 es seudonimización, no anonimización completa por sí sola."),
"meth_step4_title":"Fase 4 — Generalización de cuasi-identificadores",
"meth_step4_body":"Los ítems clasificados como cuasi-identificadores han sido generalizados mediante intervalos (numérico) o agrupación de categorías.",
"meth_step5_title":"Fase 5 — Imputación de valores ausentes",
"meth_step5_body":("Los valores ausentes de los cuasi-identificadores han sido imputados:\n\n"
"- **Categóricas**: `Desconocido`\n- **Numéricas**: mediana del ítem"),
"meth_step6_title":"Fase 6 — K-anonimidad por supresión",
"meth_step6_body":("Se ha aplicado el modelo de **k-anonimidad** (Sweeney, 2002):\n\n"
"1. Agrupa registros por combinación de cuasi-identificadores\n"
"2. Identifica grupos con menos de k pacientes\n"
"3. Elimina todos los registros de pacientes en grupos no conformes\n\n"
"La supresión se aplica a nivel de **paciente completo**."),
"cls_intro":"El usuario ha clasificado cada ítem en una de las categorías siguientes:",
"cls_quasi":"Cuasi-identificadores","cls_nonid":"No identificativos (sin cambios)",
"cls_quasi_desc":"Atributos que podrían permitir la reidentificación. Han sido generalizados e incluidos en la k-anonimidad.",
"cls_nonid_desc":"Atributos con baja capacidad de reidentificación. Se mantienen sin modificación.",
"gen_intro":"Para cada cuasi-identificador se ha aplicado la transformación siguiente:",
"gen_type_bins":"Binning numérico (intervalos)","gen_type_mapping":"Mapeo de categorías",
"gen_bins_label":"Puntos de corte","gen_labels_label":"Etiquetas resultantes",
"gen_mapping_label":"Mapeo de valores","gen_unmapped":"Valores no asignados",
"gen_none":"Sin transformación (valor original)",
"imp_intro":"Se han imputado los valores ausentes en los cuasi-identificadores siguientes:",
"imp_none":"No se detectaron valores ausentes en los cuasi-identificadores.",
"imp_item":"Ítem","imp_n":"Registros imputados","imp_strat":"Estrategia",
"kan_k_used":"Valor de k utilizado","kan_quasi_items":"Cuasi-identificadores considerados",
"kan_note":("La k-anonimidad garantiza que cada individuo sea indistinguible de al menos **k−1** otros. "
"Con k={k}, la probabilidad máxima de reidentificación es 1/{k}."),
"res_before":"Antes de la anonimización","res_after":"Después de la anonimización",
"res_patients":"Pacientes","res_records":"Registros",
"res_suppressed_p":"Pacientes suprimidos","res_suppressed_r":"Registros suprimidos",
"res_pct":"Porcentaje de pérdida",
"res_visits_min":"Mín. visitas/paciente","res_visits_max":"Máx. visitas/paciente","res_visits_mean":"Media visitas/paciente",
"eq_total":"Total de grupos","eq_conforming":"Grupos conformes (≥ k)","eq_suppressed":"Grupos suprimidos (< k)",
"eq_min":"Tamaño mínimo","eq_max":"Tamaño máximo","eq_mean":"Tamaño medio",
"eq_dist_title":"Distribución de tamaños de grupo","eq_size":"Tamaño","eq_ngroups":"Nº grupos",
"eq_suppressed_detail":"Detalle de grupos suprimidos (hasta 20)",
"eq_none_suppressed":"Ningún grupo suprimido. Todos los pacientes cumplen la k-anonimidad.",
"lim_intro":"Limitaciones inherentes que el DPD/DPO debe considerar:",
"limitations":[
"**La k-anonimidad no protege contra todos los ataques.** No protege ante ataques de homogeneidad ni de conocimiento de fondo. Considerar l-diversidad o t-closeness para mayor protección.",
"**La clasificación de cuasi-identificadores es contextual.** Depende del entorno y las fuentes externas accesibles a un adversario.",
"**La seudonimización no es anonimización completa.** Un adversario con lista de identificadores candidatos podría verificarlos.",
"**La imputación puede introducir sesgo analítico.** Los usuarios del dataset deben ser informados de este hecho.",
"**Las variables no identificativas no han sido modificadas.** Ciertas combinaciones pueden contribuir a la reidentificación indirecta.",
"**El dataset resultante es un dataset derivado.** No debe usarse para decisiones clínicas individuales.",
],
"con_intro":("El dataset resultante es adecuado para los usos previstos en un datathon, "
"**bajo las condiciones y limitaciones descritas en este informe**."),
"con_recommendations":"Se recomienda:",
"recommendations":[
"Revisar la clasificación con el responsable clínico y el DPD/DPO.",
"Documentar los usos previstos y asegurar acuerdos de uso responsable.",
"No combinar con otras fuentes sin nueva evaluación del riesgo.",
"Considerar aumentar k si el dataset se hace público.",
"Conservar este informe junto al dataset anonimizado.",
],
"con_closing":("Informe generado automáticamente por Datathon Anonymizer. "
"La validación final es responsabilidad del Delegado/a de Protección de Datos."),
}

T["en"] = {
"title":"Clinical Data Anonymization Report",
"subtitle":"Technical document for the Data Protection Officer",
"generated":"Generated on","tool":"Tool","version":"Version",
"filename":"Processed file","lang":"Report language","lang_val":"English",
"s_summary":"1. Executive Summary","s_dataset":"2. Original Dataset Description",
"s_methodology":"3. Anonymization Methodology","s_classification":"4. Item Classification",
"s_generalizations":"5. Generalizations Applied to Quasi-identifiers",
"s_imputation":"6. Missing Value Treatment (NaN)","s_kanon":"7. Application of K-anonymity",
"s_results":"8. Results and Comparative Metrics","s_eq_classes":"9. Equivalence Class Analysis",
"s_limitations":"10. Limitations and Methodological Warnings","s_conclusions":"11. Conclusions and Recommendations",
"summary_intro":("This report documents the anonymization process applied to the indicated dataset, "
"following the data minimization and privacy protection principles of the General Data Protection Regulation "
"(GDPR, EU Regulation 2016/679). The process was carried out using **Datathon Anonymizer**, "
"which operates entirely locally without transmitting any data to external services."),
"summary_method":("The main technique applied is **k-anonymity**, which guarantees that each "
"combination of quasi-identifiers appears in at least **k** records, making it statistically "
"impossible to single out an individual."),
"summary_result":"The outcome of the process was:",
"ds_patients":"Unique patients","ds_records":"Total records","ds_items":"Variables (items)",
"ds_date_range":"Date range","ds_col_mapping":"Detected column mapping",
"ds_original_col":"Original column in CSV","ds_canonical_col":"Internal canonical column",
"meth_intro":"The anonymization process was structured in the following sequential phases:",
"meth_step1_title":"Phase 1 — Column Normalization",
"meth_step1_body":"The system automatically detected CSV columns and mapped them to internal canonical names, accepting common variants.",
"meth_step2_title":"Phase 2 — Date Transformation",
"meth_step2_body":("All absolute dates were replaced by an **integer day delta** from each patient's first visit.\n\n"
"- First visit → value `0`\n- Subsequent visits → days elapsed\n- Original dates are not retained"),
"meth_step3_title":"Phase 3 — Patient Identifier Pseudonymization",
"meth_step3_body":("Patient identifier replaced by **SHA-256 hash** (12 hex chars, prefix `H-`). **Irreversible**.\n\n"
"> ⚠️ SHA-256 is pseudonymization, not complete anonymization on its own."),
"meth_step4_title":"Phase 4 — Quasi-identifier Generalization",
"meth_step4_body":"Quasi-identifier items were generalized via numeric binning or categorical grouping to reduce re-identification risk.",
"meth_step5_title":"Phase 5 — Missing Value Imputation",
"meth_step5_body":("Missing values in quasi-identifiers were imputed:\n\n"
"- **Categorical**: `Desconocido`\n- **Numeric**: item median"),
"meth_step6_title":"Phase 6 — K-anonymity by Suppression",
"meth_step6_body":("The **k-anonymity** model (Sweeney, 2002) was applied:\n\n"
"1. Group records by quasi-identifier value combination\n"
"2. Identify groups with fewer than k patients\n"
"3. Remove all records of patients in non-conforming groups\n\n"
"Suppression is applied at **full patient level** to preserve dataset coherence."),
"cls_intro":"The user classified each item into one of the following categories:",
"cls_quasi":"Quasi-identifiers","cls_nonid":"Non-identifying (unchanged)",
"cls_quasi_desc":"Attributes that could enable re-identification through linkage. Generalized and included in k-anonymity.",
"cls_nonid_desc":"Attributes with low re-identification potential. Retained unchanged in the output dataset.",
"gen_intro":"For each quasi-identifier, the following transformation was applied:",
"gen_type_bins":"Numeric binning (intervals)","gen_type_mapping":"Category mapping",
"gen_bins_label":"Cut points","gen_labels_label":"Resulting labels",
"gen_mapping_label":"Value mapping","gen_unmapped":"Unassigned values",
"gen_none":"No transformation (original value)",
"imp_intro":"Missing values were imputed for the following quasi-identifiers:",
"imp_none":"No missing values detected in quasi-identifiers. No imputation applied.",
"imp_item":"Item","imp_n":"Imputed records","imp_strat":"Strategy",
"kan_k_used":"Value of k used","kan_quasi_items":"Quasi-identifiers considered",
"kan_note":("K-anonymity guarantees each individual is indistinguishable from at least **k−1** others. "
"With k={k}, the maximum re-identification probability is 1/{k}."),
"res_before":"Before anonymization","res_after":"After anonymization",
"res_patients":"Patients","res_records":"Records",
"res_suppressed_p":"Suppressed patients","res_suppressed_r":"Suppressed records",
"res_pct":"Loss percentage",
"res_visits_min":"Min visits/patient","res_visits_max":"Max visits/patient","res_visits_mean":"Mean visits/patient",
"eq_total":"Total groups (equivalence classes)","eq_conforming":"Conforming groups (≥ k)",
"eq_suppressed":"Suppressed groups (< k)","eq_min":"Min group size","eq_max":"Max group size","eq_mean":"Mean group size",
"eq_dist_title":"Group size distribution","eq_size":"Group size","eq_ngroups":"Number of groups",
"eq_suppressed_detail":"Suppressed groups detail (up to 20)",
"eq_none_suppressed":"No groups suppressed. All patients satisfy the k-anonymity criterion.",
"lim_intro":"The following inherent limitations should be considered by the DPO:",
"limitations":[
"**K-anonymity does not protect against all re-identification attacks.** It does not protect against homogeneity or background knowledge attacks. Consider l-diversity or t-closeness for stronger guarantees.",
"**Quasi-identifier classification is context-dependent.** The organization is responsible for determining which attributes pose re-identification risks.",
"**Patient identifier pseudonymization is not complete anonymization.** An adversary with a candidate list could verify identifiers by brute force.",
"**Missing value imputation may introduce analytical bias.** Dataset users must be informed of this.",
"**Non-identifying variables were not modified.** Certain combinations may contribute to indirect re-identification.",
"**The output is a derived dataset.** It must not be used for individual clinical decisions.",
],
"con_intro":("The resulting dataset is suitable for datathon or low-sensitivity research use, "
"**subject to the conditions and limitations described in this report**."),
"con_recommendations":"Recommendations:",
"recommendations":[
"Review quasi-identifier classification with the clinical lead and DPO.",
"Document intended uses and ensure participants sign a responsible use agreement.",
"Do not combine with other data sources without a new risk assessment.",
"Consider increasing k if the dataset is made publicly available.",
"Retain this report alongside the anonymized dataset.",
],
"con_closing":("This report was automatically generated by Datathon Anonymizer. "
"Final validation is the responsibility of the organization's Data Protection Officer."),
}


def generate_markdown_report(lang, filename, col_mapping, classifications,
                              generalizations, imputation_log, metrics,
                              date_range, all_items, orig_pacient_col="patient_id"):
    t   = T.get(lang, T["ca"])
    now = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    k   = metrics.get("k_used", "?")

    quasi_items  = metrics.get("quasi_id_items", [])
    non_id_items = [i for i in all_items if classifications.get(i) != "quasi_id"]
    eq   = metrics.get("equivalence_classes", {})
    dist = eq.get("size_distribution", {})
    sg   = metrics.get("suppressed_groups", [])
    v_orig  = metrics.get("visits_per_patient_orig",  {})
    v_final = metrics.get("visits_per_patient_final", {})

    w = []
    def ln(s=""): w.append(s)

    # PORTADA
    ln(f"# {t['title']}")
    ln(f"### {t['subtitle']}")
    ln(); ln("---"); ln()
    ln(f"| | |"); ln(f"|---|---|")
    ln(f"| **{t['generated']}** | {now} |")
    ln(f"| **{t['tool']}** | Datathon Anonymizer |")
    ln(f"| **{t['version']}** | 2.0 |")
    ln(f"| **{t['filename']}** | `{filename}` |")
    ln(f"| **{t['lang']}** | {t['lang_val']} |")
    ln(); ln("---"); ln()

    # 1. RESUM EXECUTIU
    ln(f"## {t['s_summary']}"); ln()
    ln(t["summary_intro"]); ln()
    ln(t["summary_method"]); ln()
    ln(f"**{t['summary_result']}**"); ln()
    ln(f"| | {t['res_before']} | {t['res_after']} |")
    ln(f"|---|---:|---:|")
    n_po = metrics.get('n_patients_orig', 0)
    n_pf = metrics.get('n_patients_final', 0)
    n_ro = metrics.get('n_records_orig', 0)
    n_rf = metrics.get('n_records_final', 0)
    n_sp = metrics.get('n_suppressed_patients', 0)
    pct  = metrics.get('pct_suppressed', 0)
    ln(f"| **{t['res_patients']}** | {n_po:,} | {n_pf:,} |")
    ln(f"| **{t['res_records']}** | {n_ro:,} | {n_rf:,} |")
    ln(f"| **{t['res_suppressed_p']}** | — | {n_sp:,} ({pct}%) |")
    ln(f"| **k** | — | {k} |")
    ln()

    # 2. DATASET
    ln(f"## {t['s_dataset']}"); ln()
    dr_min = (date_range or {}).get("min", "?")
    dr_max = (date_range or {}).get("max", "?")
    n_it   = metrics.get('n_items', '?')
    ln(f"| {t['ds_patients']} | {t['ds_records']} | {t['ds_items']} | {t['ds_date_range']} |")
    ln(f"|---:|---:|---:|---|")
    ln(f"| {n_po:,} | {n_ro:,} | {n_it} | {dr_min} → {dr_max} |")
    ln()
    ln(f"**{t['ds_col_mapping']}**"); ln()
    ln(f"| {t['ds_original_col']} | {t['ds_canonical_col']} |")
    ln("|---|---|")
    for orig, canon in (col_mapping or {}).items():
        ln(f"| `{orig}` | `{canon}` |")
    ln()

    # 3. METODOLOGIA
    ln(f"## {t['s_methodology']}"); ln()
    ln(t["meth_intro"]); ln()
    for step in range(1, 7):
        ln(f"### {t[f'meth_step{step}_title']}"); ln()
        ln(t[f"meth_step{step}_body"]); ln()

    # 4. CLASSIFICACIÓ
    ln(f"## {t['s_classification']}"); ln()
    ln(t["cls_intro"]); ln()
    ln(f"### 🔍 {t['cls_quasi']}"); ln()
    ln(f"_{t['cls_quasi_desc']}_"); ln()
    for item in quasi_items: ln(f"- `{item}`")
    if not quasi_items: ln("_(cap)_")
    ln()
    ln(f"### ✅ {t['cls_nonid']}"); ln()
    ln(f"_{t['cls_nonid_desc']}_"); ln()
    for item in non_id_items: ln(f"- `{item}`")
    ln()

    # 5. GENERALITZACIONS
    ln(f"## {t['s_generalizations']}"); ln()
    if not quasi_items:
        ln("_(cap quasi-identificador definit)_")
    else:
        ln(t["gen_intro"]); ln()
        for item in quasi_items:
            cfg = (generalizations or {}).get(item, {})
            typ = cfg.get("type", "none")
            ln(f"### `{item}`"); ln()
            if typ == "bins":
                bins   = cfg.get("bins", [])
                labels = cfg.get("labels", [])
                ln(f"**{t['gen_type_bins']}**"); ln()
                ln(f"- {t['gen_bins_label']}: `{bins}`")
                ln(f"- {t['gen_labels_label']}: {', '.join(f'`{l}`' for l in labels)}")
                ln()
                ln(f"| Interval | {t['gen_labels_label']} |")
                ln("|---|---|")
                for i, label in enumerate(labels):
                    lo = bins[i] if i < len(bins) else "?"
                    hi = bins[i+1] if i+1 < len(bins) else "∞"
                    ln(f"| [{lo}, {hi}) | `{label}` |")
            elif typ == "mapping":
                mapping  = cfg.get("mapping", {})
                unmapped = cfg.get("unmapped_label", "Desconocido")
                ln(f"**{t['gen_type_mapping']}**"); ln()
                ln(f"| {t['gen_mapping_label']} | → |")
                ln("|---|---|")
                for ov, nv in mapping.items():
                    ln(f"| `{ov}` | `{nv}` |")
                ln(f"| _(tots els altres)_ | `{unmapped}` |")
            else:
                ln(f"_{t['gen_none']}_")
            ln()

    # 6. IMPUTACIÓ
    ln(f"## {t['s_imputation']}"); ln()
    if not imputation_log:
        ln(t["imp_none"])
    else:
        ln(t["imp_intro"]); ln()
        ln(f"| {t['imp_item']} | {t['imp_n']} | {t['imp_strat']} |")
        ln("|---|---:|---|")
        for item_name, info in imputation_log.items():
            ln(f"| `{item_name}` | {info['n_imputed']:,} | {info['strategy']} |")
    ln()

    # 7. K-ANONIMITAT
    ln(f"## {t['s_kanon']}"); ln()
    ln(f"- **{t['kan_k_used']}:** {k}")
    qi_str = ', '.join(f'`{i}`' for i in quasi_items) if quasi_items else '_(cap)_'
    ln(f"- **{t['kan_quasi_items']}:** {qi_str}")
    ln()
    note = t["kan_note"].replace("{k}", str(k))
    ln(f"> {note}"); ln()

    # 8. RESULTATS
    ln(f"## {t['s_results']}"); ln()
    ln(f"| | {t['res_before']} | {t['res_after']} |")
    ln(f"|---|---:|---:|")
    ln(f"| {t['res_patients']} | {n_po:,} | {n_pf:,} |")
    ln(f"| {t['res_records']} | {n_ro:,} | {n_rf:,} |")
    ln(f"| {t['res_suppressed_p']} | — | **{n_sp:,} ({pct}%)** |")
    ln(f"| {t['res_visits_min']} | {v_orig.get('min','?')} | {v_final.get('min','?')} |")
    ln(f"| {t['res_visits_max']} | {v_orig.get('max','?')} | {v_final.get('max','?')} |")
    ln(f"| {t['res_visits_mean']} | {v_orig.get('mean','?')} | {v_final.get('mean','?')} |")
    ln()

    # 9. CLASSES D'EQUIVALÈNCIA
    ln(f"## {t['s_eq_classes']}"); ln()
    ln(f"| | |"); ln(f"|---|---:|")
    ln(f"| {t['eq_total']} | {eq.get('total_groups','?')} |")
    ln(f"| {t['eq_conforming']} | {eq.get('conforming_groups','?')} |")
    ln(f"| {t['eq_suppressed']} | {eq.get('suppressed_groups_count','?')} |")
    ln(f"| {t['eq_min']} | {eq.get('min_size','?')} |")
    ln(f"| {t['eq_max']} | {eq.get('max_size','?')} |")
    ln(f"| {t['eq_mean']} | {eq.get('mean_size','?')} |")
    ln()
    ln(f"### {t['eq_dist_title']}"); ln()
    ln(f"| {t['eq_size']} | {t['eq_ngroups']} |"); ln("|---:|---:|")
    for sz, cnt in sorted(dist.items(), key=lambda x: int(x[0])):
        mark = "✅" if int(sz) >= int(k) else "❌"
        ln(f"| {mark} {sz} | {cnt} |")
    ln()
    ln(f"### {t['eq_suppressed_detail']}"); ln()
    if not sg:
        ln(f"✅ {t['eq_none_suppressed']}")
    else:
        headers = list(sg[0].keys())
        ln("| " + " | ".join(str(h) for h in headers) + " |")
        ln("|" + "|".join("---" for _ in headers) + "|")
        for row in sg[:20]:
            ln("| " + " | ".join(str(v) for v in row.values()) + " |")
    ln()

    # 10. LIMITACIONS
    ln(f"## {t['s_limitations']}"); ln()
    ln(t["lim_intro"]); ln()
    for i, lim in enumerate(t["limitations"], 1):
        ln(f"{i}. {lim}"); ln()

    # 11. CONCLUSIONS
    ln(f"## {t['s_conclusions']}"); ln()
    ln(t["con_intro"]); ln()
    ln(f"**{t['con_recommendations']}**"); ln()
    for rec in t["recommendations"]:
        ln(f"- {rec}")
    ln(); ln("---"); ln()
    ln(f"_{t['con_closing']}_"); ln()

    return "\n".join(w)
