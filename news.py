import streamlit as st
from gnews import GNews
import pandas as pd
from textblob import TextBlob
from datetime import datetime
import plotly.express as px
import io
import time
import random
import textblob
import nltk
nltk.download("punkt", quiet=True)
nltk.download("brown", quiet=True)
nltk.download("wordnet", quiet=True)
nltk.download("averaged_perceptron_tagger", quiet=True)
nltk.download("conll2000", quiet=True)
nltk.download("movie_reviews", quiet=True)
st.set_page_config(page_title="Akar News Search & Analysis", layout="wide")

# ===================== Custom CSS =====================
st.markdown(
    """
    <style>
    .news-table {
        font-family: 'Segoe UI', sans-serif;
        border-collapse: collapse;
        width: 100%;
    }
    .news-table td, .news-table th {
        border: 1px solid #ddd;
        padding: 8px;
        vertical-align: top;
    }
    .news-table tr:nth-child(even) { background-color: #f2f2f2; }
    .news-table tr:hover { background-color: #ddd; }
    .news-table th {
        padding-top: 12px;
        padding-bottom: 12px;
        text-align: left;
        background-color: #4CAF50;
        color: white;
    }
    .metrics-container {
        display: flex;
        justify-content: space-between;
        margin-bottom: 20px;
        gap: 15px;
        flex-wrap: wrap;
    }
    .metric-box {
        flex: 1;
        min-width: 160px;
        padding: 15px 20px;
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        text-align: center;
        color: white;
    }
    .metric-positive { background: linear-gradient(135deg, #4CAF50, #2E7D32); }
    .metric-neutral  { background: linear-gradient(135deg, #78909C, #455A64); }
    .metric-negative { background: linear-gradient(135deg, #F44336, #C62828); }
    .metric-non      { background: linear-gradient(135deg, #607D8B, #37474F); }
    .metric-total    { background: linear-gradient(135deg, #3F51B5, #1A237E); }
    .metric-value { font-size: 24px; font-weight: bold; margin-bottom: 5px; }
    .metric-label { font-size: 14px; opacity: 0.9; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <h2 style='text-align:center;color:#fff;background:#262730;padding:10px;border-radius:10px;'>
    📰 Urban Baatein News Search and Analysis Portal
    </h2>
    """,
    unsafe_allow_html=True,
)

# ===================== Fixed Queries =====================
FIXED_QUERIES = [
    "urban development",
"city planning",
"slum rehabilitation",
"informal settlements",
"affordable housing",
"urban transport",
"public transport",
"transit oriented development",
"infrastructure development India",
"smart cities mission",
"industrial corridor",
"MOHUA",
"15 minute city",
"mixed use development",
"urban logistics",
"smart mobility",
"sustainable cities",
"climate resilient cities",
"urban heat island",
"Urban inequality",
"Housing right",
]

# Fixed: India + 3 languages
LANGS = [("English", "en"), ("Hindi", "hi"), ("Marathi", "mr")]
COUNTRY = "IN"

# ===================== Session State =====================
if "all_results" not in st.session_state:
    st.session_state.all_results = []
if "seen_keys" not in st.session_state:
    st.session_state.seen_keys = set()
if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame()
if "sources_list" not in st.session_state:
    st.session_state.sources_list = []
if "selected_sources" not in st.session_state:
    st.session_state.selected_sources = []
if "has_fetched" not in st.session_state:
    st.session_state.has_fetched = False


# ===================== Helpers =====================
def reset_state():
    st.session_state.all_results = []
    st.session_state.seen_keys = set()
    st.session_state.df = pd.DataFrame()
    st.session_state.sources_list = []
    st.session_state.selected_sources = []
    st.session_state.has_fetched = False

def normalize_publisher(pub):
    # gnews sometimes returns dict
    if isinstance(pub, dict):
        return pub.get("title") or pub.get("name") or ""
    return "" if pub is None else str(pub)

def add_results(results, query: str, lang_label: str):
    for item in results:
        title = (item.get("title") or "").strip()
        desc = (item.get("description") or "").strip()
        url = (item.get("url") or "").strip()
        publisher = normalize_publisher(item.get("publisher"))
        published = item.get("published date")

        # Unique key
        key = f"{title}||{publisher}||{url}"
        if not title or key in st.session_state.seen_keys:
            continue
        st.session_state.seen_keys.add(key)

        st.session_state.all_results.append({
            "title": title,
            "desc": desc,
            "link": url,
            "media": publisher,
            "published": "" if published is None else str(published),
            "query": query,
            "language": lang_label,
        })

        if publisher and publisher not in st.session_state.sources_list:
            st.session_state.sources_list.append(publisher)

def fetch_one_query(query: str, lang_code: str, lang_label: str, days: int, max_results: int):
    gn = GNews(language=lang_code, country=COUNTRY, period=f"{days}d", max_results=max_results)
    results = gn.get_news(query) or []
    add_results(results, query=query, lang_label=lang_label)


# ===================== UI =====================
st.subheader("Fixed Search Filters")

colA, colB = st.columns([3, 2])
with colA:
    st.info(
        "Runs fixed queries × 3 languages (EN/HI/MR), Country = India.\n"
        "Sentiment: English only (TextBlob). Hindi/Marathi => Non."
    )
with colB:
    if st.button("♻️ Reset"):
        reset_state()
        st.rerun()

days = st.slider("Select day range (past N days)", 1, 30, 2, 1)
max_results = st.slider("Max results per query (per language)", 5, 30, 10, 5)

run_btn = st.button("🚀 Fetch News", type="primary")


# ===================== Fetch Runner =====================
if run_btn:
    reset_state()
    st.session_state.has_fetched = True

    total_steps = len(FIXED_QUERIES) * len(LANGS)
    progress = st.progress(0)
    status = st.empty()

    step = 0
    with st.spinner("Fetching news across all queries & languages..."):
        for q in FIXED_QUERIES:
            for (lang_label, lang_code) in LANGS:
                step += 1
                status.write(f"🔎 [{step}/{total_steps}] {lang_label}: {q}")
                try:
                    fetch_one_query(q, lang_code=lang_code, lang_label=lang_label, days=days, max_results=max_results)
                except Exception as e:
                    st.warning(f"Failed for '{q}' ({lang_label}): {e}")
                progress.progress(step / total_steps)
                time.sleep(random.uniform(0.15, 0.35))

    st.session_state.df = pd.DataFrame(st.session_state.all_results)
    if not st.session_state.df.empty:
        st.session_state.df = st.session_state.df.drop_duplicates(subset=["title", "media", "link"]).reset_index(drop=True)


# ===================== Display =====================
if not st.session_state.df.empty:
    display_df = st.session_state.df.copy()

    # Source filter
    st.subheader("Filter by Source")
    st.session_state.selected_sources = st.multiselect(
        "Select news sources to display",
        options=sorted(st.session_state.sources_list),
        default=[],
    )
    if st.session_state.selected_sources:
        display_df = display_df[display_df["media"].isin(st.session_state.selected_sources)].copy()

    # Sentiment:
    # English -> TextBlob
    # Hindi/Marathi -> Non
    display_df["polarity"] = None
    display_df["sentiment"] = "Non"

    mask_en = display_df["language"].eq("English")
    # Use title + desc (better than desc alone)
    display_df.loc[mask_en, "polarity"] = (display_df.loc[mask_en, "title"].fillna("") + ". " + display_df.loc[mask_en, "desc"].fillna("")).apply(
        lambda x: TextBlob(str(x)).sentiment.polarity
    )
    display_df.loc[mask_en, "sentiment"] = display_df.loc[mask_en, "polarity"].apply(
        lambda x: "Positive" if x > 0 else ("Negative" if x < 0 else "Neutral")
    )

    sentiment_colors = {"Positive": "green", "Negative": "red", "Neutral": "gray", "Non": "#607D8B"}

    st.success(f"Showing {len(display_df)} articles (past {days} days).")

    # Table
    df_display = display_df[
        ["title", "media", "published", "language", "query", "desc", "link", "sentiment"]
    ].copy()

    df_display["Sentiment"] = df_display["sentiment"].apply(
        lambda x: f"<span style='color:{sentiment_colors.get(x, 'black')};font-weight:600'>{x}</span>"
    )
    df_display["Title"] = df_display.apply(
        lambda row: f"<a href='{row['link']}' target='_blank'>{row['title']}</a>" if row["link"] else row["title"],
        axis=1
    )

    df_display = df_display.rename(
        columns={
            "media": "Source",
            "language": "Language",
            "query": "Matched Query",
            "desc": "Description",
            "published": "Published",
        }
    )

    df_display = df_display[
        ["Title", "Source", "Published", "Language", "Matched Query", "Description", "Sentiment"]
    ]

    st.subheader("Search Results (All-in-One)")
    st.markdown(df_display.to_html(escape=False, index=False, classes="news-table"), unsafe_allow_html=True)

    # CSV download
    download_df = display_df[
        ["title", "media", "published", "language", "query", "desc", "link", "sentiment"]
    ].copy().rename(columns={
        "title": "Title",
        "media": "Source",
        "published": "Published",
        "language": "Language",
        "query": "Matched Query",
        "desc": "Description",
        "link": "URL",
        "sentiment": "Sentiment",
    })

    csv_bytes = download_df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        label="📥 Download Results as CSV",
        data=csv_bytes,
        file_name=f"dharavi_news_{days}d_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv",
        key="download-csv",
    )

    # ===================== Charts (END OF PAGE) =====================
    st.subheader("Overall Tone Summary")

    counts = display_df["sentiment"].value_counts().reindex(["Positive", "Neutral", "Negative", "Non"], fill_value=0)
    total_articles = len(display_df)

    metric_html = f"""
    <div class="metrics-container">
        <div class="metric-box metric-positive">
            <div class="metric-value">{int(counts['Positive'])}</div>
            <div class="metric-label">Positive (EN)</div>
        </div>
        <div class="metric-box metric-neutral">
            <div class="metric-value">{int(counts['Neutral'])}</div>
            <div class="metric-label">Neutral (EN)</div>
        </div>
        <div class="metric-box metric-negative">
            <div class="metric-value">{int(counts['Negative'])}</div>
            <div class="metric-label">Negative (EN)</div>
        </div>
        <div class="metric-box metric-non">
            <div class="metric-value">{int(counts['Non'])}</div>
            <div class="metric-label">Non (HI/MR)</div>
        </div>
        <div class="metric-box metric-total">
            <div class="metric-value">{int(total_articles)}</div>
            <div class="metric-label">Total Articles</div>
        </div>
    </div>
    """
    st.markdown(metric_html, unsafe_allow_html=True)

    pie_fig = px.pie(
        names=counts.index,
        values=counts.values,
        title="Overall Sentiment Distribution",
        hole=0.55,
    )
    pie_fig.update_traces(textinfo="percent")
    st.plotly_chart(pie_fig, use_container_width=True)

elif st.session_state.has_fetched:
    st.warning("No articles found for the selected filters.")
else:
    st.info("Select day range and click **Fetch News**.")
