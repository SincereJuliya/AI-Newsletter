from collections import defaultdict
import requests
import time
import csv
import os
from datetime import datetime, timedelta
import yake
from tqdm import tqdm
import ollama  # Ollama client
from collections import defaultdict

# ==========================
# Settings
# ==========================
CSV_FILE = "semantic_scholar_results.csv"
DIGEST_FILE = "new_articles_digest.csv"
AI_DIGEST_FILE = "new_articles_digest_ai.csv"

API_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
DELAY = 62  # delay

fields_filter = "Environmental Science,Agricultural,Geography,Geology,Engineering,Physics,Computer Science"

# for queries
RIVERS = ["Po", "Sarca", "Chiese", "Adige", "Noce", "Brenta", "Avisio"]
KEY_TERMS = [
    ["drought", "Italy", "water scarcity"],
    ["aridity", "Italy"],
    ["SPI", "Italy"],          # Standardized Precipitation Index
    ["SPEI", "Italy"],         # Standardized Precipitation Evapotranspiration Index
    ["PDSI", "Italy"],         # Palmer Drought Severity Index
    ["temperature anomaly", "Italy"],
    ["hydrological index", "Italy"],
]

# ==========================
# Load existing CSV (or create)
# ==========================
if os.path.exists(CSV_FILE):
    with open(CSV_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        existing_articles = list(reader)
    print(f"Loaded {len(existing_articles)} existing articles.")
    last_dates = [a.get("publicationDate", "") for a in existing_articles if a.get("publicationDate")]
    last_scraped_date = max(last_dates) if last_dates else (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
else:
    existing_articles = []
    last_scraped_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["title","authors","year","publicationDate","link","abstract","river","keywords","source","scraped_at"])
        writer.writeheader()

print(f"Last publication date in the scraped dataset: {last_scraped_date}")

# ==========================
# Build smart queries
# ==========================
def build_smart_queries():
    queries = []
    for river in RIVERS:
        queries.append({'query': f'{river} River AND drought AND Italy', 'river': river})
        
    for group in KEY_TERMS:
        queries.append({'query': " AND ".join(group), 'river': None})   
        
    seen = set()
    result = []
    for q in queries:
        if q['query'] not in seen:
            seen.add(q['query'])
            result.append(q)
    return result

SMART_QUERIES = build_smart_queries()

# ==========================
# Fetch a batch of papers
# ==========================
def fetch_batch(query, offset=0):
    params = {
        "query": query,
        "fields": "title,authors,year,publicationDate,url,abstract",
        "offset": offset,
        "publicationDateOrYear": f"{last_scraped_date}:",
        "fieldsOfStudy": fields_filter
    }
    r = requests.get(API_URL, params=params)
    if r.status_code == 200:
        return r.json().get("data", [])
    elif r.status_code == 429:
        print("⚠️ 429 Too Many Requests → Waiting...")
        for _ in tqdm(range(DELAY), desc="Waiting for rate limit"):
            time.sleep(1)
        return fetch_batch(query, offset)
    elif r.status_code == 400:
        return []
    else:
        r.raise_for_status()

# ==========================
# Main scraping loop
# ==========================
all_new_articles = []

for q in SMART_QUERIES:
    query = q['query']
    river = q['river']
    print(f"\n🔍 Query: {query}")
    offset = 0

    while True:
        for _ in tqdm(range(DELAY), desc="Waiting before request"):
            time.sleep(1)

        papers = fetch_batch(query, offset)
        if not papers:
            print("No more papers found for this query.")
            break

        new_count = 0
        for paper in papers:
            pub_date = paper.get("publicationDate")
            year = paper.get("year")
            title = (paper.get("title") or "").strip()
            if not title or not year:
                continue
            if any(a["title"] == title for a in existing_articles + all_new_articles):
                continue
            fields = paper.get("fieldsOfStudy")

            authors = ", ".join([a.get("name","") for a in paper.get("authors",[])])
            abstract = (paper.get("abstract") or "").replace("\n"," ").strip()

            entry = {
                "title": title,
                "authors": authors,
                "year": year,
                "publicationDate": pub_date or f"{year}-01-01",
                "link": paper.get("url",""),
                "abstract": abstract,
                "river": river if river else "",
                "keywords": "",
                "source": "Semantic Scholar",
                "scraped_at": datetime.now().isoformat()
            }

            all_new_articles.append(entry)
            new_count += 1
            print(f"✅ {title}")

        if new_count == 0:
            print("No new articles in this batch, moving to next query.")
            break

        offset += len(papers)

print(f"\nTotal new articles collected: {len(all_new_articles)}")

# ==========================
# YAKE setup
# ==========================
yake_kw_extractor = yake.KeywordExtractor(
    lan="en",
    n=3,
    top=7,
    dedupLim=0.9,
    dedupFunc='seqSimilarity',
    windowsSize=2
)
# for keywords
RELEVANT_TERMS = ["drought", "water", "river", "basin", "irrigation", "scarcity", "flow", "hydrology"]

# ==========================
# Generate YAKE keywords
# ==========================
print("\n🔹 Generating keywords with YAKE...")
for article in tqdm(all_new_articles):
    abstract = article.get("abstract","")
    if abstract:
        kws = yake_kw_extractor.extract_keywords(abstract)
        filtered_kws = [kw for kw, score in kws if any(term.lower() in kw.lower() for term in RELEVANT_TERMS)]
        article["keywords"] = ", ".join(filtered_kws)
    else:
        article["keywords"] = ""

# ==========================
# Save new articles digest
# ==========================
if all_new_articles:
    with open(DIGEST_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=all_new_articles[0].keys())
        writer.writeheader()
        writer.writerows(all_new_articles)
    print(f"Saved digest of {len(all_new_articles)} new articles to {DIGEST_FILE}")
else:
    print("No new articles found for digest.")

# ==========================
# Update main CSV
# ==========================
if all_new_articles:
    combined_articles = existing_articles + all_new_articles
    combined_articles = sorted(combined_articles, key=lambda x: x["publicationDate"], reverse=True)
    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=combined_articles[0].keys())
        writer.writeheader()
        writer.writerows(combined_articles)
    print(f"Updated main CSV {CSV_FILE} with {len(all_new_articles)} new articles.")
