# Italy Rivers Scientific Digest

This project collects, analyzes, and visualizes scientific articles about Italian rivers, focusing on drought, water scarcity, and hydrological indices. It automatically fetches new articles from **Semantic Scholar**, generates concise AI summaries using **LLaMA**, and provides an interactive dashboard with maps and filtered article views.

---
## Features

- **Automated Weekly Updates**: Fetches new articles and generates digests.  
- **AI Summarization**: Uses LLaMA via `ollama` to produce concise 2-3 sentence summaries per river.  
- **Interactive Dashboard**: Streamlit + Folium map with river-specific summaries and article lists.  
- **Archiving**: Automatically archives previous CSVs for reference.  

---
## Technologies & Tools

**Programming & Scripting**  
- Python 3.11+  
- GitHub Actions workflows  

**Libraries & Packages**  
- `requests`, `yake`, `csv`, `pandas`, `numpy`, `tqdm` — data fetching, processing, keyword extraction  
- `ollama` — AI summarization (LLaMA model)  
- `streamlit`, `folium`, `streamlit-folium` — interactive dashboard and maps  
- `json`, `os`, `shutil`, `datetime` — file handling and archiving  

**External Services / APIs**  
- [Semantic Scholar API](https://www.semanticscholar.org/product/api) — scientific article retrieval  

**Data & Visualization**  
- CSV files for raw articles and digests:  
  - `semantic_scholar_results.csv`  
  - `new_articles_digest.csv`  
  - `new_articles_digest_ai.csv`  
- GeoJSON files for Italian rivers: `geo/*.geojson`  

**Automation / Deployment**  
- GitHub Actions — scheduled weekly runs of `run_all.py`  
- GitHub-hosted Linux runners (free for public repos)  

---
## File Structure
```bash
/repo-root
├─ run_all.py # Main script: archives CSVs, scrapes articles, generates AI digest
├─ semantic_scraper.py # Fetches articles from Semantic Scholar
├─ llama_digest.py # Generates AI summaries using LLaMA
├─ digest.py # Streamlit dashboard visualization
├─ archive/ # Archived CSVs
├─ geo/ # GeoJSON files for rivers
├─ .github/workflows/ # GitHub Actions workflow (weekly)
└─ requirements.txt # Python dependencies
```

---
## Setup & Usage

### 1. Install Dependencies
```bash
python -m venv venv
source venv/bin/activate        # Linux/macOS
venv\Scripts\activate           # Windows
pip install -r requirements.txt
```
### 2. Run Scripts Locally
```bash
# Full weekly update
python run_all.py
```
### 3. Start Dashboard
```bash
# To run locally
streamlit run digest.py
```

---
## Automation with GitHub Actions

The workflow is configured to run run_all.py weekly.

Public repos use free GitHub-hosted runners.

Logs, artifacts, and errors are available via the Actions tab.

---
## Sources & References

(Semantic Scholar API)[https://www.semanticscholar.org/product/api] — Article data

LLaMA Models via Ollama — AI summarization

River GeoJSON boundaries — Project local geo/ folder

---
## Notes

> Keywords are extracted using YAKE and included in the digest.

> Dashboard - [https://ai-newsletter-demo.streamlit.app/]




