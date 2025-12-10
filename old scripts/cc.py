from collections import defaultdict
import time
import ollama
import csv

INPUT_FILE = "new_articles_digest.csv"
OUTPUT_FILE = "new_articles_digest_ai.csv"

LLAMA_MODEL = "llama3"

def load_articles():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)

def ask_llama(prompt):
    try:
        response = ollama.generate(
            model=LLAMA_MODEL,
            prompt=prompt,
            options={
                "temperature": 0.2,
                "num_ctx": 5000,
                "num_predict": 350
            }
        )
        return response["response"].strip()
    except Exception as e:
        print(f"⚠️ LLaMA error: {e}")
        return ""

# ========================
# Для обычных рек (абстракт, Markdown ссылки)
# ========================
def process_river_articles(river, articles):
    parts = []
    for a in articles:
        title = a.get("title", "")
        abstract = a.get("abstract", "")
        link = a.get("link", "")
        # Markdown для ссылок
        parts.append(f"[{title}]({link})\n\n{abstract}")

    joined = "\n\n".join(parts)
    prompt = f"""
You are analyzing NEW scientific articles about {river} River.

Write a very concise digest (2-3 sentences) in Markdown format:
- new data, indices, models, or results
- relevance for hydrology, drought, climate, or monitoring
- keep article titles as Markdown links [Title](URL)

Start immediately with the digest. Do NOT add introductory phrases. Do NOT output bullet points.

Articles to summarize:
{joined}
"""
    return ask_llama(prompt)

# ========================
# Для Others (только ключевые слова)
# ========================
def process_others_articles(articles):
    keywords_list = []
    for a in articles:
        kws = a.get("keywords", "")
        if kws:
            keywords_list.extend([kw.strip() for kw in kws.split(";")])
    
    keywords_list = sorted(set(keywords_list))
    keywords_str = ", ".join(keywords_list)

    print(f"   --- Others: {len(articles)} articles, keywords collected: {keywords_str[:100]}...")

    prompt = f"""
You are analyzing NEW scientific articles in the 'Others' category.

Using only the provided keywords, write a single, beautiful, concise digest (2-3 sentences) suitable for website display.
- Mention the main topics discovered (from keywords)
- Start immediately with the digest
- Do NOT include links or bullet points

Keywords:
{keywords_str}
"""
    return ask_llama(prompt)

# ========================
# Main
# ========================
def main():
    print(f"Loading articles from {INPUT_FILE}...")
    articles = load_articles()
    if not articles:
        print("No articles found.")
        return

    by_river = defaultdict(list)
    for a in articles:
        river = a.get("river")
        if not river or river.strip() == "":
            river = "Others"
        by_river[river].append(a)

    print("Generating AI digest per river...\n")
    river_summaries = []

    for river, arts in by_river.items():
        print(f"🌊 {river}: {len(arts)} articles")
        if river == "Others":
            summary = process_others_articles(arts)
        else:
            summary = process_river_articles(river, arts)

        # Собираем keywords для дебага
        kws = set()
        for a in arts:
            k = a.get("keywords", "")
            if k:
                kws.update([kw.strip() for kw in k.split(";")])
        kws_str = ";".join(sorted(kws)) if kws else ""

        river_summaries.append({
            "river": river,
            "summary": summary,
            "keywords": kws_str
        })

    # Сохраняем CSV
    with open(OUTPUT_FILE, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["river", "summary", "keywords"])
        writer.writeheader()
        for row in river_summaries:
            writer.writerow(row)

    print(f"\n✅ Saved AI digest to {OUTPUT_FILE} in CSV format")

if __name__ == "__main__":
    main()
