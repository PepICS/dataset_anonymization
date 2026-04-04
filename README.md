# 🔐 Datathon Anonymizer

> Eina local i portable per a la preparació de datasets clínics anonimitzats per a datathons sanitaris.

[![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)](https://docker.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

## Què és?

Aplicació web **desplegable en local** amb un sol comandament Docker que permet a qualsevol centre sanitari:

1. Carregar un CSV de dades clíniques en format llarg estàndard
2. Classificar les variables com a quasi-identificadors o no identificatives
3. Definir generalitzacions per a cada quasi-identificador
4. Aplicar **k-anonimitat** amb supressió de registres no conformes
5. Descarregar el dataset anonimitzat i un **informe complet** per al Delegat de Protecció de Dades

Cap dada surt del servidor. Tot s'executa en local, sense cap dependència de serveis externs.

---

## Execució ràpida

```bash
# 1. Clona el repositori
git clone https://github.com/el-teu-usuari/datathon-anonymizer.git
cd datathon-anonymizer

# 2. Arrenca l'aplicació
docker compose up --build -d

# 3. Obre el navegador
# → http://localhost:8000
```

Per aturar:

```bash
docker compose down
```

> **Port personalitzat**: modifica el port esquerre al `docker-compose.yml` (ex: `"8092:8000"`)

---

## Format del CSV d'entrada

El fitxer ha de tenir **exactament 4 columnes** en format llarg:

| Columna | Noms acceptats | Descripció |
|---------|---------------|------------|
| `pacient` | `patient_id`, `pacient_id`, `nhc`, `pid` | Identificador únic del pacient |
| `data` | `date`, `fecha`, `datetime`, `timestamp` | Data de la visita o observació |
| `item` | `variable`, `var`, `field`, `measure` | Nom de la variable clínica |
| `valor` | `value`, `val`, `resultat`, `result` | Valor observat |

L'aplicació detecta automàticament les variantes del nom de columna i les normalitza internament.

### Exemple de fila

```csv
patient_id,data,variable,valor
P0001,2023-02-15,estado_cognitivo,deterioro_leve
P0001,2023-02-15,edad,67
P0001,2023-02-15,fragilidad,fragil
P0001,2023-03-28,estado_cognitivo,deterioro_moderado
```

---

## Flux de l'aplicació

```
┌──────────────┐    ┌─────────────────┐    ┌──────────────────┐    ┌──────────────┐
│  1. Càrrega  │───▶│ 2. Classificació│───▶│ 3. Generalització│───▶│  4. k-anon   │
│  CSV + perfil│    │ QI / no-ID      │    │ bins / categories│    │  + resultats │
└──────────────┘    └─────────────────┘    └──────────────────┘    └──────────────┘
```

### Fase 1 — Càrrega i perfilat

- Accepta codificacions UTF-8, Latin-1, CP1252
- Detecta automàticament el tipus de cada variable (numèrica vs. categòrica)
- Mostra estadístiques, distribució de valors i previsualització

### Fase 2 — Classificació de variables

Per a cada variable, l'usuari indica el rol:

| Rol | Tractament automàtic |
|-----|---------------------|
| 🔑 Identificador directe (`pacient`) | Hash SHA-256 irreversible (prefix `H-`) |
| 📅 Data (`data`) | Delta d'enters: dies des de la primera visita del pacient |
| 🔍 Quasi-identificador | Generalització definida per l'usuari + k-anonimitat |
| ✅ No identificatiu | Sense canvis |

### Fase 3 — Generalitzacions

Per a cada quasi-identificador, l'usuari defineix com agrupar els valors:

- **Variables numèriques** → intervals personalitzats (ex: edat → `0-17`, `18-39`, `40-64`, `65+`)
- **Variables categòriques** → mapeig de valors originals a categories agrupades

Els valors absents (NaN) s'imputen automàticament:
- Categòrics → `Desconocido`
- Numèrics → mediana del conjunt observat

### Fase 4 — K-anonimitat i resultats

- **Simulació prèvia**: mostra l'impacte de k=2, 3, 4, 5 abans d'executar
- **Paràmetre k**: cada combinació de quasi-identificadors ha de tenir ≥ k pacients
- **Supressió**: els pacients en grups massa petits s'eliminen del dataset final
- **Mètriques**: flux de pacients, distribució de classes d'equivalència, grups suprimits

---

## Descàrregues generades

| Fitxer | Format | Per a qui |
|--------|--------|-----------|
| `*_anonymized.csv` | CSV | Participants del datathon |
| `*_report.html` | HTML estilitzat | Delegat de Protecció de Dades (imprimible com a PDF) |
| `*_report.md` | Markdown | Repositori / documentació tècnica |
| `anonymization_report.json` | JSON | Auditoria i traçabilitat |

### Informe per al DPD

L'informe HTML (imprimible com a PDF des del navegador amb Ctrl+P) inclou:

1. Resum executiu amb mètriques clau
2. Descripció del dataset original
3. Marc legal aplicable (RGPD, LOPDGDD, Dictamen 05/2014 del GT Art. 29)
4. Descripció de totes les transformacions aplicades
5. Resultats i distribució de classes d'equivalència
6. Limitacions metodològiques
7. Checklist de verificació per al DPD

---

## Sobre el risc de reidentificació

La protecció real d'aquest procés té **dues capes complementàries**:

**Capa 1 — Incertesa de mostreig** (inherent al context del datathon)

El dataset d'un datathon és una mostra aleatòria d'una població gran. Un atacant que intenti reidentificar una persona concreta no pot saber si aquella persona és al dataset, cosa que per si sola ja és una protecció significativa. Amb 2.000 pacients d'una comunitat de 500.000, la probabilitat que una persona específica sigui a la mostra és inferior al 0,4%.

**Capa 2 — K-anonimitat**

Garanteix que, per a qualsevol perfil definit pels quasi-identificadors, existeixin almenys k-1 individus indistingibles. Amb k=3 i dos quasi-identificadors ben generalitzats (ex: edat en rangs amples + sexe), la protecció és molt robusta en el context d'un datathon.

### Quasi-identificadors recomanats

| Variable | Risc | Recomanació |
|----------|------|-------------|
| `edad` | 🔴 Alt | Sempre QI; generalitzar en rangs de ≥15 anys |
| `sexo_y_o_genero` | 🔴 Alt | Sempre QI |
| `nivel_educativo` | 🟡 Mitjà | QI si el dataset és <500 pacients |
| `situacion_de_convivencia` | 🟡 Mitjà | QI si el dataset és <500 pacients |
| `origen` | 🟡 Mitjà | QI en poblacions locals petites |
| `estado_cognitivo` | 🟢 Baix | Opcional; amb sampling ja és poc probable la reidentificació |
| `fragilidad` | 🟢 Baix | Opcional |
| Reste de variables | 🟢 Molt baix | No identificatives en context de datathon |

---

## Estructura del repositori

```
datathon-anonymizer/
│
├── app/
│   ├── main.py                    # FastAPI: endpoints i gestió de sessions
│   └── modules/
│       ├── anonymizer.py          # Tota la lògica d'anonimització
│       ├── report_md.py           # Generació d'informe Markdown (ca/es/en)
│       └── report_html.py         # Conversió Markdown → HTML estilitzat
│
├── static/
│   ├── index.html                 # Interfície wizard de 4 fases
│   ├── css/styles.css             # Estils (dark mode clínic)
│   └── js/
│       ├── app.js                 # Lògica del frontend (vanilla JS)
│       └── i18n.js                # Traduccions: català, castellà, anglès
│
├── sample_data/
│   ├── dataset_500p.csv           # Dataset sintètic de 500 pacients
│   ├── dataset_2000p.csv          # Dataset sintètic de 2.000 pacients
│   └── Cataluña_Unificado.xlsx    # Excel de variables clíniques de referència
│
├── generate_synthetic.py          # Script per regenerar datasets sintètics
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## Arquitectura tècnica

| Component | Tecnologia |
|-----------|-----------|
| Backend | Python 3.12 + FastAPI |
| Frontend | HTML/CSS/JS pur (sense frameworks) |
| Contenidor | Docker + Docker Compose |
| Dependències Python | pandas, numpy, fastapi, uvicorn, markdown |
| Estat de sessió | En memòria (no persistit) |
| Comunicació | API REST JSON |

L'aplicació no té base de dades, no fa servir cookies de seguiment i no genera cap log persistent amb dades del fitxer carregat.

---

## Multilingüe

La interfície és disponible en **català**, **castellà** i **anglès**. L'idioma es selecciona amb els botons a la barra lateral i afecta tant la interfície com els informes generats.

---

## Generació de datasets sintètics

El script `generate_synthetic.py` genera datasets de prova llegint les variables directament de l'Excel de referència:

```bash
# Des de dins del contenidor Docker:
docker exec datathon-anonymizer python3 generate_synthetic.py

# O localment amb Python:
python3 generate_synthetic.py
```

Per canviar el nombre de pacients, edita les variables `n_patients` i `visits_per_patient` al final del script.

---

## Requisits

- [Docker](https://docs.docker.com/get-docker/) ≥ 24.0
- [Docker Compose](https://docs.docker.com/compose/) ≥ 2.0
- Cap altra dependència al host

---

## Limitacions conegudes

- **Sessió en memòria**: si el servidor es reinicia, les sessions actives es perden. Per a ús en datathon (sessió curta), això no és un problema.
- **Un usuari a la vegada**: no hi ha autenticació ni aïllament de sessions entre usuaris simultanis. Pensat per a ús individual o en xarxa local controlada.
- **K-anonimitat per supressió**: no implementa generalització addicional automàtica. Si la pèrdua de pacients és massa gran, cal revisar les generalitzacions.
- **L-diversitat no implementada**: la k-anonimitat no protegeix contra atacs d'homogeneïtat. Amb el context de datathon i la incertesa de mostreig, aquest risc és molt baix a la pràctica.

---

## Marc legal

Aquest projecte ajuda a complir amb:

- **RGPD (Reglament UE 2016/679)** — Art. 89 i Recital 26 sobre tractament per a recerca
- **LOPDGDD (LO 3/2018)** — Transposició espanyola del RGPD
- **Dictamen 05/2014 del Grup de Treball de l'Art. 29** — K-anonimitat com a tècnica reconeguda
- **Guies ENISA** sobre anonimització de dades sanitàries

> ⚠️ Aquesta eina facilita el procés tècnic, però la responsabilitat de la classificació de les variables i la validació de l'informe recau en el Delegat de Protecció de Dades del centre.

---

## Llicència

MIT — Lliure per a ús, modificació i distribució. Atribució apreciada.

---

## Contribucions

Pull requests benvinguts. Per a canvis majors, obriu primer una *issue*.

Idees per a futures versions:
- [ ] Autenticació bàsica per a entorns multi-usuari
- [ ] Persistència de sessions (base de dades lleugera)
- [ ] Suport per a Excel (.xlsx) com a format d'entrada
- [ ] Advertiment d'homogeneïtat per a variables sensibles
- [ ] Soroll diferencial com a alternativa a la supressió

---

*Construït per a centres sanitaris que volen participar en datathons preservant la privacitat dels seus pacients.*
