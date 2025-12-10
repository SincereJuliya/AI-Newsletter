import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import json
import os
import numpy as np 
import re 
from datetime import datetime 

# ==========================
# Configuration and Data
# ==========================
AI_DIGEST_FILE = "new_articles_digest_ai.csv" 
ARTICLES_FILE = "new_articles_digest.csv"     

GEOJSON_FOLDER = "geo"

# River colors mapping
COLOR_MAP = {
    "Po": "#1f77b4",       # blue
    "Adige": "#ff7f0e",    # orange
    "Chiese": "#2ca02c",   # green
    "Noce": "#9467bd",     # purple
    "Sarca": "#8c564b",    # brown
    "Brenta": "#e377c2",   # pink
    "Avisio": "#7f7f7f"    # gray
}

# Map center coordinates for focused view
CENTER_MAP = {
    "Po": [45.0, 9.5],      
    "Adige": [45.5, 11.0],  
    "Chiese": [45.7, 10.5], 
    "Noce": [46.3, 11.0],   
    "Sarca": [46.0, 10.9],  
    "Brenta": [45.6, 11.7], 
    "Avisio": [46.3, 11.5], 
    "Others": [43.5, 12.5], 
    "default": [43.5, 12.5] 
}

# Map zoom levels
ZOOM_MAP = {
    "Po": 7,
    "Adige": 8,
    "Chiese": 9,
    "Noce": 10,
    "Sarca": 10,
    "Brenta": 9,
    "Avisio": 10,
    "Others": 6,
    "default": 6
}

# ==========================
# Load Digest Data
# ==========================
known_rivers = list(COLOR_MAP.keys())

# --- 1. Load Summary File ---
try:
    df_digest = pd.read_csv(AI_DIGEST_FILE)
    df_digest.columns = df_digest.columns.str.strip() 
except FileNotFoundError:
    st.error(f"Error: File not found: {AI_DIGEST_FILE}. Please ensure the file exists.")
    st.stop()
except pd.errors.EmptyDataError:
    st.warning(f"Warning: The file {AI_DIGEST_FILE} is empty. River summaries will be unavailable.")
    df_digest = pd.DataFrame(columns=["river", "summary", "keywords"])


# --- 2. Load Articles File ---
try:
    # Use parse_dates to convert publicationDate column to datetime objects
    df_articles = pd.read_csv(ARTICLES_FILE, parse_dates=['publicationDate'])
    df_articles.columns = df_articles.columns.str.strip() 
except FileNotFoundError:
    st.error(f"Error: File not found: {ARTICLES_FILE}. Please ensure the file exists.")
    st.stop()
except pd.errors.EmptyDataError:
    st.warning(f"Warning: The file {ARTICLES_FILE} is empty. Article listings will be unavailable.")
    df_articles = pd.DataFrame(columns=['title', 'abstract', 'link', 'river', 'year', 'authors', 'keywords', 'publicationDate'])
    
# Check for required columns in df_articles and initialize if missing
required_cols = ['title', 'abstract', 'link', 'river', 'year', 'authors', 'keywords', 'publicationDate']
for col in required_cols:
    if col not in df_articles.columns:
        df_articles[col] = np.nan
    
# --- Extract and Calculate Date Range from publicationDate ---
min_date_str = "N/A"
max_date_str = "N/A"
DATE_FORMAT = "%d %b %Y" # Format: 10 Dec 2025

if 'publicationDate' in df_articles.columns and not df_articles.empty:
    # Drop NaT (Not a Time) values resulting from parsing errors
    dates = df_articles['publicationDate'].dropna()
    
    if not dates.empty:
        min_date = dates.min()
        max_date = dates.max()
        
        # Format dates to string
        min_date_str = min_date.strftime(DATE_FORMAT)
        max_date_str = max_date.strftime(DATE_FORMAT)

# --- Split Digest Data ---
df_digest_summary = df_digest.drop_duplicates(subset=['river'], keep='first')
    
tab_names = known_rivers + ["Others"]

# ==========================
# GeoJSON Loading Function
# ==========================
@st.cache_data
def load_geojson(river_name):
    path = os.path.join(GEOJSON_FOLDER, f"{river_name}.geojson")
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            st.warning(f"Error decoding GeoJSON for {river_name}.")
            return None

# ==========================
# Style Function Factory
# ==========================
def style_function_factory(r_color, is_active=False):
    def style(feature):
        return {
            "color": r_color,
            "weight": 4 if is_active else 2,
            "opacity": 1,
            "fillOpacity": 0.6 if is_active else 0.3,
            "fillColor": r_color,
        }
    return style

# ==========================
# Streamlit Layout
# ==========================
st.set_page_config(layout="wide", page_title="Italy Rivers Digest")
st.markdown("<h2 style='margin-bottom:5px;'>🌊 Italy Rivers Digest</h2>", unsafe_allow_html=True)

# --- CSS Injection for Uniform Article Container Height ---
st.markdown("""
<style>
/* Targets the st.container(border=True) element used for each article card */
/* Увеличен min-height до 350px, чтобы вместить все элементы (включая Абстракт и кнопку) */
div[data-testid="stVerticalBlock"] > div.stContainer {
    min-height: 350px !important; 
    height: 100% !important; 
}
</style>
""", unsafe_allow_html=True)


# --- Display Date Range ---
date_info_html = f"""
    <p style='font-size: 1em; color: #6c757d; margin-top: 0px; margin-bottom: 20px;'>
        Publication Range: Oldest: <span style='font-weight: bold; color: #333;'>{min_date_str}</span> 
        • Newest: <span style='font-weight: bold; color: #333;'>{max_date_str}</span>
    </p>
"""
st.markdown(date_info_html, unsafe_allow_html=True)

fixed_height = 650 

# --- Initialize Session State for Active River ---
if 'active_river' not in st.session_state:
    st.session_state.active_river = tab_names[0]
if 'scroll_flag' not in st.session_state:
    st.session_state.scroll_flag = False

def set_active_river(river_name):
    # Set active river and scroll flag
    st.session_state.active_river = river_name
    st.session_state.scroll_flag = True 

# --------------------
# 1. Top Row (Map and Digest)
# --------------------
col_map, col_digest = st.columns([1.5, 1])

# --------------------
# Left Column: Dynamic Map
# --------------------
with col_map:
    current_focus_river = st.session_state.active_river
    center = CENTER_MAP.get(current_focus_river, CENTER_MAP["default"])
    zoom = ZOOM_MAP.get(current_focus_river, ZOOM_MAP["default"])
    m = folium.Map(location=center, zoom_start=zoom)

    # Use df_digest_summary for the map popups
    for river in known_rivers:
        geo = load_geojson(river)
        if not geo:
            continue

        color = COLOR_MAP.get(river, "#3388ff")
        digest_row = df_digest_summary[df_digest_summary["river"]==river]
        summary = digest_row["summary"].values[0] if not digest_row.empty else "No new reports."
        is_active = river == current_focus_river

        popup_html = f"""
        <div style="font-family:Arial;">
            <h4 style="margin:0; color:{color}; font-weight:700;">{river}</h4>
            <div style="
                max-height:120px; 
                overflow-y:auto; 
                font-size:13px; 
                line-height:1.3;
                word-wrap: break-word;
                white-space: normal;
            ">
                {summary}
            </div>
        </div>
        """

        river_geojson = folium.GeoJson(
            geo,
            name=river,
            tooltip=river,
            popup=folium.Popup(popup_html, max_width=300),
            style_function=style_function_factory(color, is_active),
            highlight_function=lambda feature: {"weight":5, "fillOpacity":0.7}
        )
        river_geojson.add_to(m)

        if is_active:
            try:
                if geo["features"]:
                    feature = geo["features"][0]
                    coords = feature["geometry"]["coordinates"]
                    geom_type = feature["geometry"]["type"]
                    if geom_type == "Point":
                        lat, lon = coords[1], coords[0]
                    elif geom_type == "LineString":
                        lat, lon = coords[0][1], coords[0][0]
                    else:
                        continue

                    folium.CircleMarker(
                        location=(lat, lon),
                        radius=8,
                        color=color,
                        weight=2,
                        fill=True,
                        fill_color=color,
                        fill_opacity=1,
                        tooltip=f"{river} (ACTIVE FOCUS)"
                    ).add_to(m)
            except Exception:
                pass
            
    folium.LayerControl().add_to(m)
    st_folium(m, width=900, height=fixed_height, returned_objects=[])

# --------------------
# Right Column: Digest Tabs
# --------------------
with col_digest:
    tabs = st.tabs(tab_names)

    for i, river_name in enumerate(tab_names):
        with tabs[i]:
            current_river = river_name
            color = COLOR_MAP.get(current_river, "#444")
            
            st.markdown(f"<h4 style='color:{color}; margin-top:0px; margin-bottom: 10px;'>{current_river} Digest</h4>", unsafe_allow_html=True)
            
            # Focus button / Article selector
            if st.session_state.active_river != river_name:
                st.button(
                    f"Show Articles for {river_name}", 
                    key=f"focus_{river_name}", 
                    on_click=set_active_river, 
                    args=(river_name,),
                    use_container_width=True
                )
            else:
                st.markdown(f"**Articles and map focused on {river_name}.**", unsafe_allow_html=True)

            # --- Display General Summary ---
            with st.container(): 
                
                # Get summary and keywords
                summary_data = df_digest_summary[df_digest_summary["river"] == current_river]
                general_summary = summary_data["summary"].values[0] if not summary_data.empty else "No new reports for this river."
                
                st.markdown("##### 📝 General Summary")
                st.markdown(general_summary)
                
                # Category Keywords (from AI_DIGEST_FILE)
                keywords_row = df_digest_summary[df_digest_summary["river"] == current_river]
                if not keywords_row.empty:
                    kws = keywords_row['keywords'].values[0]
                    if kws and pd.notna(kws):
                        kw_list = [kw.strip() for kw in str(kws).split(";")]
                        st.markdown("---")
                        st.markdown(f"<p style='color:gray; font-size:12px; margin-top:10px;'>Keywords: {', '.join(kw_list)}</p>", unsafe_allow_html=True)


# --------------------
# 2. Bottom Row (Dynamic Article List)
# --------------------

st.divider()

# !!! Scroll Target Anchor !!!
st.markdown('<div id="articles_target"></div>', unsafe_allow_html=True) 

st.markdown(f"## 📚 Articles Related to {st.session_state.active_river}")

# --- Article Filtering Logic ---
active_river = st.session_state.active_river
articles_data = pd.DataFrame()

if not df_articles.empty:
    if active_river == "Others":
        # Filter articles where 'river' is NOT in the list of known rivers
        articles_data = df_articles[~df_articles['river'].isin(known_rivers)].copy()
    elif active_river in known_rivers:
        # Filter articles by the active river
        articles_data = df_articles[df_articles['river'] == active_river].copy()

# --- Display Articles (stable st.columns(4)) ---
if not articles_data.empty:
    # Set to 4 columns
    cols = st.columns(4) 
    
    for idx, row in articles_data.iterrows():
        col = cols[idx % 4] 
        
        with col:
            title = row.get('title', 'N/A Title')
            article_summary = row.get('abstract', 'No summary available.') 
            link = row.get('link')
            year = row.get('year', 'N/A')
            authors = row.get('authors', 'N/A')
            
            # Individual article keywords (from ARTICLES_FILE, column 'keywords')
            article_keywords_raw = row.get('keywords') 
            
            # River tag handling
            river_tag_raw = row.get('river')
            if pd.isna(river_tag_raw) or river_tag_raw == 'N/A':
                final_tag = active_river
            else:
                final_tag = river_tag_raw

            # Date formatting (uses publicationDate if available)
            display_date = str(year)
            if 'publicationDate' in row and pd.notna(row['publicationDate']):
                try:
                    # Use accurate year from date if 'year' is undefined
                    if pd.isna(year):
                        year = row['publicationDate'].year
                    
                    # Format the date for display
                    display_date = row['publicationDate'].strftime("%d %b %Y") # e.g., 10 Dec 2025
                    
                except AttributeError:
                    # Fallback to year if parsing fails
                    pass
                
            if pd.isna(title):
                continue
                
            with st.container(border=True): # <--- This container gets the min-height CSS
                
                # --- Заголовок: Горизонтальная прокрутка ---
                st.markdown(f"""
                <h4 style="
                    white-space: nowrap; 
                    overflow-x: auto; 
                    overflow-y: hidden;
                    margin-top: 0;
                    margin-bottom: 5px;
                ">
                {title}
                </h4>
                """, unsafe_allow_html=True)
                
                # --- Авторы: Горизонтальная прокрутка (ВСЕГДА ВЫВОДИМ) ---
                # Получаем чистый текст авторов или 'N/A'
                authors_text = authors if pd.notna(authors) and authors != 'N/A' else 'N/A'
                
                # Вставляем чистый текст, используя HTML-теги <b> и <i> вместо Markdown ** и *
                st.markdown(f"""
                <div style="
                    white-space: nowrap; 
                    overflow-x: auto; 
                    overflow-y: hidden;
                    margin-bottom: 5px;
                ">
                    <b>Authors:</b> <i>{authors_text}</i>
                </div>
                """, unsafe_allow_html=True)
                
                # --- Тег/Дата: Горизонтальная прокрутка (ВСЕГДА ВЫВОДИМ) ---
                if active_river == "Others" and final_tag != "Others":
                    tag_display = f"<span style='background-color: #e0e0e0; color: #444; padding: 2px 6px; border-radius: 3px; font-weight: 500; font-size: 0.9em;'>Original Tag: {final_tag}</span>"
                else:
                    tag_display = f"<span style='font-size: 0.9em; color: {COLOR_MAP.get(active_river, '#6c757d')};'>River Tag: {final_tag}</span>"

                st.markdown(f"""
                <p style='margin-bottom: 5px; white-space: nowrap; overflow-x: auto; overflow-y: hidden;'>
                    {tag_display} ({display_date})
                </p>
                """, unsafe_allow_html=True)
                
                # --- Ключевые слова: Горизонтальная прокрутка (ВОЗВРАЩАЕМ СТИЛИ) ---
                
                article_keywords_formatted = ""
                keywords_list = []
                
                if pd.notna(article_keywords_raw) and article_keywords_raw:
                    kw_str = str(article_keywords_raw).strip()
                    
                    # 1. Deep cleaning: remove unwanted start/end chars (quotes, extra whitespace)
                    kw_str = re.sub(r'^[\s"\'\-]+|[\s"\'\-]+$', '', kw_str) 
                    
                    # 2. Parsing logic: Prioritize ; then , then treat as single string
                    if ';' in kw_str:
                        keywords_list = [kw.strip() for kw in kw_str.split(';') if kw.strip()]
                    elif ',' in kw_str:
                        keywords_list = [kw.strip() for kw in kw_str.split(',') if kw.strip()]
                    else:
                        if kw_str:
                            keywords_list = [kw_str]
                
                # Badge style: reduced size and nowrap for better fit
                badge_style = "background-color: #e8e8e8; color: #333; padding: 2px 5px; border-radius: 4px; font-size: 0.75em; margin-right: 5px; margin-bottom: 5px; display: inline-block; white-space: nowrap;"
                
                if keywords_list:
                    for kw in keywords_list:
                        final_kw = kw.strip()
                        if final_kw:
                            # Apply styling as a badge
                            article_keywords_formatted += f"<span style='{badge_style}'>{final_kw}</span>"
                
                # Если ключевых слов нет или они пустые, выводим N/A (без стилизации баджей, просто текст)
                if not article_keywords_formatted:
                     article_keywords_formatted = "N/A"
                     
                # Wrap keywords in a div for horizontal scroll
                # Используем <b> для "Keywords:"
                st.markdown(f"""
                <div style="
                    margin-top: 5px; 
                    margin-bottom: 0; 
                    white-space: nowrap; 
                    overflow-x: auto; 
                    overflow-y: hidden;
                ">
                    <b>Keywords:</b> {article_keywords_formatted}
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown("---")
                
                with st.expander("Show Abstract"):
                    if pd.notna(article_summary):
                        st.markdown(article_summary) 
                    
                if link and pd.notna(link):
                    st.link_button("Read Full Article (External Link)", url=link, type="primary", use_container_width=True)
else:
    st.info(f"No individual articles found for **{active_river}**.")
    
# --------------------
# 3. SCROLL LOGIC
# --------------------
if st.session_state.scroll_flag:
    scroll_script = """
    <script>
        setTimeout(function() {
            const target = document.getElementById('articles_target');
            if (target) {
                target.scrollIntoView({behavior: 'smooth', block: 'start'});
            }
        }, 100); 
    </script>
    """
    st.markdown(scroll_script, unsafe_allow_html=True)
    st.session_state.scroll_flag = False