import subprocess
import sys
import os
import shutil
from datetime import datetime

# ==========================
# Archive old CSVs
# ==========================
ARCHIVE_DIR = "archive"
os.makedirs(ARCHIVE_DIR, exist_ok=True)

FILES_TO_ARCHIVE = [
    "semantic_scholar_results.csv",
    "new_articles_digest.csv",
    "new_articles_digest_ai.csv"
]

def archive_file(file_path):
    if os.path.exists(file_path):
        date_str = datetime.now().strftime("%Y-%m-%d")
        base_name = os.path.basename(file_path)
        new_name = f"{ARCHIVE_DIR}/{date_str}_{base_name}"
        shutil.copy(file_path, new_name)
        print(f"Archived {file_path} → {new_name}")

# ==========================
# Run a Python script
# ==========================
def run_script(script_name):
    if os.path.exists(script_name):
        print(f"\n➡️ Running {script_name} ...")
        result = subprocess.run([sys.executable, script_name])
        if result.returncode != 0:
            print(f"⚠️ Error while running {script_name}")
            sys.exit(1)
    else:
        print(f"⚠️ {script_name} not found, skipping.")

# ==========================
# Main function
# ==========================
def main():
    # 1. Archive old CSV files
    for f in FILES_TO_ARCHIVE:
        archive_file(f)

    # 2. Scraping new articles
    run_script("semantic_scraper.py")

    # 3. AI digest generation
    run_script("llama_digest.py")

    print("\n🎉 Weekly update completed successfully!")

if __name__ == "__main__":
    main()
