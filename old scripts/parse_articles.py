import requests
import time
import csv
from datetime import datetime
import yake
from tqdm import tqdm

# ==========================
# Settings
# ==========================
CSV_FILE = "semantic_scholar_results.csv"
YEARS_BACK = 5
MAX_ARTICLES = 60
MIN_ARTICLES_PER_RIVER = 10

DELAY = 65  # safe for free-tier
BATCH_SIZE = 25
url = "https://api.semanticscholar.org/graph/v1/paper/search"

RIVERS = ["Po", "Sarca", "Chiese", "Adige", "Noce", "Brenta", "Avisio"]
REGION = "Italy"

KEY_TERMS = [
    ["drought", "Italy", "water scarcity"],
    ["drought", "Italy"],
    ["aridity", "Italy"],
    ["water scarcity", "Italy"],
    ["hydrology", "Italy"],
]

BASE_KEYWORDS = [
    "drought",
    "water resources",
    "water scarcity",
    "aridity",
    "hydrology",
    "Italy",
]

RELEVANT_TERMS = ["drought", "water", "river", "basin", "irrigation", "scarcity", "flow", "hydrology"]

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

# ==========================
# Build smart queries
# ==========================
def build_smart_queries():
    queries = []
    for river in RIVERS:
        queries.append({'query': f'"{river}" AND drought AND Italy', 'river': river})
    for group in KEY_TERMS:
        queries.append({'query': " AND ".join(group), 'river': None})
    for kw in BASE_KEYWORDS:
        queries.append({'query': f"{kw} AND drought AND", 'river': None})
    for q in ["drought Italy", "drought", "water resources", "Italy water", "water"]:
        queries.append({'query': q, 'river': None})
    # remove duplicates
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
def fetch_batch(query, offset=0, limit=BATCH_SIZE):
    params = {
        "query": query,
        "fields": "title,authors,year,url,abstract,fieldsOfStudy",
        "offset": offset,
        "limit": limit
    }
    r = requests.get(url, params=params)
    if r.status_code == 200:
        return r.json().get("data", [])
    elif r.status_code == 429:
        print("⚠️ 429 Too Many Requests → Waiting...")
        for _ in tqdm(range(DELAY), desc="Waiting for rate limit"):
            time.sleep(1)
        return fetch_batch(query, offset, limit)
    elif r.status_code == 400:
        # offset too large → stop
        return []
    else:
        r.raise_for_status()

# ==========================
# Main scraping loop
# ==========================
all_articles = []
current_year = datetime.now().year
min_year = current_year - YEARS_BACK + 1
river_counts = {r: 0 for r in RIVERS}

print("🔹 Starting Semantic Scholar scraping...\n")

for q in SMART_QUERIES:
    query = q['query']
    river = q['river']
    print(f"\n🔍 Sending query: {query}")
    offset = 0
    total_found_for_query = 0

    while True:
        if len(all_articles) >= MAX_ARTICLES:
            print("Reached maximum articles limit.")
            break
        else: print(f"  → Total articles collected so far: {len(all_articles)}")
        
        for _ in tqdm(range(DELAY), desc="Before let's wait for rate limit!"):
            time.sleep(1)

        papers = fetch_batch(query, offset=offset)
        if not papers:
            break

        new_count_in_batch = 0

        for paper in papers:
            year = paper.get("year")
            if not year or year < min_year:
                continue

            title = (paper.get("title") or "").strip()
            if not title:
                continue

            # filter out medical/health papers
            fields = paper.get("fieldsOfStudy")
            if fields and any(f.lower() in ['medicine', 'health', 'clinical'] for f in fields):
                continue

            # filter duplicates
            if any(a["title"] == title for a in all_articles):
                continue

            authors = ", ".join([a.get("name", "") for a in paper.get("authors", [])])
            abstract = (paper.get("abstract") or "").replace("\n", " ").strip()

            entry = {
                "title": title,
                "authors": authors,
                "year": year,
                "link": paper.get("url", ""),
                "abstract": abstract,
                "river": river if river else "",
                "region": REGION,
                "keywords": "",  # will be filled by YAKE later
                "source": "Semantic Scholar",
                "scraped_at": datetime.now().isoformat()
            }

            # enforce minimum articles per river
            if river:
                if river_counts[river] >= MIN_ARTICLES_PER_RIVER:
                    continue
                river_counts[river] += 1

            all_articles.append(entry)
            total_found_for_query += 1
            new_count_in_batch += 1
            print(f"✅ {title}")

        # stop loop if no new articles or batch smaller than BATCH_SIZE
        if new_count_in_batch == 0 or len(papers) < BATCH_SIZE:
            break

        offset += len(papers)

    print(f"  → Total found from this query: {total_found_for_query}")


# ==========================
# Generate YAKE keywords
# ==========================
print("\n🔹 Generating keywords with YAKE for all articles...")
for article in tqdm(all_articles):
    abstract = article.get("abstract", "")
    river = article.get("river")  # kept for reference, not used in keywords
    if abstract:
        kws = yake_kw_extractor.extract_keywords(abstract)
        filtered_kws = []
        for kw, score in kws:
            # filter only by RELEVANT_TERMS, river not included
            if any(term.lower() in kw.lower() for term in RELEVANT_TERMS):
                filtered_kws.append(kw)
        article["keywords"] = ", ".join(filtered_kws)
    else:
        article["keywords"] = ""

# ==========================
# Sort and limit articles
# ==========================
all_articles = sorted(all_articles, key=lambda x: x["year"], reverse=True)[:MAX_ARTICLES]

# ==========================
# Save CSV
# ==========================
fieldnames = ["title","authors","year","link","abstract","river","region","keywords","source","scraped_at"]
with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(all_articles)

print(f"\n✅ Saved {len(all_articles)} articles to {CSV_FILE}")