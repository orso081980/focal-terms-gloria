import os
os.environ.setdefault("POLARS_MAX_THREADS", "4")

import gc
import json
import time
from pathlib import Path
import polars as pl

# =========================
# CONFIGURATION
# =========================
BASE     = Path(__file__).parent
DATA_DIR = BASE.parent / "data"

PAT_PATH  = DATA_DIR / "FullSampleGloria_Pat_GlinerLabels_16042026.parquet"
LINK_PATH = DATA_DIR / "FullSampleGloria_Link_PmidOa_16042026.parquet"
PMED_PATH = DATA_DIR / "FullSampleGloria_Pmed_GlinerLabels_16042026.parquet"

OUT_DIR    = BASE.parent / "output"
OUT_DIR.mkdir(exist_ok=True)
FINAL_PATH = OUT_DIR / "focal_terms_full.parquet"

def elapsed(t0):
    """Format elapsed time as 'Xm' or 'Xs' for readability."""
    s = time.time() - t0
    return f"{s/60:.1f}m" if s >= 60 else f"{s:.1f}s"

print("=== TASK 1: Focal Terms (single-pass join) ===")
print(f"Polars version: {pl.__version__}")

if FINAL_PATH.exists():
    FINAL_PATH.unlink()

t0_all = time.time()

# =========================
# STEP 1: Load and clean link table (scanned once)
# =========================
# Extract all unique (patent_id, pmid) pairs.
# PMID values may be stored as URLs — extract just the trailing numeric part.
print("\nStep 1: Loading link table...")
t0 = time.time()

link_clean = (
    pl.scan_parquet(LINK_PATH)
    .filter(pl.col("pmid").is_not_null())
    .with_columns(
        pl.col("pmid")
        .cast(pl.String)
        .str.extract(r"(\d+)$", 1)  # Extract trailing digits from URL or plain ID
        .cast(pl.Int64)
        .alias("pmid")
    )
    .filter(pl.col("pmid").is_not_null())
    .select("patent_id", "pmid")
    .unique()
    .collect()
)

print(f"  {len(link_clean):,} unique (patent, pmid) pairs | {elapsed(t0)}")

# =========================
# STEP 2: Load patent terms (scanned once)
# =========================
# Count how many times each term appears in each patent.
print("\nStep 2: Computing patent term frequencies...")
t0 = time.time()

pat_terms = (
    pl.scan_parquet(PAT_PATH)
    .select("patent_id", "term")
    .filter(pl.col("term").is_not_null())
    .group_by("patent_id", "term")
    .agg(pl.len().alias("freq_in_patent"))
    .collect()
)

print(f"  {len(pat_terms):,} (patent, term) rows | {elapsed(t0)}")

# =========================
# STEP 3: Load PubMed terms — filtered to linked PMIDs only (scanned once)
# =========================
# Filtering to only PMIDs that appear in the link table avoids loading the
# full 207M-row PubMed file into memory — only relevant papers are kept.
print("\nStep 3: Computing PubMed term frequencies (linked PMIDs only)...")
t0 = time.time()

linked_pmids = link_clean.select("pmid").unique()

pmed_terms = (
    pl.scan_parquet(PMED_PATH)
    .select(pl.col("pmid").cast(pl.Int64), "term")
    .filter(pl.col("term").is_not_null())
    .filter(pl.col("pmid").is_not_null())
    .join(linked_pmids.lazy(), on="pmid", how="inner")  # Keep only cited papers
    .group_by("pmid", "term")
    .agg(pl.len().alias("freq_in_paper"))
    .collect()
)

print(f"  {len(pmed_terms):,} (pmid, term) rows | {elapsed(t0)}")

del linked_pmids
gc.collect()

# =========================
# STEP 4: Join to identify focal terms
# =========================
# Focal term = a term that appears in both:
#   - the patent  (freq_in_patent > 0)
#   - a cited paper (freq_in_paper > 0)
# The join chain: link_clean × pmed_terms (on pmid) × pat_terms (on patent_id + term)
# Only terms present in BOTH sources survive the two inner joins.
print("\nStep 4: Joining to identify focal terms...")
t0 = time.time()

(
    link_clean.lazy()
    .join(pmed_terms.lazy(), on="pmid", how="inner")
    .join(pat_terms.lazy(), on=["patent_id", "term"], how="inner")
    .rename({"term": "focal_term"})
    .select("patent_id", "pmid", "focal_term", "freq_in_patent", "freq_in_paper")
    .sink_parquet(FINAL_PATH)
)

print(f"  Saved to: {FINAL_PATH} | {elapsed(t0)}")

del link_clean, pat_terms, pmed_terms
gc.collect()

# =========================
# STEP 5: Print summary statistics
# =========================
print("\nStep 5: Computing summary statistics...")
t0 = time.time()

stats = (
    pl.scan_parquet(FINAL_PATH)
    .select([
        pl.len().alias("n_rows"),
        pl.col("patent_id").n_unique().alias("n_patents"),
        pl.col("pmid").n_unique().alias("n_pmids"),
        pl.col("focal_term").n_unique().alias("n_focal_terms"),
    ])
    .collect()
)

print(stats)
print(f"  Done in {elapsed(t0)}")

# =========================
# STEP 6: Export JSON summary
# =========================
print("\nStep 6: Exporting JSON summary...")
t0 = time.time()

stats_row = stats.to_dicts()[0]
json_path = OUT_DIR / "focal_terms_full.json"
json_path.write_text(json.dumps({
    "n_rows":        int(stats_row["n_rows"]),
    "n_patents":     int(stats_row["n_patents"]),
    "n_pmids":       int(stats_row["n_pmids"]),
    "n_focal_terms": int(stats_row["n_focal_terms"]),
}, indent=2))
print(f"  Saved to: {json_path} | {elapsed(t0)}")

print(f"\n{'='*60}")
print(f"TASK 1 COMPLETE | Total time: {elapsed(t0_all)}")
print(f"{'='*60}")
