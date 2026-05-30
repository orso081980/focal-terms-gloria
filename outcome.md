# Outcome — Focal Terms Pipeline

## In plain words

This project answers a simple question:
**"When a patent cites a scientific paper, do they share the same vocabulary — and is that vocabulary used the same way?"**

The pipeline works in three steps:

1. **Find the shared terms.** We look at the words (terms) used in each patent, find which scientific papers that patent cites, and check which terms appear in *both* the patent and at least one of those papers. We call these *focal terms*.

2. **Measure the overlap.** How many focal terms does each patent share with its cited papers? Some patents share many (up to 158); most share a handful. This step measures the distribution and identifies the patents and terms with the highest overlap.

3. **Check if the meaning is the same.** A term like *"cell"* could mean very different things in a patent vs. a biology paper. For a sample of 20,000 patent-term pairs, we convert the surrounding context into a sentence embedding and compare how similar the usage is (cosine similarity). A score near 1 means the term is used in the same way; near 0 or negative means the contexts are very different.

All computation runs exclusively on **GitHub Actions**. Input data is downloaded from **Cloudflare R2**, and all output files (Parquet + JSON) are uploaded back to R2 under the `outcomes/` folder. Nothing is committed to the repository.

---

## Results at a glance

| Metric | Value |
|---|---|
| Total focal-term pairs | 11,967,149 |
| Patents covered | 474,011 |
| PubMed papers linked | 795,519 |
| Unique focal terms | 34,536 |
| Mean focal terms per patent | 8.85 |
| Median focal terms per patent | 6 |
| Most common focal term | "cell" (500 k occurrences) |
| Mean semantic similarity | 0.469 |

---

## Interactive viewer

A Vue 3 app (in `focal-terms-app/`) visualises all pipeline outputs. It is automatically deployed to GitHub Pages by workflow `04_deploy_app.yml` whenever `focal-terms-app/` changes.

**Live app:** `https://orso081980.github.io/focal-terms-gloria/`

> **One-time setup required:** In GitHub repo settings → Pages → set Source to **GitHub Actions**.

---

---

## Architecture

```
GitHub Actions
    │
    ├─ Workflow 01 ── downloads raw parquets from R2 ──► runs 01_focal_terms.py
    │                  uploads to R2: outcomes/01_focal_terms_full.{parquet,json}
    │
    ├─ Workflow 02 ── downloads outcomes/01_focal_terms_full.parquet from R2
    │                  runs 02_analysis.py
    │                  uploads to R2: outcomes/02_*.{parquet,json}
    │
    ├─ Workflow 03 ── downloads outcomes/01_focal_terms_full.parquet + raw files
    │                  runs 03_semantic.py
    │                  uploads to R2: outcomes/03_*.{parquet,json}, viewer_data_full.json
    │
    └─ Workflow 04 ── builds focal-terms-app/ Vue app ──► deploys to GitHub Pages
```

---

## Scripts

### `full-notebook/01_focal_terms.py` — Task 1: Identify Focal Terms

**Input:** Three raw Parquet files from R2 (`parquetunistuttgart` bucket):

- `FullSampleGloria_Pat_GlinerLabels.parquet` — patent terms
- `FullSampleGloria_Link_PmidOa.parquet` — patent ↔ PMID links
- `FullSampleGloria_Pmed_GlinerLabels_16042026.parquet` — PubMed paper terms

**What it does:**

1. Loads all unique patent IDs
2. Processes patents in batches of 5,000 to stay within memory limits
3. For each batch: loads patent terms → links → PubMed terms → inner-joins to find terms present in both
4. Combines all batch outputs, removes duplicates
5. Exports summary statistics

**Output to R2 (`outcomes/`):**

- `01_focal_terms_full.parquet` — all `(patent_id, pmid, focal_term, freq_in_patent, freq_in_paper)` rows
- `01_focal_terms_full.json` — summary stats (row count, unique patents, PMIDs, terms)

---

### `full-notebook/02_analysis.py` — Task 2: Overlap Intensity

**Input:** `outcomes/01_focal_terms_full.parquet` (downloaded from R2)

**What it does:**

1. Counts unique focal terms per patent
2. Computes summary statistics (mean, median, std, min, max)
3. Identifies top-10 patents by focal-term overlap
4. Ranks focal terms by frequency across patents
5. Exports a histogram visualisation

**Output to R2 (`outcomes/`):**

- `02_focal_term_counts_full.parquet` — per-patent focal-term counts
- `02_term_frequency_full.parquet` — per-term frequency across patents
- `02_analysis_full.json` — full summary including top patents and top/bottom terms

---

### `full-notebook/03_semantic.py` — Task 3: Semantic Context Comparison

**Input:** `outcomes/01_focal_terms_full.parquet` + raw Parquet files (both from R2)

**What it does:**

1. Samples up to 20,000 `(patent_id, focal_term)` pairs
2. Builds a _patent context_ (all other terms in the patent) and a _paper context_ (all other terms in cited papers that contain the focal term)
3. Serialises each context to a sentence: `"<focal_term> <term_1> <term_2> ..."`
4. Encodes all sentences using `sentence-transformers/all-MiniLM-L6-v2`
5. Computes cosine similarity row-wise (patent vs. paper context)
6. Exports high/low similarity examples and distribution plot
7. Generates `viewer_data.json` (aggregated dashboard payload)

**Output to R2 (`outcomes/`):**

- `03_contexts_full.parquet` — serialised context pairs
- `03_similarity_full.parquet` — per-pair cosine similarity scores
- `03_semantic_summary_full.json` — stats + high/low examples
- `viewer_data_full.json` — aggregated payload for downstream use

---

## GitHub Actions Workflows

All three workflows are triggered manually via `workflow_dispatch` (no parameters — always runs in full mode).

| Workflow             | Timeout | Key dependencies                                  |
| -------------------- | ------- | ------------------------------------------------- |
| `01_focal_terms.yml` | 6 h     | `polars`, `pyarrow`, `boto3`                      |
| `02_analysis.yml`    | 1 h     | `polars`, `numpy`, `matplotlib`                   |
| `03_semantic.yml`    | 6 h     | `polars`, `sentence-transformers`, `scikit-learn` |

### Required GitHub Secrets

Set these in **Settings → Secrets → Actions** on the repository:

| Secret name        | Description                     |
| ------------------ | ------------------------------- |
| `R2_ACCESS_KEY`    | Cloudflare R2 Access Key ID     |
| `R2_ACCESS_SECRET` | Cloudflare R2 Secret Access Key |

### Execution Order

Run the workflows in sequence:

1. **Workflow 01** — produces the focal terms file
2. **Workflow 02** — consumes it for analysis
3. **Workflow 03** — consumes it for semantic similarity

---

## Performance Notes

- Script 01 uses Polars' **streaming engine** (`sink_parquet`) to process the 3-way join (PAT=700 MB, LINK=554 MB, PMED=198 MB) without loading everything into RAM. No `.collect()` is called — data flows through in chunks.
- Script 03 caps per-PMID term lists at 300 entries before the join to prevent OOM; this is lossless since the embedding model (`all-MiniLM-L6-v2`) truncates at 256 tokens anyway. A sample of 20,000 pairs is used to keep CPU inference time tractable.

---

## R2 Bucket Layout

```
parquetunistuttgart/
├── FullSampleGloria_Pat_GlinerLabels.parquet        ← input (patent terms)
├── FullSampleGloria_Link_PmidOa.parquet             ← input (patent-PMID links)
├── FullSampleGloria_Pmed_GlinerLabels_16042026.parquet  ← input (paper terms)
└── outcomes/
    ├── 01_focal_terms_full.parquet
    ├── 01_focal_terms_full.json
    ├── 02_focal_term_counts_full.parquet
    ├── 02_term_frequency_full.parquet
    ├── 02_analysis_full.json
    ├── 03_contexts_full.parquet
    ├── 03_similarity_full.parquet
    ├── 03_semantic_summary_full.json
    └── viewer_data_full.json
```
