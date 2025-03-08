import streamlit as st
import pandas as pd
import requests
import re
import time
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from html import unescape
from urllib.parse import unquote

# Streamlit Configuration
st.set_page_config(
    page_title="WhatsApp Group Finder Pro",
    page_icon="🔍",
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

def get_google_results(query: str, pages: int) -> list:
    """Get actual website URLs from Google search results"""
    session = requests.Session()
    result_urls = []
    
    try:
        for page in range(pages):
            url = f"https://www.google.com/search?q={query}&start={page*10}"
            response = session.get(url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract actual result URLs
            for link in soup.find_all('a', href=True):
                href = link['href']
                if href.startswith('/url?q='):
                    decoded_url = unquote(href.split('&sa=')[0].replace('/url?q=', ''))
                    if decoded_url.startswith('http'):
                        result_urls.append(decoded_url)
            
            time.sleep(2)
            
    except Exception as e:
        st.error(f"Google search failed: {str(e)}")
    
    return list(set(result_urls))[:20]  # Return unique URLs

def scrape_website(url: str) -> list:
    """Scrape WhatsApp links from a website"""
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        return [link['href'] for link in soup.find_all('a', href=WHATSAPP_PATTERN)]
    except:
        return []

def validate_whatsapp_link(link: str) -> dict:
    """Comprehensive WhatsApp link validation"""
    result = {
        "Group Name": "Expired",
        "Invite Link": link,
        "Logo URL": "",
        "Status": "❌ Expired",
        "Scraped From": ""
    }
    
    try:
        with requests.Session() as session:
            # Initial header request to follow redirects
            response = session.head(link, headers=HEADERS, timeout=10, allow_redirects=True)
            final_url = response.url
            
            if not WHATSAPP_PATTERN.match(final_url):
                return result
                
            # Full page request
            response = session.get(final_url, headers=HEADERS, timeout=10)
            if response.status_code != 200:
                return result
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Check for expiration markers
            page_text = soup.get_text().lower()
            if any(x in page_text for x in ["expired", "invalid", "doesn't exist"]):
                return result
                
            # Extract metadata
            result['Status'] = "✅ Active"
            if meta := soup.find('meta', property='og:title'):
                result['Group Name'] = unescape(meta['content']).strip()
                
            # Extract image URL
            if img := soup.find('img', {'src': IMAGE_PATTERN}):
                result['Logo URL'] = unescape(img['src']).replace('&amp;', '&')
                # Verify image exists
                if not session.head(result['Logo URL'], timeout=5).ok:
                    result['Logo URL'] = ""
                
    except Exception as e:
        pass
        
    return result

def main():
    st.title("WhatsApp Group Finder Pro 🔍")
    
    # Session state initialization
    if 'results' not in st.session_state:
        st.session_state.results = []
    
    # Control Panel
    with st.sidebar:
        st.header("Controls ⚙️")
        
        # Google Search Section
        with st.expander("🔍 Google Search", expanded=True):
            search_query = st.text_input("Search Query:", "programming WhatsApp groups")
            search_pages = st.slider("Pages to Search:", 1, 3, 1)
            
            if st.button("Start Search & Validation"):
                with st.spinner("Searching Google..."):
                    # Step 1: Get website URLs from Google
                    website_urls = get_google_results(search_query, search_pages)
                    
                    # Step 2: Scrape WhatsApp links from websites
                    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                        futures = [executor.submit(scrape_website, url) for url in website_urls]
                        whatsapp_links = []
                        for future in as_completed(futures):
                            if links := future.result():
                                whatsapp_links.extend(links)
                        
                        # Step 3: Validate WhatsApp links
                        if whatsapp_links:
                            st.session_state.results = []
                            validation_futures = [executor.submit(validate_whatsapp_link, link) for link in set(whatsapp_links)]
                            for future in as_completed(validation_futures):
                                result = future.result()
                                result["Scraped From"] = next((url for url in website_urls if url in result["Invite Link"]), "")
                                st.session_state.results.append(result)
                        else:
                            st.error("No WhatsApp links found in search results")

        # Direct Input Section
        with st.expander("📥 Custom Links", expanded=True):
            custom_links = st.text_area("Paste links (one per line):")
            if st.button("Validate Links"):
                links = [link.strip() for link in custom_links.split('\n') if link.strip()]
                if links:
                    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                        futures = [executor.submit(validate_whatsapp_link, link) for link in links]
                        st.session_state.results = []
                        for future in as_completed(futures):
                            st.session_state.results.append(future.result())

    # Main Display
    st.header("Results 📊")
    
    if st.session_state.results:
        df = pd.DataFrame(st.session_state.results)
        active_df = df[df['Status'] == '✅ Active']
        
        # Statistics
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Links", len(df))
        col2.metric("Active Groups", len(active_df))
        col3.metric("Success Rate", f"{(len(active_df)/len(df)*100 if len(df) > 0 else 0):.1f}%")
        
        # Data Display
        st.dataframe(
            active_df,
            column_config={
                "Logo URL": st.column_config.LinkColumn(
                    "Group Logo",
                    display_text="View ➡️"
                ),
                "Invite Link": st.column_config.LinkColumn(
                    "Join Group"
                )
            },
            height=600,
            use_container_width=True
        )
        
        # Data Management
        if st.button("Clear Results"):
            st.session_state.results = []
            st.rerun()
        
        # Export
        csv = active_df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            "💾 Download CSV",
            csv,
            "active_groups.csv",
            "text/csv"
        )
    else:
        st.info("No results to display. Perform a search or enter links to begin.")

if __name__ == "__main__":
    main()
