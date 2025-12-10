import streamlit as st
import pandas as pd

CSV_FILE = "cleaned_with_summary_llama.csv"
st.set_page_config(page_title="Academic Papers Dashboard", layout="wide")

# ==========================
# Load data
# ==========================
try:
    df = pd.read_csv(CSV_FILE)
except FileNotFoundError:
    st.error(f"File {CSV_FILE} not found.")
    st.stop()

st.title("📚 Academic Papers Dashboard")

# ==========================
# Sidebar Filters
# ==========================
st.sidebar.header("Filters")

# Year filter
min_year = int(df['year'].min())
max_year = int(df['year'].max())
years_selected = st.sidebar.slider("Select year range", min_year, max_year, (min_year, max_year))
df_filtered = df[(df['year'] >= years_selected[0]) & (df['year'] <= years_selected[1])]

# River filter
all_rivers = df_filtered['river'].dropna().unique()
rivers_selected = st.sidebar.multiselect("Select rivers", all_rivers)
if rivers_selected:
    df_filtered = df_filtered[df_filtered['river'].isin(rivers_selected)]

# Keywords filter
all_keywords = (
    df_filtered['keywords']
    .dropna()
    .astype(str)
    .str.split(',')
    .explode()
    .str.strip()
    .unique()
)
keywords_selected = st.sidebar.multiselect("Select keywords", all_keywords)
if keywords_selected:
    def contains_keyword(val):
        if not isinstance(val, str):
            return False
        val_lower = val.lower()
        return any(k.lower() in val_lower for k in keywords_selected)
    df_filtered = df_filtered[df_filtered['keywords'].apply(contains_keyword)]

st.sidebar.markdown(f"**Total papers:** {len(df_filtered)}")

# ==========================
# Display cards
# ==========================
cards_per_row = 3
card_height = "360px"
rows = [df_filtered.iloc[i:i+cards_per_row] for i in range(0, len(df_filtered), cards_per_row)]

for row_df in rows:
    cols = st.columns(cards_per_row, gap="large")
    for col, (_, paper) in zip(cols, row_df.iterrows()):
        title = paper["title"]
        keywords = str(paper.get('keywords', ''))
        river = str(paper.get('river', 'N/A'))
        year = str(paper.get('year', 'N/A'))
        summary = str(paper.get('summary', 'No summary'))
        link = str(paper.get('link', '#'))

        col.markdown(f"""
            <div style="
                position: relative;
                border-radius:12px;
                background: rgba(255, 255, 255, 0.35);
                backdrop-filter: blur(10px);
                box-shadow: 0 4px 12px rgba(0,0,0,0.08);
                padding:15px;
                display:flex;
                flex-direction:column;
                height:{card_height};
                transition: transform 0.2s, box-shadow 0.2s;
            " onmouseover="this.style.transform='scale(1.03)'; this.style.boxShadow='0 8px 20px rgba(0,0,0,0.12)';" 
              onmouseout="this.style.transform='scale(1)'; this.style.boxShadow='0 4px 12px rgba(0,0,0,0.08)';">
                <div style="flex:none;">
                    <h4 style="
                        margin-bottom:8px; 
                        font-weight:bold; 
                        font-size:1.05em; 
                        overflow-wrap: break-word;
                        word-wrap: break-word;
                        hyphens: auto;
                    ">
                        <a href="{link}" target="_blank" style="text-decoration:none; color:#111;">{title}</a>
                    </h4>
                    <p style="margin:2px 0; font-size:0.9em;">🔹 <strong>Year:</strong> {year}</p>
                    <p style="margin:2px 0; font-size:0.9em;">🌊 <strong>River:</strong> {river}</p>
                    <p style="
                        margin:2px 0; 
                        font-size:0.9em; 
                        overflow-x:auto; 
                        white-space:nowrap;
                        border-bottom:1px dashed #ccc;
                        padding-bottom:2px;
                    ">🏷️ <strong>Keywords:</strong> {keywords}</p>
                </div>
                <div style="
                    margin-top:8px; 
                    flex-grow:1; 
                    overflow-y:auto;
                ">
                    <details>
                        <summary style='cursor:pointer; font-weight:bold;'>Summary</summary>
                        <div style='margin-top:5px;'>{summary}</div>
                    </details>
                </div>
            </div>
        """, unsafe_allow_html=True)
    # Add spacing between rows
    st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)
