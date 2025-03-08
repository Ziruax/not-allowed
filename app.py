import streamlit as st
import pandas as pd
import requests
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

def load_links(uploaded_file):
    """Load links from an uploaded TXT or CSV file."""
    if uploaded_file.name.endswith('.csv'):
        return pd.read_csv(uploaded_file).iloc[:, 0].tolist()
    else:
        return [line.decode().strip() for line in uploaded_file.readlines()]

def validate_link(link):
    """Validate a WhatsApp group link and extract group details."""
    result = {
        "Group Name": "Unknown",
        "Group Link": link,
        "Logo URL": "",
        "Status": "Expired"
    }
    
    # Preliminary check for valid WhatsApp link format
    if not link.startswith(WHATSAPP_DOMAIN):
        result["Status"] = "Invalid"
        return result
    
    try:
        # Headers to mimic a browser request
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9"
        }
        
        # Fetch the link with a timeout and allow redirects
        response = requests.get(link, headers=headers, timeout=10, allow_redirects=True)
        
        # Check if the link is expired based on the final URL
        if WHATSAPP_DOMAIN not in response.url:
            return result  # Expired
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract group name from meta tags
        meta_title = soup.find('meta', property='og:title')
        if meta_title:
            result["Group Name"] = unescape(meta_title['content']).strip()
            result["Status"] = "Active"  # Active if group name is found
        
        # Extract logo URL from the group preview image div
        preview_div = soup.find('div', class_='invite-link-preview-image')
        if preview_div:
            img_tag = preview_div.find('img')
            if img_tag and 'src' in img_tag.attrs:
                result["Logo URL"] = unescape(img_tag['src'])
        
        return result
    
    except Exception as e:
        result["Status"] = "Error"
        return result

def main():
    """Main function to run the WhatsApp Group Validator app."""
    st.title("WhatsApp Group Validator 🚀")
    st.markdown("### Validate your WhatsApp group links")
    st.markdown("This app checks if WhatsApp group links are active and extracts group names and logos.")
    st.markdown("**Possible statuses:** Active, Expired, Invalid, Error")

    # Input method selection
    input_method = st.selectbox("Choose input method", ["Upload file", "Enter links manually"])
    
    if input_method == "Upload file":
        uploaded_file = st.file_uploader("Choose file (TXT/CSV)", type=["txt", "csv"])
        if uploaded_file:
            links = load_links(uploaded_file)
        else:
            links = []
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
            
            # Create DataFrame with all results
            df = pd.DataFrame(results)
            valid_df = df[df['Status'] == 'Active']
            
            # Display summary statistics
            st.success(f"Found {len(valid_df)} active groups out of {len(links)} links!")
            st.write(f"**Total links processed:** {len(links)}")
            st.write(f"**Active links:** {len(valid_df)}")
            st.write(f"**Expired/Invalid/Error links:** {len(df) - len(valid_df)}")
            
            # Option to show all links or only active ones
            show_all = st.checkbox("Show all links (including expired/invalid)", value=False)
            display_df = df if show_all else valid_df
            
            # Display results in a DataFrame
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
            csv = valid_df.to_csv(index=False)
            st.download_button(
                "Download Active Groups",
                csv,
                "active_groups.csv",
                "text/csv"
            )
    else:
        st.info("Please upload a file or enter links to validate.")

if __name__ == "__main__":
    main()
