import streamlit as st
import re
import pandas as pd
from urllib.parse import urlparse
from typing import List, Dict, Tuple
import matplotlib.pyplot as plt
import io
from PIL import Image
import base64


def tab_manager(tab_labels: list, section_name: str):
    """Improved tab manager with better state persistence"""
    # Initialize tab state for this section
    if section_name not in st.session_state.tab_states:
        st.session_state.tab_states[section_name] = 0

    # Create tabs
    tabs = st.tabs(tab_labels)

    # Track active tab without using buttons
    active_index = st.session_state.tab_states[section_name]

    # Update session state if tabs are clicked
    if 'tab_clicked' in st.session_state and st.session_state.tab_clicked:
        st.session_state.tab_states[section_name] = st.session_state.tab_clicked
        st.session_state.tab_clicked = None
        st.rerun()

    return active_index, tabs


def extract_links(text: str) -> Dict[str, list]:
    """
    Extract URLs, emails, and phone numbers from text.
    Supports all types of URL detection including embedded URLs.

    Args:
        text: Input text to extract from

    Returns:
        Dictionary containing lists of URLs, emails, and phone numbers
    """
    if not text:
        return {
            "urls": [],
            "emails": [],
            "phone_numbers": []
        }

    result = {
        "urls": [],
        "emails": [],
        "phone_numbers": []
    }

    # ===== URLS - COMPREHENSIVE DETECTION =====
    # Pattern 1: HTTP/HTTPS URLs (most common)
    http_pattern = r'https?://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&/=]*)'

    # Pattern 2: FTP URLs
    ftp_pattern = r'ftp://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&/=]*)'

    # Pattern 3: WWW URLs (without protocol)
    www_pattern = r'www\.[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&/=]*)'

    # Pattern 4: Embedded URLs or markdown links [text](url)
    markdown_pattern = r'\[([^\]]+)\]\(([^)]+)\)'

    # Pattern 5: URLs in text format like "visit example.com"
    domain_pattern = r'(?:(?:https?|ftp):\/\/)?(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{2,256}\.[a-zA-Z]{2,6}(?:\/[-a-zA-Z0-9()@:%_\+.~#?&/=]*)?'

    # Collect all URLs
    all_urls = []

    # Find HTTP/HTTPS URLs
    all_urls.extend(re.findall(http_pattern, text))

    # Find FTP URLs
    all_urls.extend(re.findall(ftp_pattern, text))

    # Find WWW URLs
    all_urls.extend(re.findall(www_pattern, text))

    # Find markdown links - extract the URL part
    markdown_links = re.findall(markdown_pattern, text)
    for _, url in markdown_links:
        if url not in all_urls:
            all_urls.append(url)

    # Find domain pattern URLs
    domain_urls = re.findall(domain_pattern, text)
    for url in domain_urls:
        if url and url not in all_urls:
            all_urls.append(url)

    # Clean up URLs by removing trailing punctuation
    all_urls = [url.rstrip('.,;:!?)"\'}') for url in all_urls]
    # Remove duplicates while preserving order
    seen = set()
    unique_urls = []
    for url in all_urls:
        if url not in seen and len(url) > 4:  # Filter out very short strings
            seen.add(url)
            unique_urls.append(url)

    result["urls"] = unique_urls

    # ===== EMAIL ADDRESSES =====
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = re.findall(email_pattern, text)
    result["emails"] = list(set(emails))

    # ===== PHONE NUMBERS =====
    # Matches various phone formats: +1-800-555-1234, (800) 555-1234, 800-555-1234, etc.
    phone_pattern = r'(?:\+?1[-.\s]?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}|\+[0-9]{1,3}[-.\s]?[0-9]{1,14})'
    phone_numbers = re.findall(phone_pattern, text)
    result["phone_numbers"] = list(set(phone_numbers))

    return result


def display_extracted_links(text: str, section_key: str = "links"):
    """
    Display detected URLs, emails, and phone numbers in formatted manner

    Args:
        text: Text to extract contacts from
        section_key: Unique key for this display section
    """
    links_data = extract_links(text)
    urls = links_data["urls"]
    emails = links_data["emails"]
    phone_numbers = links_data["phone_numbers"]

    total_contacts = len(urls) + len(emails) + len(phone_numbers)

    if total_contacts == 0:
        st.info("ℹ️ No URLs, emails, or phone numbers found in the text")
        return

    # Display summary
    st.subheader(f"🔗 Detected URLs, Emails & Phone Numbers ({total_contacts})")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("🌐 URLs Found", len(urls))
    with col2:
        st.metric("📧 Emails Found", len(emails))
    with col3:
        st.metric("📞 Phone Numbers Found", len(phone_numbers))

    st.divider()

    # Display URLs
    if urls:
        st.markdown("### 🌐 URLs (All Types)")
        for idx, url in enumerate(urls):
            # Normalize URL for opening
            normalized_url = url
            if not normalized_url.startswith(('http://', 'https://', 'ftp://')):
                if normalized_url.startswith('www.'):
                    normalized_url = 'https://' + normalized_url
                else:
                    normalized_url = 'https://' + normalized_url

            col1, col2, col3 = st.columns([2.5, 1, 1])

            with col1:
                st.markdown(f"**{idx + 1}.** `{url}`")

            with col2:
                if st.button("🔗 Open", key=f"{section_key}_url_open_{idx}"):
                    st.markdown(f"[Open Link →]({normalized_url})")

            with col3:
                if st.button("📋 Copy", key=f"{section_key}_url_copy_{idx}"):
                    st.info(f"Copied: {url}")

        st.divider()

    # Display Emails
    if emails:
        st.markdown("### 📧 Email Addresses")
        for idx, email in enumerate(emails):
            col1, col2 = st.columns([3, 1])

            with col1:
                st.markdown(f"**{idx + 1}.** `{email}`")

            with col2:
                if st.button("📋 Copy", key=f"{section_key}_email_copy_{idx}"):
                    st.info(f"Copied: {email}")

        st.divider()

    # Display Phone Numbers
    if phone_numbers:
        st.markdown("### 📞 Phone Numbers")
        for idx, phone in enumerate(phone_numbers):
            col1, col2 = st.columns([3, 1])

            with col1:
                st.markdown(f"**{idx + 1}.** `{phone}`")

            with col2:
                if st.button("📋 Copy", key=f"{section_key}_phone_copy_{idx}"):
                    st.info(f"Copied: {phone}")

    # Export section
    st.divider()
    st.markdown("### 💾 Export All Contacts")

    export_col1, export_col2 = st.columns(2)

    with export_col1:
        # Export as TXT
        export_text = "EXTRACTED URLs, EMAILS & PHONE NUMBERS\n" + "=" * 60 + "\n\n"

        if urls:
            export_text += f"URLS ({len(urls)})\n" + "-" * 40 + "\n"
            export_text += "\n".join([f"• {url}" for url in urls]) + "\n\n"

        if emails:
            export_text += f"EMAIL ADDRESSES ({len(emails)})\n" + "-" * 40 + "\n"
            export_text += "\n".join([f"• {email}" for email in emails]) + "\n\n"

        if phone_numbers:
            export_text += f"PHONE NUMBERS ({len(phone_numbers)})\n" + "-" * 40 + "\n"
            export_text += "\n".join([f"• {phone}" for phone in phone_numbers])

        st.download_button(
            label="⬇️ Download as TXT",
            data=export_text,
            file_name=f"extracted_contacts_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain",
            key=f"{section_key}_export_txt"
        )

    with export_col2:
        # Export as CSV
        import csv
        from io import StringIO

        csv_buffer = StringIO()
        writer = csv.writer(csv_buffer)
        writer.writerow(["Type", "Value"])

        for url in urls:
            writer.writerow(["URL", url])
        for email in emails:
            writer.writerow(["EMAIL", email])
        for phone in phone_numbers:
            writer.writerow(["PHONE", phone])

        csv_data = csv_buffer.getvalue()

        st.download_button(
            label="⬇️ Download as CSV",
            data=csv_data,
            file_name=f"extracted_contacts_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            key=f"{section_key}_export_csv"
        )


# ============================================================================
# GRAPH VISUALIZATION EXPORT FUNCTIONS
# ============================================================================

def create_download_buttons_plotly(fig, chart_title: str, section_key: str):
    """
    Create download buttons for Plotly figures in PDF, HTML, and PNG formats

    Args:
        fig: Plotly figure object
        chart_title: Title of the chart for filename
        section_key: Unique key for button identifiers
    """
    col1, col2, col3 = st.columns(3)

    timestamp = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
    safe_title = chart_title.replace(" ", "_").replace("/", "_").lower()[:30]

    with col1:
        # HTML Download
        try:
            html_data = fig.to_html()
            st.download_button(
                label="📄 Download HTML",
                data=html_data,
                file_name=f"{safe_title}_{timestamp}.html",
                mime="text/html",
                key=f"{section_key}_html"
            )
        except Exception as e:
            st.error(f"HTML export failed: {str(e)}")

    with col2:
        # PNG Download
        try:
            img_data = fig.to_image(format='png')
            st.download_button(
                label="🖼️ Download PNG",
                data=img_data,
                file_name=f"{safe_title}_{timestamp}.png",
                mime="image/png",
                key=f"{section_key}_png"
            )
        except Exception:
            st.warning("PNG export unavailable (kaleido not installed)")

    with col3:
        # PDF Download
        try:
            pdf_data = fig.to_image(format='pdf')
            st.download_button(
                label="📕 Download PDF",
                data=pdf_data,
                file_name=f"{safe_title}_{timestamp}.pdf",
                mime="application/pdf",
                key=f"{section_key}_pdf"
            )
        except Exception:
            st.warning("PDF export unavailable (kaleido not installed)")


def create_download_buttons_matplotlib(fig, chart_title: str, section_key: str):
    """
    Create download buttons for Matplotlib figures in PNG, PDF, and SVG formats

    Args:
        fig: Matplotlib figure object
        chart_title: Title of the chart for filename
        section_key: Unique key for button identifiers
    """
    col1, col2, col3 = st.columns(3)

    timestamp = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
    safe_title = chart_title.replace(" ", "_").replace("/", "_").lower()[:30]

    with col1:
        # PNG Download
        try:
            buf_png = io.BytesIO()
            fig.savefig(buf_png, format='png', bbox_inches='tight', dpi=150)
            buf_png.seek(0)
            st.download_button(
                label="🖼️ Download PNG",
                data=buf_png,
                file_name=f"{safe_title}_{timestamp}.png",
                mime="image/png",
                key=f"{section_key}_png"
            )
        except Exception as e:
            st.error(f"PNG export failed: {str(e)}")

    with col2:
        # PDF Download
        try:
            buf_pdf = io.BytesIO()
            fig.savefig(buf_pdf, format='pdf', bbox_inches='tight')
            buf_pdf.seek(0)
            st.download_button(
                label="📕 Download PDF",
                data=buf_pdf,
                file_name=f"{safe_title}_{timestamp}.pdf",
                mime="application/pdf",
                key=f"{section_key}_pdf"
            )
        except Exception as e:
            st.error(f"PDF export failed: {str(e)}")

    with col3:
        # SVG Download
        try:
            buf_svg = io.BytesIO()
            fig.savefig(buf_svg, format='svg', bbox_inches='tight')
            buf_svg.seek(0)
            st.download_button(
                label="📊 Download SVG",
                data=buf_svg,
                file_name=f"{safe_title}_{timestamp}.svg",
                mime="image/svg+xml",
                key=f"{section_key}_svg"
            )
        except Exception as e:
            st.error(f"SVG export failed: {str(e)}")


def display_chart_with_expander(fig, title: str, section_key: str,
                                chart_type: str = "plotly", expanded: bool = True):
    """
    Display a chart inside an expander with download buttons

    Args:
        fig: Chart figure (Plotly or Matplotlib)
        title: Title of the chart
        section_key: Unique key for identifiers
        chart_type: "plotly" or "matplotlib"
        expanded: Whether expander is initially expanded
    """
    with st.expander(f"📊 {title}", expanded=expanded):
        # Display the chart
        if chart_type.lower() == "plotly":
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.pyplot(fig, use_container_width=True)

        st.markdown("**Download Chart:**")

        # Show download buttons
        if chart_type.lower() == "plotly":
            create_download_buttons_plotly(fig, title, section_key)
        else:
            create_download_buttons_matplotlib(fig, title, section_key)


def display_multiple_charts(charts_list: list, section_key: str, expanded: bool = False):
    """
    Display multiple charts, each in its own expander with download buttons

    Args:
        charts_list: List of tuples (fig, title, chart_type)
                    where chart_type is "plotly" or "matplotlib"
        section_key: Base key for identifiers
        expanded: Whether expanders are initially expanded
    """
    for idx, (fig, title, chart_type) in enumerate(charts_list):
        unique_key = f"{section_key}_{idx}"
        display_chart_with_expander(fig, title, unique_key, chart_type, expanded)