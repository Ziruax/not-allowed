import streamlit as st
import pandas as pd
import requests
import re
import time
from html import unescape
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

# Streamlit Configuration
st.set_page_config(
    page_title="WhatsApp Group Validator Pro",
    page_icon="✅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Constants
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9"
}
WHATSAPP_PATTERN = re.compile(r'https://chat\.whatsapp\.com/(invite/)?[a-zA-Z0-9]{22}')
IMAGE_PATTERN = re.compile(r'https:\/\/pps\.whatsapp\.net\/.*\.jpg\?[^&]*&[^&]+')
MAX_WORKERS = 3

@st.cache_data(show_spinner=False)
def google_search(query: str, pages: int = 3) -> list:
    """Robust Google search with link extraction"""
    session = requests.Session()
    links = set()
    
    try:
        for page in range(pages):
            url = f"https://www.google.com/search?q={query}&start={page*10}"
            response = session.get(url, headers=HEADERS, timeout=15)
            
            # Extract all URLs from page
            all_links = re.findall(r'https?://[^\s"\'<>]+', response.text)
            whatsapp_links = [link for link in all_links if WHATSAPP_PATTERN.match(link.split("&")[0])]
            links.update(whatsapp_links)
            
            time.sleep(2)  # Avoid blocking
            
    except Exception as e:
        st.error(f"Search failed: {str(e)}")
    return list(links)[:20]

def validate_group(link: str) -> dict:
    """Comprehensive group validation"""
    result = {
        "name": "Expired Group",
        "link": link,
        "image": "",
        "status": "Expired",
        "members": "N/A"
    }
    
    try:
        with requests.Session() as session:
            # Follow redirects and get final URL
            response = session.head(link, headers=HEADERS, timeout=10, allow_redirects=True)
            final_url = response.url
            
            # Check if link is expired
            if "chat.whatsapp.com" not in final_url or "invite" not in final_url:
                return result
                
            # Get full page content
            response = session.get(link, headers=HEADERS, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Check for expiration markers
            if any(text in response.text for text in ["expired", "not exist", "invalid"]):
                return result
                
            # Extract group info
            result['status'] = "Active"
            result['name'] = unescape(soup.find('meta', property='og:title')['content']).strip()
            
            # Member count extraction
            if desc := soup.find('meta', property='og:description'):
                if members := re.search(r'(\d+)\s+members', desc['content']):
                    result['members'] = members.group(1)
            
            # Image URL validation
            if img := soup.find('img', {'src': IMAGE_PATTERN}):
                result['image'] = unescape(img['src']).replace('&amp;', '&')
                if not requests.head(result['image'], timeout=5).ok:
                    result['image'] = ""
                
    except Exception as e:
        pass
        
    return result

def main():
    st.title("WhatsApp Group Validator Pro 🚀")
    
    # Search Section
    with st.form("search_form"):
        col1, col2 = st.columns([3, 1])
        query = col1.text_input("Search Query:", "site:chat.whatsapp.com inurl:invite")
        pages = col2.number_input("Search Pages:", 1, 5, 3)
        
        if st.form_submit_button("🔍 Search & Validate"):
            with st.spinner("Scanning Google..."):
                links = google_search(query, pages)
                st.session_state.links = links
                st.session_state.show_results = True

    # Results Section
    if st.session_state.get('show_results', False):
        if not st.session_state.links:
            st.error("No WhatsApp links found in search results")
            return
            
        st.info(f"Found {len(st.session_state.links)} potential groups. Validating...")
        
        # Progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()
        results = []
        
        # Parallel validation
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(validate_group, link): link for link in st.session_state.links}
            
            for i, future in enumerate(as_completed(futures)):
                result = future.result()
                results.append(result)
                progress = (i+1)/len(futures)
                progress_bar.progress(progress)
                status_text.text(f"Validated {i+1}/{len(futures)} links | Active: {len([r for r in results if r['status'] == 'Active'])}")
        
        # Process results
        df = pd.DataFrame(results)
        valid_df = df[df['status'] == 'Active']
        
        if not valid_df.empty:
            st.success(f"Found {len(valid_df)} active groups!")
            st.dataframe(
                valid_df[['name', 'members', 'link', 'image', 'status']],
                column_config={
                    "image": st.column_config.LinkColumn("Group Image"),
                    "link": st.column_config.LinkColumn("Group Invite")
                },
                height=500,
                use_container_width=True
            )
            
            # Download
            csv = valid_df.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                "💾 Download Active Groups",
                csv,
                "active_groups.csv",
                "text/csv"
            )
        else:
            st.error("No active groups found in the results")

    # File Upload Section
    with st.expander("📤 Upload Custom Links", expanded=False):
        uploaded_file = st.file_uploader("Upload TXT/CSV file", type=["txt", "csv"])
        if uploaded_file and st.button("Validate Uploaded Links"):
            if uploaded_file.name.endswith('.csv'):
                links = pd.read_csv(uploaded_file).iloc[:, 0].tolist()
            else:
                links = [line.decode().strip() for line in uploaded_file.readlines()]
            
            progress_bar = st.progress(0)
            results = []
            
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                futures = {executor.submit(validate_group, link): link for link in links}
                
                for i, future in enumerate(as_completed(futures)):
                    results.append(future.result())
                    progress = (i+1)/len(futures)
                    progress_bar.progress(progress)
            
            df = pd.DataFrame(results)
            valid_df = df[df['status'] == 'Active']
            
            if not valid_df.empty:
                st.success(f"Found {len(valid_df)} active groups in uploaded file")
                st.dataframe(valid_df)
            else:
                st.error("No active groups found in uploaded links")

if __name__ == "__main__":
    main()
