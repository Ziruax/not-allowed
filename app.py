import streamlit as st
import pandas as pd
import requests
import re
import time
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from html import unescape

# Streamlit Configuration
st.set_page_config(
    page_title="WhatsApp Group Manager Pro",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Constants
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9"
}
WHATSAPP_PATTERN = re.compile(r'https://chat\.whatsapp\.com/(?:invite/)?[A-Za-z0-9]{22}')
IMAGE_PATTERN = re.compile(r'https:\/\/pps\.whatsapp\.net\/.*\.jpg(\?.*&.*)?')
MAX_WORKERS = 3

def search_google(query: str, pages: int) -> list:
    """Search Google and extract WhatsApp group links from result pages"""
    session = requests.Session()
    all_links = set()
    
    try:
        for page in range(pages):
            url = f"https://www.google.com/search?q={query}&start={page*10}"
            response = session.get(url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract all valid WhatsApp links from page
            for link in soup.find_all('a', href=True):
                href = link['href']
                if href.startswith('/url?q='):
                    clean_url = href.split('/url?q=')[1].split('&')[0]
                    if WHATSAPP_PATTERN.match(clean_url):
                        all_links.add(clean_url)
            
            time.sleep(2)  # Avoid rate limiting
            
    except Exception as e:
        st.error(f"Search error: {str(e)}")
    
    return list(all_links)

def validate_group(link: str) -> dict:
    """Validate WhatsApp group link and extract metadata"""
    result = {
        "Group Name": "Expired",
        "Invite Link": link,
        "Logo URL": "",
        "Status": "❌ Expired",
        "Members": "N/A"
    }
    
    try:
        with requests.Session() as session:
            # Check link validity
            response = session.head(link, headers=HEADERS, timeout=10, allow_redirects=True)
            final_url = response.url
            
            if not WHATSAPP_PATTERN.match(final_url):
                return result
                
            # Get full page content
            response = session.get(final_url, headers=HEADERS, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Check for expiration markers
            if any(text in response.text.lower() for text in ["expired", "invalid", "not exist"]):
                return result
                
            # Extract metadata
            result['Status'] = "✅ Active"
            if meta := soup.find('meta', property='og:title'):
                result['Group Name'] = unescape(meta['content']).strip()
            
            # Extract member count
            if desc := soup.find('meta', property='og:description'):
                if match := re.search(r'(\d+)\s+members', desc['content']):
                    result['Members'] = match.group(1)
            
            # Extract valid image URL
            if img := soup.find('img', {'src': IMAGE_PATTERN}):
                result['Logo URL'] = unescape(img['src']).replace('&amp;', '&')
                # Verify image URL
                if not session.head(result['Logo URL'], timeout=5).ok:
                    result['Logo URL'] = ""
                
    except Exception as e:
        pass
        
    return result

def main():
    st.title("WhatsApp Group Manager Pro 🔍")
    
    # Initialize session state
    if 'results' not in st.session_state:
        st.session_state.results = []
    
    # Sidebar Controls
    with st.sidebar:
        st.header("Controls ⚙️")
        
        # Google Search Section
        with st.expander("🔍 Google Search", expanded=True):
            search_query = st.text_input("Search Query:", "programming WhatsApp groups")
            search_pages = st.slider("Pages to Search:", 1, 5, 2)
            if st.button("Search & Validate"):
                with st.spinner(f"Searching {search_pages} Google pages..."):
                    links = search_google(search_query, search_pages)
                    if links:
                        st.session_state.results = []
                        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                            futures = [executor.submit(validate_group, link) for link in links]
                            for future in as_completed(futures):
                                st.session_state.results.append(future.result())
                    else:
                        st.error("No links found in search results")

        # Manual Input Section
        with st.expander("📥 Add Custom Links", expanded=True):
            custom_links = st.text_area("Paste links (one per line):")
            if st.button("Validate Custom Links"):
                links = [link.strip() for link in custom_links.split('\n') if link.strip()]
                if links:
                    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                        futures = [executor.submit(validate_group, link) for link in links]
                        for future in as_completed(futures):
                            st.session_state.results.append(future.result())

        # File Upload Section
        with st.expander("📤 Upload Links File"):
            uploaded_file = st.file_uploader("Upload CSV/TXT", type=["csv", "txt"])
            if uploaded_file and st.button("Validate Uploaded Links"):
                if uploaded_file.name.endswith('.csv'):
                    links = pd.read_csv(uploaded_file).iloc[:, 0].tolist()
                else:
                    links = [line.decode().strip() for line in uploaded_file.readlines()]
                if links:
                    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                        futures = [executor.submit(validate_group, link) for link in links]
                        for future in as_completed(futures):
                            st.session_state.results.append(future.result())

    # Main Display Area
    st.header("Results 📊")
    
    if st.session_state.results:
        df = pd.DataFrame(st.session_state.results)
        active_df = df[df['Status'] == '✅ Active']
        
        # Statistics Cards
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Links", len(df))
        col2.metric("Active Groups", len(active_df))
        col3.metric("Success Rate", f"{(len(active_df)/len(df)*100:.1f}%")
        
        # Data Display
        st.dataframe(
            active_df,
            column_config={
                "Logo URL": st.column_config.LinkColumn(
                    "Group Logo",
                    help="Click to view image",
                    display_text="View ➡️"
                ),
                "Invite Link": st.column_config.LinkColumn(
                    "Join Group",
                    help="Click to join WhatsApp group"
                )
            },
            height=600,
            use_container_width=True
        )
        
        # Data Management
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Clear Results"):
                st.session_state.results = []
                st.experimental_rerun()
        
        with col2:
            csv = active_df.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                "Download Active Groups",
                csv,
                "active_groups.csv",
                "text/csv",
                help="Excel-friendly format"
            )
    else:
        st.info("No validation results available. Perform a search or upload links to begin.")

if __name__ == "__main__":
    main()
