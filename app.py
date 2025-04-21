import streamlit as st
import pandas as pd
import requests
from html import unescape
from bs4 import BeautifulSoup
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# Streamlit Configuration
st.set_page_config(
    page_title="WhatsApp Link Validator",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Constants
WHATSAPP_DOMAIN = "https://chat.whatsapp.com/"
IMAGE_PATTERN = re.compile(r'https:\/\/pps\.whatsapp\.net\/.*\.jpg\?[^&]*&[^&]+')
GOOGLE_SEARCH_URL = "https://www.google.com/search"
EMOJI_PATTERN = re.compile("["
    u"\U0001F600-\U0001F64F"  # emoticons
    u"\U0001F300-\U0001F5FF"  # symbols & pictographs
    u"\U0001F680-\U0001F6FF"  # transport & map symbols
    u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
    u"\U00002702-\U000027B0"
    u"\U000024C2-\U0001F251"
    "]+", flags=re.UNICODE)

# Custom CSS for enhanced UI
st.markdown("""
    <style>
    .main-title {
        font-size: 2.5em;
        color: #25D366;
        text-align: center;
        margin-bottom: 0;
        font-weight: bold;
    }
    .subtitle {
        font-size: 1.2em;
        color: #4A4A4A;
        text-align: center;
        margin-top: 0;
    }
    .stButton>button {
        background-color: #25D366;
        color: #FFFFFF;
        border-radius: 8px;
        font-weight: bold;
        border: none;
        padding: 8px 16px;
    }
    .stButton>button:hover {
        background-color: #1EBE5A;
        color: #FFFFFF;
    }
    .stProgress .st-bo {
        background-color: #25D366;
    }
    .metric-card {
        background-color: #F5F6F5;
        padding: 12px;
        border-radius: 8px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        color: #333333;
        text-align: center;
    }
    .stTextInput, .stTextArea {
        border: 1px solid #25D366;
        border-radius: 5px;
    }
    .sidebar .sidebar-content {
        background-color: #F5F6F5;
    }
    .stExpander {
        border: 1px solid #E0E0E0;
        border-radius: 5px;
    }
    </style>
""", unsafe_allow_html=True)

def validate_link(link):
    """Validate a WhatsApp group link and return details if active."""
    result = {
        "Group Name": "Unknown",
        "Group Link": link,
        "Logo URL": "",
        "Status": "Error"
    }
    
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9"
        }
        
        response = requests.get(link, headers=headers, timeout=10, allow_redirects=True)
        
        if response.status_code != 200:
            result["Status"] = f"HTTP Error {response.status_code}"
            return result
        
        if WHATSAPP_DOMAIN not in response.url:
            result["Status"] = "Invalid Link"
            return result
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        meta_title = soup.find('meta', property='og:title')
        if meta_title and meta_title.get('content'):
            group_name = unescape(meta_title['content']).strip()
            group_name = EMOJI_PATTERN.sub('', group_name)  # Remove emojis immediately after fetching
            result["Group Name"] = group_name
        else:
            result["Group Name"] = "Unnamed Group"
        
        img_tags = soup.find_all('img', src=True)
        for img in img_tags:
            src = unescape(img['src'])
            if IMAGE_PATTERN.match(src):
                result["Logo URL"] = src
                result["Status"] = "Active"
                break
        else:
            result["Status"] = "Expired"
                
    except requests.exceptions.RequestException as e:
        result["Status"] = f"Network Error: {str(e)}"
    except Exception as e:
        result["Status"] = f"Error: {str(e)}"
    
    return result

def scrape_whatsapp_links(url):
    """Scrape WhatsApp group links from a webpage, handling various HTML structures."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        links = []
        # Check for links in <a> tags
        for a in soup.find_all('a', href=True):
            if a['href'].startswith(WHATSAPP_DOMAIN):
                links.append(a['href'])
        
        # Check for links in text content (e.g., plain text or within <p>, <div>, etc.)
        for text in soup.stripped_strings:
            if WHATSAPP_DOMAIN in text:
                # Extract URLs from text
                found_links = re.findall(r'https?://chat\.whatsapp\.com/[^\s]+', text)
                links.extend(found_links)
        
        return list(set(links))  # Remove duplicates
    except Exception:
        return []

def google_search(query, top_n=5):
    """Fetch URLs from Google's top N search results."""
    search_results = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    params = {
        "q": query,
        "start": 0  # First page only
    }
    try:
        response = requests.get(GOOGLE_SEARCH_URL, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        search_div = soup.find('div', id='search')
        if search_div:
            result_divs = search_div.find_all('div', class_='g', limit=top_n)
            for div in result_divs:
                a_tag = div.find('a', href=True)
                if a_tag and a_tag['href'].startswith('/url?q='):
                    url = a_tag['href'].split('/url?q=')[1].split('&')[0]
                    search_results.append(url)
    except Exception as e:
        st.error(f"Error fetching search results: {e}")
    return search_results

def load_links(uploaded_file):
    """Load WhatsApp group links from an uploaded TXT or CSV file."""
    if uploaded_file.name.endswith('.csv'):
        return pd.read_csv(uploaded_file).iloc[:, 0].tolist()
    else:
        return [line.decode().strip() for line in uploaded_file.readlines()]

def main():
    """Main function for the WhatsApp Group Validator app."""
    st.markdown('<h1 class="main-title">WhatsApp Group Validator 🚀</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Search, scrape, or validate WhatsApp group links with ease</p>', unsafe_allow_html=True)

    # Sidebar for settings
    with st.sidebar:
        st.header("⚙️ Settings")
        st.markdown("Customize your experience")
        input_method = st.selectbox("Input Method", ["Search and Scrape from Google", "Enter Links Manually", "Upload File (TXT/CSV)"], help="Choose how to input links")
        if input_method == "Search and Scrape from Google":
            top_n = st.slider("Number of top Google results to scrape from", min_value=1, max_value=10, value=5, help="Number of top search results to scrape")

    # Clear Results Button
    if st.button("🗑️ Clear Results", use_container_width=True):
        if 'results' in st.session_state:
            del st.session_state['results']
        st.success("Results cleared successfully!")

    # Input Section
    with st.container():
        results = []
        
        if input_method == "Search and Scrape from Google":
            st.subheader("🔍 Google Search & Scrape")
            keyword = st.text_input("Search Query:", placeholder="Whatsapp Group Links", help="Enter a query to search for WhatsApp group links")
            if st.button("Search, Scrape, and Validate", use_container_width=True):
                if not keyword:
                    st.warning("Please enter a search query.")
                    return

                with st.spinner("Searching Google..."):
                    search_results = google_search(keyword, top_n=top_n)

                if not search_results:
                    st.info("No search results found for the query.")
                    return

                st.success(f"Found {len(search_results)} webpages. Scraping WhatsApp links...")

                # Scrape links with progress
                all_links = []
                progress_bar = st.progress(0)
                for idx, url in enumerate(search_results):
                    links = scrape_whatsapp_links(url)
                    all_links.extend(links)
                    progress_bar.progress((idx + 1) / len(search_results))

                unique_links = list(set(all_links))
                if not unique_links:
                    st.warning("No WhatsApp group links found in the scraped webpages.")
                    return

                st.success(f"Scraped {len(unique_links)} unique WhatsApp group links. Validating...")

                # Validate links concurrently
                progress_bar = st.progress(0)
                status_text = st.empty()
                with ThreadPoolExecutor(max_workers=5) as executor:
                    future_to_link = {executor.submit(validate_link, link): link for link in unique_links}
                    for i, future in enumerate(as_completed(future_to_link)):
                        result = future.result()
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
                with ThreadPoolExecutor(max_workers=5) as executor:
                    future_to_link = {executor.submit(validate_link, link): link for link in links}
                    for i, future in enumerate(as_completed(future_to_link)):
                        result = future.result()
                        results.append(result)
                        progress_bar.progress((i + 1) / len(links))
                        status_text.text(f"Validated {i + 1}/{len(links)} links")

        elif input_method == "Upload File (TXT/CSV)":
            st.subheader("📥 File Upload")
            uploaded_file = st.file_uploader("Upload TXT or CSV", type=["txt", "csv"], help="One link per line or in first column")
            if uploaded_file and st.button("Validate File Links", use_container_width=True):
                links = load_links(uploaded_file)
                if not links:
                    st.warning("No links found in the uploaded file.")
                    return

                progress_bar = st.progress(0)
                status_text = st.empty()
                with ThreadPoolExecutor(max_workers=5) as executor:
                    future_to_link = {executor.submit(validate_link, link): link for link in links}
                    for i, future in enumerate(as_completed(future_to_link)):
                        result = future.result()
                        results.append(result)
                        progress_bar.progress((i + 1) / len(links))
                        status_text.text(f"Validated {i + 1}/{len(links)} links")

        # Store results in session state
        if results:
            st.session_state['results'] = results

    # Results Section
    if 'results' in st.session_state:
        df = pd.DataFrame(st.session_state['results'])
        active_df = df[df['Status'] == 'Active']
        expired_df = df[df['Status'] == 'Expired']

        # Summary Metrics
        st.subheader("📊 Results Summary")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric("Total Links", len(df), help="Total links processed")
            st.markdown('</div>', unsafe_allow_html=True)
        with col2:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric("Active Links", len(active_df), help="Valid WhatsApp groups")
            st.markdown('</div>', unsafe_allow_html=True)
        with col3:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric("Expired Links", len(expired_df), help="Invalid or expired links")
            st.markdown('</div>', unsafe_allow_html=True)

        # Filter and Display Results
        with st.expander("🔎 View and Filter Results", expanded=True):
            status_filter = st.multiselect("Filter by Status", options=df['Status'].unique(), default=["Active"], help="Select statuses to display")
            filtered_df = df[df['Status'].isin(status_filter)] if status_filter else df

            st.dataframe(
                filtered_df,
                column_config={
                    "Group Link": st.column_config.LinkColumn("Invite Link", display_text="Join Group", help="Click to join"),
                    "Logo URL": st.column_config.LinkColumn("Logo", help="Click to view logo")
                },
                height=400,
                use_container_width=True
            )

        # Download Buttons
        col_dl1, col_dl2 = st.columns(2)
        with col_dl1:
            csv_active = active_df.to_csv(index=False)
            st.download_button(
                "📥 Download Active Groups",
                csv_active,
                "active_groups.csv",
                "text/csv",
                use_container_width=True
            )
        with col_dl2:
            csv_all = df.to_csv(index=False)
            st.download_button(
                "📥 Download All Results",
                csv_all,
                "all_groups.csv",
                "text/csv",
                use_container_width=True
            )

    else:
        st.info("Select an input method and start validating WhatsApp group links!", icon="ℹ️")

if __name__ == "__main__":
    main()
