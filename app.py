import streamlit as st
import pandas as pd
import requests
import re
from html import unescape
from bs4 import BeautifulSoup

# Streamlit Configuration
st.set_page_config(
    page_title="WhatsApp Link Validator",
    page_icon="✅",
    layout="wide"
)

# Constants
WHATSAPP_DOMAIN = "https://chat.whatsapp.com/"
IMAGE_PATTERN = re.compile(r'https:\/\/pps\.whatsapp\.net\/.*\.jpg\?[^&]*&[^&]+')

def load_links(uploaded_file):
    """Load links from an uploaded TXT or CSV file."""
    if uploaded_file.name.endswith('.csv'):
        return pd.read_csv(uploaded_file).iloc[:, 0].tolist()
    else:
        return [line.decode().strip() for line in uploaded_file.readlines()]

def validate_link(link):
    """Validate WhatsApp group link without browser automation."""
    result = {
        "Group Name": "Expired",
        "Group Link": link,
        "Logo URL": "",
        "Status": "Expired"
    }
    
    try:
        # Headers to bypass Cloudflare protection
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9"
        }
        
        # Follow redirects to get the final URL
        response = requests.get(link, headers=headers, timeout=10, allow_redirects=True)
        
        # Original logic: if final URL doesn't contain WHATSAPP_DOMAIN, link is expired
        if WHATSAPP_DOMAIN not in response.url:
            return result
            
        # Parse HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract group name from meta tags
        meta_title = soup.find('meta', property='og:title')
        result["Group Name"] = unescape(meta_title['content']).strip() if meta_title else "Unnamed Group"
        
        # Find valid image URL using regex pattern
        img_tags = soup.find_all('img', src=True)
        for img in img_tags:
            src = unescape(img['src'])
            if IMAGE_PATTERN.match(src):
                result["Logo URL"] = src.replace('&', '&')
                result["Status"] = "Active"
                break
                
        return result
        
    except Exception as e:
        return result

def main():
    """Main function to run the WhatsApp Group Validator app."""
    st.title("WhatsApp Group Link Validator 🚀")
    st.markdown("### Validate your WhatsApp group links with ease")
    st.markdown("Upload a file or enter links manually to check their status. **Statuses:** Active (valid group), Expired (invalid or expired link).")

    # Input method selection
    input_method = st.selectbox("Choose how to provide links", ["Upload file (TXT/CSV)", "Enter links manually"])
    
    links = []
    if input_method == "Upload file (TXT/CSV)":
        uploaded_file = st.file_uploader("Choose file", type=["txt", "csv"])
        if uploaded_file:
            links = load_links(uploaded_file)
    else:
        links_text = st.text_area("Enter links (one per line)", height=200, placeholder="https://chat.whatsapp.com/...")
        links = [line.strip() for line in links_text.split('\n') if line.strip()]
    
    if links:
        if st.button("Start Validation"):
            progress = st.progress(0)
            status_text = st.empty()
            results = []
            
            # Process each link
            for i, link in enumerate(links):
                result = validate_link(link)
                results.append(result)
                progress.progress((i + 1) / len(links))
                status_text.text(f"Processed {i + 1}/{len(links)} links")
            
            # Create DataFrame with results
            df = pd.DataFrame(results)
            active_df = df[df['Status'] == 'Active']
            expired_df = df[df['Status'] == 'Expired']
            
            # Display summary statistics
            st.success(f"Found {len(active_df)} active groups out of {len(links)} links!")
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Links", len(links))
            col2.metric("Active Links", len(active_df))
            col3.metric("Expired Links", len(expired_df))
            
            # Option to show all links or only active ones
            show_all = st.checkbox("Show all links (including expired)", value=False)
            display_df = df if show_all else active_df
            
            # Display results in a table
            st.dataframe(
                display_df,
                column_config={
                    "Logo URL": st.column_config.LinkColumn(
                        "Group Logo",
                        help="Click to view image",
                        validate="^https://.*"
                    )
                },
                height=500,
                use_container_width=True
            )
            
            # Download button for active groups
            csv = active_df.to_csv(index=False)
            st.download_button(
                "Download Active Groups",
                csv,
                "active_groups.csv",
                "text/csv"
            )
    else:
        st.info("Please upload a file or enter links to start validation.")

if __name__ == "__main__":
    main()
