import streamlit as st
import pandas as pd
import requests
import re
import time
from html import unescape
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

# Streamlit Configuration
st.set_page_config(
    page_title="WhatsApp Group Validator Pro",
    page_icon="✅",
    layout="wide"
)

# Constants
WHATSAPP_DOMAIN = "https://chat.whatsapp.com/"
IMAGE_PATTERN = re.compile(r'https:\/\/pps\.whatsapp\.net\/.*\.jpg\?[^&]*&[^&]+')
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9"
}

def validate_link(link):
    """Enhanced validation with expiration detection and image verification"""
    result = {
        "Group Name": "Expired",
        "Group Link": link,
        "Logo URL": "",
        "Status": "Expired",
        "Members": "N/A"
    }
    
    try:
        # Initial HEAD request to check redirects
        with requests.Session() as session:
            # Check final redirect URL
            response = session.head(link, headers=HEADERS, timeout=10, allow_redirects=True)
            final_url = response.url
            
            if not final_url.startswith(WHATSAPP_DOMAIN):
                return result
            
            # Get full page content
            response = session.get(final_url, headers=HEADERS, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Check for expiration markers in page content
            page_text = soup.get_text().lower()
            if any(x in page_text for x in ["expired", "invalid", "not exist"]):
                return result
            
            # Extract group metadata
            result["Status"] = "Active"
            if meta_title := soup.find('meta', property='og:title'):
                result["Group Name"] = unescape(meta_title['content']).strip()
            
            # Extract member count
            if meta_desc := soup.find('meta', property='og:description'):
                if members := re.search(r'(\d+)\s+members', meta_desc['content']):
                    result["Members"] = members.group(1)
            
            # Find and verify image URL
            for img in soup.find_all('img', src=True):
                src = unescape(img['src'])
                if IMAGE_PATTERN.match(src):
                    # Verify image exists
                    img_response = session.head(src, timeout=5)
                    if img_response.status_code == 200:
                        result["Logo URL"] = src.replace('&amp;', '&')
                        break
                        
    except Exception as e:
        pass
        
    return result

def google_search(query, pages=3):
    """Search Google and extract WhatsApp links from search results"""
    session = requests.Session()
    all_links = set()
    
    try:
        for page in range(pages):
            url = f"https://www.google.com/search?q={query}&start={page*10}"
            response = session.get(url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract all links from search results
            for link in soup.find_all('a', href=True):
                href = link.get('href')
                if href.startswith('/url?q='):
                    clean_url = href.split('/url?q=')[1].split('&')[0]
                    if clean_url.startswith(WHATSAPP_DOMAIN):
                        all_links.add(clean_url)
            
            time.sleep(2)  # Avoid rate limiting
            
    except Exception as e:
        st.error(f"Google search failed: {str(e)}")
    
    return list(all_links)

def main():
    st.title("WhatsApp Group Validator Pro 🚀")
    
    # Input Section
    with st.expander("🔍 Input Options", expanded=True):
        input_method = st.radio("Select Input Method:", 
                              ["File Upload", "Google Search", "Direct Input"])
        
        links = []
        if input_method == "File Upload":
            uploaded_file = st.file_uploader("Upload TXT/CSV", type=["txt", "csv"])
            if uploaded_file:
                if uploaded_file.name.endswith('.csv'):
                    links = pd.read_csv(uploaded_file).iloc[:, 0].tolist()
                else:
                    links = [line.decode().strip() for line in uploaded_file.readlines()]
        
        elif input_method == "Google Search":
            col1, col2 = st.columns([3, 1])
            search_query = col1.text_input("Search Query:", "site:chat.whatsapp.com inurl:invite")
            search_pages = col2.number_input("Search Pages:", 1, 5, 2)
            if st.button("Search Google"):
                with st.spinner("Searching..."):
                    links = google_search(search_query, search_pages)
        
        elif input_method == "Direct Input":
            raw_links = st.text_area("Paste Links (one per line):")
            links = [link.strip() for link in raw_links.split('\n') if link.strip()]
    
    # Validation Section
    if links and st.button("Start Validation"):
        st.info(f"Processing {len(links)} links...")
        progress = st.progress(0)
        status_text = st.empty()
        results = []
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(validate_link, link): link for link in links}
            
            for i, future in enumerate(as_completed(futures)):
                result = future.result()
                results.append(result)
                progress.progress((i+1)/len(links))
                status_text.text(f"Processed {i+1}/{len(links)} | Active: {len([r for r in results if r['Status'] == 'Active'])}")
        
        # Process results
        df = pd.DataFrame(results)
        valid_df = df[df['Status'] == 'Active']
        
        # Display results
        st.success(f"Found {len(valid_df)} active groups!")
        st.dataframe(
            valid_df,
            column_config={
                "Logo URL": st.column_config.LinkColumn(
                    "Group Logo",
                    help="Click to view image",
                    validate="^https://.*"
                ),
                "Group Link": st.column_config.LinkColumn(
                    "Join Group"
                )
            },
            height=600,
            use_container_width=True
        )
        
        # Download
        csv = valid_df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            "📥 Download Results",
            csv,
            "active_groups.csv",
            "text/csv",
            help="Excel-ready format"
        )

if __name__ == "__main__":
    main()
