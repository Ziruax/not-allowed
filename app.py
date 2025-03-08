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

def validate_link(link):
    """Validate WhatsApp group link without browser automation"""
    result = {
        "Group Name": "Expired",
        "Group Link": link,
        "Logo URL": "",
        "Status": "Expired"
    }
    
    try:
        # Bypass Cloudflare protection with headers
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9"
        }
        
        response = requests.get(link, headers=headers, timeout=10, allow_redirects=True)
        
        # Check if link is expired
        if WHATSAPP_DOMAIN not in response.url:
            return result
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract group name from meta tags
        meta_title = soup.find('meta', property='og:title')
        result["Group Name"] = unescape(meta_title['content']).strip() if meta_title else "Unnamed Group"
        
        # Find valid image URL
        img_tags = soup.find_all('img', src=True)
        for img in img_tags:
            src = unescape(img['src'])
            if IMAGE_PATTERN.match(src):
                result["Logo URL"] = src.replace('&amp;', '&')
                result["Status"] = "Active"
                break
                
        return result
        
    except Exception as e:
        return result

def main():
    st.title("WhatsApp Group Validator 🚀")
    st.markdown("### Upload your list of WhatsApp group links")
    
    uploaded_file = st.file_uploader("Choose file (TXT/CSV)", type=["txt", "csv"])
    
    if uploaded_file:
        if uploaded_file.name.endswith('.csv'):
            links = pd.read_csv(uploaded_file).iloc[:, 0].tolist()
        else:
            links = [line.decode().strip() for line in uploaded_file.readlines()]
        
        if st.button("Start Validation"):
            progress = st.progress(0)
            status_text = st.empty()
            results = []
            
            for i, link in enumerate(links):
                result = validate_link(link)
                results.append(result)
                progress.progress((i+1)/len(links))
                status_text.text(f"Processed {i+1}/{len(links)} links")
            
            df = pd.DataFrame(results)
            valid_df = df[df['Status'] == 'Active']
            
            st.success(f"Found {len(valid_df)} active groups!")
            
            st.dataframe(
                valid_df,
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
            
            csv = valid_df.to_csv(index=False)
            st.download_button(
                "Download Results",
                csv,
                "valid_groups.csv",
                "text/csv"
            )

if __name__ == "__main__":
    main()
