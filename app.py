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
    page_title="WhatsApp Group Finder",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Constants
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9"
}
WHATSAPP_PATTERN = re.compile(r'https://chat\.whatsapp\.com/(invite/)?[a-zA-Z0-9]{22}')
MAX_WORKERS = 3

def search_and_scrape_links(query: str, pages: int) -> list:
    """Search Google and scrape WhatsApp links from all result pages"""
    session = requests.Session()
    all_links = set()
    
    try:
        for page in range(pages):
            url = f"https://www.google.com/search?q={query}&start={page*10}"
            response = session.get(url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all links in search results
            for result in soup.find_all('div', {'class': 'g'}):
                link = result.find('a', href=True)
                if link and (href := link['href']):
                    if href.startswith('/url?q='):
                        href = href.split('/url?q=')[1].split('&')[0]
                    if WHATSAPP_PATTERN.match(href):
                        all_links.add(href)
            
            time.sleep(2)  # Avoid getting blocked
            
    except Exception as e:
        st.error(f"Search error: {str(e)}")
    
    return list(all_links)

def validate_whatsapp_link(link: str) -> dict:
    """Validate WhatsApp group link and extract information"""
    result = {
        "name": "Expired",
        "link": link,
        "logo": "",
        "status": "Expired"
    }
    
    try:
        with requests.Session() as session:
            # Follow redirects to final URL
            response = session.head(link, headers=HEADERS, timeout=10, allow_redirects=True)
            final_url = response.url
            
            # Check if link is valid
            if "chat.whatsapp.com" not in final_url or "invite" not in final_url:
                return result
                
            # Get full page content
            response = session.get(final_url, headers=HEADERS, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract group info
            result['status'] = "Active"
            result['name'] = unescape(soup.find('meta', property='og:title')['content']).strip()
            
            # Extract logo URL
            if img := soup.find('img', {'src': re.compile(r'\.jpg(\?|$)'}):
                result['logo'] = unescape(img['src']).replace('&amp;', '&')
                
    except Exception as e:
        pass
        
    return result

def main():
    st.title("WhatsApp Group Finder & Validator 🔍")
    
    # Search Interface
    with st.form("search_form"):
        col1, col2 = st.columns([3, 1])
        query = col1.text_input("Enter search query:", "programming whatsapp groups")
        pages = col2.number_input("Number of Google pages:", 1, 5, 3)
        
        if st.form_submit_button("🚀 Search & Validate"):
            with st.spinner(f"Searching {pages} Google pages..."):
                # Step 1: Search Google and scrape links
                links = search_and_scrape_links(query, pages)
                st.session_state.links = links
                st.session_state.show_results = True

    # Results Display
    if st.session_state.get('show_results', False):
        if not st.session_state.links:
            st.error("No WhatsApp links found in search results")
            return
            
        st.info(f"Found {len(st.session_state.links)} potential groups. Validating...")
        
        # Progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()
        results = []
        
        # Step 2: Validate links in parallel
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(validate_whatsapp_link, link): link for link in st.session_state.links}
            
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
            
            # Display results with image previews
            st.dataframe(
                valid_df[['name', 'link', 'logo', 'status']],
                column_config={
                    "logo": st.column_config.LinkColumn(
                        "Group Logo",
                        help="Click to view image",
                        validate="^https://.*",
                        display_text="View Logo"
                    ),
                    "link": st.column_config.LinkColumn(
                        "Invite Link",
                        help="Click to join group"
                    )
                },
                height=600,
                use_container_width=True
            )
            
            # CSV Download
            csv = valid_df.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                "💾 Download Active Groups",
                csv,
                "active_groups.csv",
                "text/csv",
                help="Excel-friendly CSV format"
            )
        else:
            st.error("No active groups found in the search results")

if __name__ == "__main__":
    main()
