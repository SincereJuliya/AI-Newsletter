import pandas as pd
from datetime import datetime
import time
import re
import ollama  # Ollama client

# ==========================
# SETTINGS
# ==========================
CSV_FILE_RAW = "semantic_scholar_results.csv"           # input CSV
CSV_FILE_CLEAN = "cleaned_with_summary_llama.csv"      # output CSV for clean articles
CSV_FILE_BROKEN = "broken_articles.csv"               # output CSV for broken/missing abstracts
YEARS_BACK = 3
ITALY_KEYWORDS = [
    "italy", "italia",
    "po basin", "po river", "padana",
    "calabria", "sicily", "sicilia",
    "alps", "apennines",
    "po", "sarca", "chiese", "adige", "noce", "brenta", "avisio",
    "lombardy", "veneto", "trentino", "piemonte", "tuscany", "emilia-romagna", "friuli",
    "river", "basin", "water resources", "drought"
]
LLAMA_MODEL_NAME = "llama3"
DELAY_BETWEEN_REQUESTS = 0.5

# ==========================
# CONNECT TO OLLAMA
# ==========================
try:
    client = ollama.Client()
    client.list()
    print(f"✅ Ollama client connected. Using model: {LLAMA_MODEL_NAME}")
except Exception as e:
    print(f"❌ Could not connect to Ollama. Make sure it's running. Error: {e}")
    exit()

# ==========================
# STEP 1: LOAD CSV
# ==========================
print(f"📄 Loading data from {CSV_FILE_RAW}...")
try:
    df = pd.read_csv(CSV_FILE_RAW)
except FileNotFoundError:
    print(f"❌ Error: {CSV_FILE_RAW} not found.")
    exit()

# ==========================
# STEP 2: CLEAN DATA
# ==========================
print("🧹 Cleaning data...")
df = df[df["title"].notnull() & (df["title"].str.strip() != "")]
df = df.drop_duplicates(subset=["title"])

current_year = datetime.now().year
min_year = current_year - YEARS_BACK + 1
df = df[df["year"].notnull() & (df["year"] >= min_year)]
print(f"   Articles left after cleaning and year filter ({min_year}-{current_year}): {len(df)}")

# ==========================
# STEP 3: FILTER BY ITALY
# ==========================
def is_about_italy(text):
    if pd.isnull(text):
        return False
    t = text.lower()
    for kw in ITALY_KEYWORDS:
        if re.search(r'\b' + re.escape(kw) + r'\b', t):
            return True
    return False

df = df[df["title"].apply(is_about_italy) | df["abstract"].apply(is_about_italy)]
print(f"🇮🇹 Articles left after Italy keyword filter: {len(df)}")

# ==========================
# STEP 4: SPLIT BROKEN ARTICLES
# ==========================
broken_mask = df["abstract"].isnull() | (df["abstract"].str.strip().str.len() < 30)
df_broken = df[broken_mask].copy()
df = df[~broken_mask].copy()
print(f"⚠️ Broken/empty abstracts moved to {CSV_FILE_BROKEN}: {len(df_broken)} articles")
df_broken.to_csv(CSV_FILE_BROKEN, index=False, encoding="utf-8")

# ==========================
# STEP 5: GENERATE SHORT SUMMARY
# ==========================
def summarize_short(text):
    prompt = f"""
Summarize the abstract in 2-3 sentences. Output ONLY the summary, no leading phrases.
Focus on the main objective, key methods, results, and conclusions.
Abstract:
{text}
"""
    try:
        response = client.generate(
            model=LLAMA_MODEL_NAME,
            prompt=prompt,
            options={
                "temperature": 0.2,
                "num_ctx": 4096,
                "num_predict": 250
            }
        )
        return response['response'].strip()
    except Exception as e:
        print(f"⚠️ Error summarizing via Ollama: {e}")
        return ""

print(f"🤖 Generating concise summaries using {LLAMA_MODEL_NAME}...")
summaries = []
for idx, abstract in enumerate(df["abstract"]):
    print(f"Summarizing article {idx+1}/{len(df)}...")
    summaries.append(summarize_short(abstract))
    time.sleep(DELAY_BETWEEN_REQUESTS)

df["summary"] = summaries

# ==========================
# STEP 6: DROP FULL ABSTRACT
# ==========================
df_clean = df.drop(columns=["abstract"])

# ==========================
# STEP 7: SAVE TO CSV
# ==========================
print(f"💾 Saving cleaned data to {CSV_FILE_CLEAN}...")
df_clean.to_csv(CSV_FILE_CLEAN, index=False, encoding="utf-8")
print(f"✅ Done! Saved {len(df_clean)} clean articles to {CSV_FILE_CLEAN}")