import streamlit as st
import pandas as pd
import requests
from html import unescape
from bs4 import BeautifulSoup
import re
import time
import random
from fake_useragent import UserAgent

# Streamlit Configuration
st.set_page_config(
    page_title="WhatsApp Link Validator",
    page_icon="✅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Constants
WHATSAPP_DOMAIN = "https://chat.whatsapp.com/"
IMAGE_PATTERN = re.compile(r'https:\/\/pps\.whatsapp\.net\/.*\.jpg\?[^&]*&[^&]+')

# Custom CSS for UI
st.markdown("""
    <style>
    .main-title { font-size: 2.5em; color: #25D366; text-align: center; margin-bottom: 0; font-weight: bold; }
    .subtitle { font-size: 1.2em; color: #4A4A4A; text-align: center; margin-top: 0; }
    .stButton>button { background-color: #25D366; color: #FFFFFF; border-radius: 8px; font-weight: bold; border: none; padding: 8px 16px; }
    .stButton>button:hover { background-color: #1EBE5A; color: #FFFFFF; }
    .stProgress .st-bo { background-color: #25D366; }
    .metric-card { background-color: #F5F6F5; padding: 12px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); color: #333333; text-align: center; }
    .stTextInput, .stTextArea { border: 1px solid #25D366; border-radius: 5px; }
    .sidebar .sidebar-content { background-color: #F5F6F5; }
    .stExpander { border: 1px solid #E0E0E0; border-radius: 5px; }
    </style>
""", unsafe_allow_html=True)

# Initialize fake User-Agent generator
ua = UserAgent()

def validate_link(link):
    """Validate a WhatsApp group link with anti-detection headers."""
    result = {"Group Name": "Expired", "Group Link": link, "Logo URL": "", "Status": "Expired"}
    try:
        headers = {
            "User-Agent": ua.random,  # Random User-Agent to mimic different browsers
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Referer": "https://www.google.com/"  # Fake referer to look legit
        }
        response = requests.get(link, headers=headers, timeout=10, allow_redirects=True)
        if WHATSAPP_DOMAIN not in response.url:
            return result
        soup = BeautifulSoup(response.text, 'html.parser')
        meta_title = soup.find('meta', property='og:title')
        result["Group Name"] = unescape(meta_title['content']).strip() if meta_title and meta_title.get('content') else "Unnamed Group"
        img_tags = soup.find_all('img', src=True)
        for img in img_tags:
            src = unescape(img['src'])
            if IMAGE_PATTERN.match(src):
                result["Logo URL"] = src
                result["Status"] = "Active"
                break
        time.sleep(random.uniform(0.5, 1.5))  # Random delay to mimic human behavior
        return result
    except Exception:
        return result

def scrape_whatsapp_links(url):
    """Scrape WhatsApp group links from a webpage with anti-detection."""
    try:
        headers = {
            "User-Agent": ua.random,
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Referer": "https://www.google.com/"
        }
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        links = [a['href'] for a in soup.find_all('a', href=True) if a['href'].startswith(WHATSAPP_DOMAIN)]
        time.sleep(random.uniform(0.5, 2))  # Random delay
        return links
    except Exception:
        return []

def simulate_google_search(query, num_pages):
    """Simulate Google search with sample URLs (replace with API for production)."""
    sample_urls = [
        "https://www.example.com/islamic-groups",
        "https://www.test.com/whatsapp-links",
        "https://chat.whatsapp.com/DummyGroup1",
        "https://chat.whatsapp.com/DummyGroup2",
        "https://www.dummy.com/community-links"
    ]
    search_results = sample_urls * num_pages
    return list(set(search_results[:num_pages * 5]))  # Limit results

# Placeholder for Google Custom Search API (uncomment and configure for real use)
# def google_custom_search(query, num_pages, api_key, cse_id):
#     """Use Google Custom Search JSON API for real search."""
#     search_results = []
#     for page in range(num_pages):
#         url = f"https://www.googleapis.com/customsearch/v1?key={api_key}&cx={cse_id}&q={query}&start={page * 10 + 1}"
#         response = requests.get(url)
#         data = response.json()
#         items = data.get('items', [])
#         search_results.extend([item['link'] for item in items])
#         time.sleep(1)
#     return list(set(search_results))

def load_links(uploaded_file):
    """Load WhatsApp group links from a file."""
    if uploaded_file.name.endswith('.csv'):
        return pd.read_csv(uploaded_file).iloc[:, 0].tolist()
    else:
        return [line.decode().strip() for line in uploaded_file.readlines()]

def main():
    """Main function for the WhatsApp Group Validator app."""
    st.markdown('<h1 class="main-title">WhatsApp Group Validator 🚀</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Validate WhatsApp group links with advanced features</p>', unsafe_allow_html=True)

    # Sidebar for settings
    with st.sidebar:
        st.header("⚙️ Settings")
        input_method = st.selectbox("Input Method", ["Search and Scrape from Google", "Enter Links Manually", "Upload File (TXT/CSV)"])
        if input_method == "Search and Scrape from Google":
            num_pages = st.slider("Pages to Simulate", min_value=1, max_value=5, value=3)

    # Clear Results Button
    if st.button("🗑️ Clear Results", use_container_width=True):
        if 'results' in st.session_state:
            del st.session_state['results']
        st.success("Results cleared successfully!")

    # Input Section
    with st.container():
        results = []
        
        if input_method == "Search and Scrape from Google":
            st.subheader("🔍 Google Search & Scrape (Simulated)")
            keyword = st.text_input("Search Query:", placeholder="e.g., 'islamic whatsapp groups'", help="Currently simulated; use API for real search")
            if st.button("Search, Scrape, and Validate", use_container_width=True):
                if not keyword:
                    st.warning("Please enter a search query.")
                    return

                with st.spinner("Simulating Google search..."):
                    search_results = simulate_google_search(keyword, num_pages)
                    # For real search, uncomment and configure:
                    # api_key = "YOUR_GOOGLE_API_KEY"
                    # cse_id = "YOUR_CSE_ID"
                    # search_results = google_custom_search(keyword, num_pages, api_key, cse_id)

                if not search_results:
                    st.info("No search results found (simulated).")
                    return

                st.success(f"Found {len(search_results)} webpages. Scraping WhatsApp links...")

                all_links = []
                progress_bar = st.progress(0)
                for idx, url in enumerate(search_results):
                    links = scrape_whatsapp_links(url) if not url.startswith(WHATSAPP_DOMAIN) else [url]
                    all_links.extend(links)
                    progress_bar.progress((idx + 1) / len(search_results))
                    time.sleep(random.uniform(0.1, 0.5))  # Random delay

                unique_links = list(set(all_links))
                if not unique_links:
                    st.warning("No WhatsApp group links found.")
                    return= 0)
                    st.warning("No WhatsApp group links found.")
                    return

                st.success(f"Scraped {len(unique_links)} unique WhatsApp group links. Validating...")

                progress_bar = st.progress(0)
                status_text = st.empty()
                for i, link in enumerate(unique_links):
                    result = validate_link(link)
                    results.append(result)
                    progress_bar.progress((i + 1) / len(unique_links))
                    status_text.text(f"Validated {i + 1}/{len(unique_links)} links")

        elif input_method == "Enter Links Manually":
            st.subheader("📝 Manual Link Entry")
            links_text = st.text_area("Enter WhatsApp Links (one per line):", height=200, placeholder="e.g., https://chat.whatsapp.com/ABC123")
            if st.button("Validate Links", use_container_width=True):
                links = [line.strip() for line in links_text.split('\n') if line.strip()]
                if not links:
                    st.warning("Please enter at least one link.")
                    return

                progress_bar = st.progress(0)
                status_text = st.empty()
                for i, link in enumerate(links):
                    result = validate_link(link)
                    results.append(result)
                    progress_bar.progress((i + 1) / len(links))
                    status_text.text(f"Validated {i + 1}/{len(links)} links")

        elif input_method == "Upload File (TXT/CSV)":
            st.subheader("📥 File Upload")
            uploaded_file = st.file_uploader("Upload TXT or CSV", type=["txt", "csv"])
            if uploaded_file and st.button("Validate File Links", use_container_width=True):
                links = load_links(uploaded_file)
                if not links:
                    st.warning("No links found in the uploaded file.")
                    return

                progress_bar = st.progress(0)
                status_text = st.empty()
                for i, link in enumerate(links):
                    result = validate_link(link)
                    results.append(result)
                    progress_bar.progress((i + 1) / len(links))
                    status_text.text(f"Validated {i + 1}/{len(links)} links")

        if results:
            st.session_state['results'] = results

    # Results Section
    if 'results' in st.session_state:
        df = pd.DataFrame(st.session_state['results'])
        active_df = df[df['Status'] == 'Active']
        expired_df = df[df['Status'] == 'Expired']

        st.subheader("📊 Results Summary")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric("Total Links", len(df))
            st.markdown('</div>', unsafe_allow_html=True)
        with col2:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric("Active Links", len(active_df))
            st.markdown('</div>', unsafe_allow_html=True)
        with col3:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric("Expired Links", len(expired_df))
            st.markdown('</div>', unsafe_allow_html=True)

        with st.expander("🔎 View and Filter Results", expanded=True):
            status_filter = st.multiselect("Filter by Status", options=["Active", "Expired"], default=["Active"])
            filtered_df = df[df['Status'].isin(status_filter)] if status_filter else df
            st.dataframe(
                filtered_df,
                column_config={
                    "Group Link": st.column_config.LinkColumn("Invite Link", display_text="Join Group"),
                    "Logo URL": st.column_config.LinkColumn("Logo")
                },
                height=400,
                use_container_width=True
            )

        col_dl1, col_dl2 = st.columns(2)
        with col_dl1:
            csv_active = active_df.to_csv(index=False)
            st.download_button("📥 Download Active Groups", csv_active, "active_groups.csv", "text/csv", use_container_width=True)
        with col_dl2:
            csv_all = df.to_csv(index=False)
            st.download_button("📥 Download All Results", csv_all, "all_groups.csv", "text/csv", use_container_width=True)

    else:
        st.info("Select an input method to start validating!", icon="ℹ️")

if __name__ == "__main__":
    main()
