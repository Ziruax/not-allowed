import streamlit as st
import pandas as pd
import requests
import re
import time
from html import unescape
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

# Streamlit Configuration (must be first)
st.set_page_config(
    page_title="WhatsApp Group Manager Pro",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Constants
PORT = 8501
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9"
}
WHATSAPP_REGEX = re.compile(r'https://chat\.whatsapp\.com/[^\s"\']+')
IMAGE_REGEX = re.compile(r'https:\/\/pps\.whatsapp\.net\/.*\.jpg\?.*&.*')
MAX_WORKERS = 3

@st.cache_data(show_spinner=False)
def search_google(query: str, pages: int = 2) -> list:
    """Search Google and extract WhatsApp links without JavaScript"""
    session = requests.Session()
    results = set()
    
    try:
        for page in range(pages):
            url = f"https://www.google.com/search?q={query}&start={page*10}"
            response = session.get(url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all search result links
            for link in soup.find_all('a', href=True):
                href = link['href']
                if WHATSAPP_REGEX.match(href):
                    results.add(href)
            
            time.sleep(2)  # Avoid rate limiting
            
    except Exception as e:
        st.error(f"Search error: {str(e)}")
    return list(results)[:20]

def validate_group(link: str) -> dict:
    """Validate WhatsApp group link with enhanced error handling"""
    result = {
        "name": "Expired",
        "link": link,
        "image": "",
        "status": "❌ Expired",
        "members": "N/A"
    }
    
    try:
        with requests.Session() as session:
            response = session.get(link, headers=HEADERS, timeout=10, allow_redirects=True)
            
            if "chat.whatsapp.com" not in response.url:
                return result
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract group metadata
            result['status'] = "✅ Active"
            result['name'] = unescape(soup.find('meta', property='og:title')['content']).strip()
            
            # Find member count
            if desc := soup.find('meta', property='og:description'):
                members = re.search(r'(\d+)\s+members', desc['content'])
                result['members'] = members.group(1) if members else "N/A"
            
            # Find valid image URL
            if img := soup.find('img', src=IMAGE_REGEX):
                result['image'] = unescape(img['src']).replace('&amp;', '&')
                
    except Exception as e:
        pass
        
    return result

def main():
    st.title("WhatsApp Group Manager Pro 🔍")
    st.markdown("### Find & Validate Active WhatsApp Groups")
    
    # Sidebar Controls
    with st.sidebar:
        st.header("Settings ⚙️")
        search_query = st.text_input("Search Query:", "site:chat.whatsapp.com inurl:invite")
        search_pages = st.slider("Google Pages:", 1, 3, 1)
        
        if st.button("🌐 Search Google", type="primary"):
            with st.spinner(f"Searching {search_pages} pages..."):
                links = search_google(search_query, search_pages)
                st.session_state['links'] = links
                st.session_state['search_done'] = True

    # Main Content Area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # File Upload Section
        with st.expander("📤 Upload Links File", expanded=True):
            uploaded_file = st.file_uploader("Choose TXT/CSV", type=["txt", "csv"])
            if uploaded_file:
                if uploaded_file.name.endswith('.csv'):
                    links = pd.read_csv(uploaded_file).iloc[:, 0].tolist()
                else:
                    links = [line.decode().strip() for line in uploaded_file.readlines()]
                st.session_state['links'] = links
                st.session_state['search_done'] = True

        # Results Display
        if st.session_state.get('search_done', False):
            if not st.session_state.get('links', []):
                st.error("No links found for validation!")
                return
                
            st.info(f"Found {len(st.session_state.links)} links. Validating...")
            
            # Progress tracking
            progress_bar = st.progress(0)
            status_text = st.empty()
            results = []
            
            # Parallel validation
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                futures = {executor.submit(validate_group, link): link for link in st.session_state.links}
                
                for i, future in enumerate(as_completed(futures)):
                    results.append(future.result())
                    progress = (i+1)/len(futures)
                    progress_bar.progress(progress)
                    status_text.text(f"Processed {i+1}/{len(futures)} links")
            
            # Process results
            df = pd.DataFrame(results)
            valid_df = df[df['status'] == '✅ Active']
            
            st.success(f"Validation complete! Found {len(valid_df)} active groups")
            
            # Display results
            st.dataframe(
                valid_df[['name', 'members', 'link', 'image', 'status']],
                column_config={
                    "image": st.column_config.LinkColumn("Group Image"),
                    "link": st.column_config.LinkColumn("Group Link")
                },
                height=500,
                use_container_width=True
            )
            
            # CSV Export
            csv = valid_df.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                "💾 Download Results",
                csv,
                "active_groups.csv",
                "text/csv",
                key='download-csv'
            )

    with col2:
        # Single Link Validation
        with st.form("single_validation"):
            st.subheader("Single Link Check")
            single_link = st.text_input("Enter WhatsApp Link:")
            if st.form_submit_button("Validate Now"):
                result = validate_group(single_link)
                st.json({
                    "Group Name": result['name'],
                    "Status": result['status'],
                    "Members": result['members'],
                    "Image URL": result['image'],
                    "Group Link": result['link']
                })

if __name__ == "__main__":
    main()
