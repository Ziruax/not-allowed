import streamlit as st
import pandas as pd
import requests
from html import unescape
from bs4 import BeautifulSoup
from googlesearch import search  # Third-party library for Google search
import re

# Streamlit Configuration
st.set_page_config(
    page_title="WhatsApp Link Validator",
    page_icon="✅",
    layout="wide"
)

# Constants
WHATSAPP_DOMAIN = "https://chat.whatsapp.com/"
IMAGE_PATTERN = re.compile(r'https:\/\/pps\.whatsapp\.net\/.*\.jpg\?[^&]*&[^&]+')

# Custom CSS for modern styling
st.markdown("""
    <style>
    .main-title {
        font-size: 2.5em;
        color: #25D366;
        text-align: center;
        margin-bottom: 0;
    }
    .subtitle {
        font-size: 1.2em;
        color: #555;
        text-align: center;
        margin-top: 0;
    }
    .stButton>button {
        background-color: #25D366;
        color: white;
        border-radius: 10px;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #128C7E;
    }
    .stProgress .st-bo {
        background-color: #25D366;
    }
    .metric-card {
        background-color: #f9f9f9;
        padding: 10px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    </style>
""", unsafe_allow_html=True)

def validate_link(link):
    """Validate WhatsApp group link without browser automation"""
    result = {
        "Group Name": "Expired",
        "Group Link": link,
        "Logo URL": "",
        "Status": "Expired"
    }
    
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9"
        }
        
        response = requests.get(link, headers=headers, timeout=10, allow_redirects=True)
        
        if WHATSAPP_DOMAIN not in response.url:
            return result
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        meta_title = soup.find('meta', property='og:title')
        result["Group Name"] = unescape(meta_title['content']).strip() if meta_title else "Unnamed Group"
        
        img_tags = soup.find_all('img', src=True)
        for img in img_tags:
            src = unescape(img['src'])
            if IMAGE_PATTERN.match(src):
                result["Logo URL"] = src.replace('&', '&')
                result["Status"] = "Active"
                break
                
        return result
        
    except Exception:
        return result

def scrape_whatsapp_links(url):
    """Scrape WhatsApp group links from a given URL"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        links = []
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            if href.startswith(WHATSAPP_DOMAIN):
                links.append(href)
        return links
    except Exception:
        return []

def main():
    """Main function to run the WhatsApp Group Validator app with keyword search and scraping"""
    st.markdown('<h1 class="main-title">WhatsApp Group Validator 🚀</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Search, scrape, and validate WhatsApp group links with ease</p>', unsafe_allow_html=True)

    # Input Section
    with st.container():
        st.subheader("🔍 Search for WhatsApp Groups")
        keyword = st.text_input("Enter your targeted keyword:", placeholder="e.g., 'music enthusiasts'")

        if st.button("Start Search and Validation", use_container_width=True):
            if not keyword:
                st.warning("Please enter a keyword to search.")
                return

            with st.spinner("Searching Google for webpages..."):
                try:
                    search_results = list(search(keyword, num=20, stop=20, pause=2))
                except Exception as e:
                    st.error(f"Error performing Google search: {e}")
                    return

            if not search_results:
                st.info("No search results found for the given keyword.")
                return

            st.success(f"Found {len(search_results)} webpages. Scraping for WhatsApp group links...")

            all_links = []
            for url in search_results:
                links = scrape_whatsapp_links(url)
                all_links.extend(links)

            unique_links = list(set(all_links))  # Remove duplicates
            st.success(f"Scraped {len(unique_links)} unique WhatsApp group links. Starting validation...")

            progress = st.progress(0)
            status_text = st.empty()
            results = []

            for i, link in enumerate(unique_links):
                result = validate_link(link)
                results.append(result)
                progress.progress((i + 1) / len(unique_links))
                status_text.text(f"Validated {i + 1}/{len(unique_links)} links")

            # Store results in session state for filtering
            st.session_state['results'] = results

    # Results Section
    if 'results' in st.session_state:
        df = pd.DataFrame(st.session_state['results'])
        active_df = df[df['Status'] == 'Active']
        expired_df = df[df['Status'] == 'Expired']

        # Summary Metrics
        st.subheader("📊 Validation Summary")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric("Total Links", len(df), help="Total WhatsApp group links scraped and validated")
            st.markdown('</div>', unsafe_allow_html=True)
        with col2:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric("Active Links", len(active_df), help="Links that are currently valid")
            st.markdown('</div>', unsafe_allow_html=True)
        with col3:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric("Expired Links", len(expired_df), help="Links that are expired or invalid")
            st.markdown('</div>', unsafe_allow_html=True)

        # Filter Options
        with st.expander("🔎 Filter Results", expanded=True):
            status_filter = st.multiselect("Filter by Status", options=["Active", "Expired"], default=["Active"])
            filtered_df = df[df['Status'].isin(status_filter)] if status_filter else df

            # Display Filtered Results
            st.dataframe(
                filtered_df,
                column_config={
                    "Group Link": st.column_config.LinkColumn("Group Link", display_text="Join Group"),
                    "Logo URL": st.column_config.LinkColumn("Group Logo", help="Click to view image")
                },
                height=400,
                use_container_width=True
            )

        # Download Buttons
        col_dl1, col_dl2 = st.columns(2)
        with col_dl1:
            csv_active = active_df.to_csv(index=False)
            st.download_button("📥 Download Active Groups", csv_active, "active_groups.csv", "text/csv", use_container_width=True)
        with col_dl2:
            csv_all = df.to_csv(index=False)
            st.download_button("📥 Download All Results", csv_all, "all_groups.csv", "text/csv", use_container_width=True)

if __name__ == "__main__":
    main()
