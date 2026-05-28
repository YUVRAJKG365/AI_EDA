
import streamlit as st


st.set_page_config(
    page_title="EDA App",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)


import gc
import time
import os
import pandas as pd
import numpy as np

# Authentication
from security_auth import authenticate, show_user_profile_card, show_admin_dashboard

# Import utilities for isolated session state management
from utils.session_state_manager import get_session_manager
from utils.memory_manager import MemoryManager

# Get session manager instance
session_manager = get_session_manager()

# Define a global rainbow color palette with more vibrant colors
RAINBOW_COLORS = [
    "#FF355E", "#FD5B78", "#FF6037", "#FF9966",
    "#FF9933", "#FFCC33", "#FFFF66", "#CCFF00",
    "#66FF66", "#50BFE6", "#FF6EFF", "#EE34D2"
]


# Initialize session state with comprehensive defaults
def initialize_session_state():
    """Initialize all global session state variables with proper defaults"""
    defaults = {
        'x_col': None,
        'y_col': None,
        'plot_type': "Scatter Plot",
        'pred_x_col': None,
        'pred_y_col': None,
        'pred_plot_type': "Line Plot",
        'is_structured': True,
        'current_section': "Home",
        'last_section': None,
        'transition_start': False,
        'df': None,
        'cleaned_df': None,
        'text_data': None,
        'pdf_text': None,
        'performance_mode': False,
        'uploaded_file_name': None,
        'uploaded_file': None,
        'file_uploader_key': 0,  # Used to force reset the file uploader
        'chat_history': [],
        'selected_section': "Home",
        'file_processed': False,
        'image_data': None,
        'pdf_images': None,
        'tab_states': {},
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


initialize_session_state()

if 'tracker' not in st.session_state:
    from tracker import AppTracker
    st.session_state.tracker = AppTracker()
tracker = st.session_state.tracker

# Authentication gating
if not authenticate():
    st.stop()


# Add custom CSS for header only - optimized for memory efficiency
st.markdown(
    """
    <style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&family=Montserrat:wght@400;600;700&display=swap');

    /* Header Box with Rainbow Gradient - Professional Data Analysis Style */
    .header-box {
        background: linear-gradient(90deg, 
            #FF6B6B 0%,      /* Vibrant Red */
            #FF8C42 15%,     /* Orange */
            #FFD93D 30%,     /* Golden Yellow */
            #6BCB77 45%,     /* Fresh Green */
            #4D96FF 60%,     /* Sky Blue */
            #6C5CE7 75%,     /* Purple */
            #A29BFE 90%,     /* Lavender */
            #FF6B6B 100%     /* Back to Red */
        );
        background-size: 100% 100%;
        color: white;
        padding: 30px 25px;
        text-align: center;
        font-size: 2rem;
        font-weight: 700;
        border-radius: 15px;
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.15);
        margin-bottom: 25px;
        font-family: 'Montserrat', sans-serif;
        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.25);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }

    .header-box:hover {
        transform: translateY(-5px);
        box-shadow: 0 15px 35px rgba(0, 0, 0, 0.2);
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Header with improved design
st.markdown(
    """
    <div class="header-box">
        <div style="font-size: 1.2rem; margin-bottom: 5px; font-weight: 400;">✨ AI Powered EDA </div>
        <div style="font-size: 1.5rem;">Advanced Data Analysis Tool</div>
        <div style="font-size: 0.9rem; margin-top: 10px; font-weight: 300;">By <span style="color: #FFD700; font-weight: 600;">YUVRAJ KUMAR GOND</span></div>
    </div>
    """,
    unsafe_allow_html=True
)
# Performance optimization toggle
with st.sidebar.expander("🚀 Performance Mode"):
    st.session_state.performance_mode = st.toggle("Enable Performance Mode",
                                                  value=st.session_state.get('performance_mode', False))
    if st.session_state.performance_mode:
        st.info("Performance mode reduces animations for faster processing.")
with st.sidebar.expander("🔄 Refresh"):
    if st.button("Refresh", help="Refresh the entire application and clear session state"):
        session_manager.clear_all_data()  # Clear section-specific data
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

    if st.button("🧹 Clear All Data", help="Remove all uploaded files and reset the app"):
        # Clear all section data
        session_manager.clear_all_data()

        # Clear Streamlit cache
        st.cache_data.clear()
        st.cache_resource.clear()

        # Run garbage collection
        gc.collect()
        st.rerun()

    # Display memory usage information
    MemoryManager.display_memory_usage()

show_user_profile_card()

# Sidebar Navigation with improved design
st.sidebar.markdown("---")
st.sidebar.markdown(
    """
    <style>
    .sidebar-header {
        font-size: 1.5rem;
        font-weight: 600;
        color: #6B5B95;
        margin-bottom: 1px;
        text-align: center;
    }
    </style>
    <div class="sidebar-header">Navigation</div>
    """,
    unsafe_allow_html=True
)
st.sidebar.markdown("---")

# Define the sections with icons (limited set for this fixed version)
sections = [
    {"name": "Home", "icon": "🏠"},
    {"name": "Data Cleaning", "icon": "🧹"},
    {"name": "Visualizations", "icon": "📈"},
    {"name": "Chatbot", "icon": "💬"},
    {"name": "Machine Learning", "icon": "🤖"},
    {"name": "NLP Analysis", "icon": "📝"},
    {"name": "Time Series Analysis", "icon": "⏰"},
    {"name": "SQL Querying", "icon": "🗄️"},
    {"name": "Image Analysis", "icon": "🖼️"},
    {"name": "OCR Processing", "icon": "🔍"}
]

# Create navigation buttons with icons
for section in sections:
    if st.sidebar.button(f"{section['icon']} {section['name']}", key=f"nav_{section['name']}", use_container_width=True):
        st.session_state.last_section = st.session_state.selected_section
        st.session_state.selected_section = section["name"]
        st.session_state.transition_start = True

# Admin-only dashboard link separated by divider
if st.session_state.get('is_admin'):
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Admin Panel")
    if st.sidebar.button("👑 Admin Dashboard", key="nav_admin_dashboard_sidebar", use_container_width=True):
        st.session_state.last_section = st.session_state.selected_section
        st.session_state.selected_section = "Admin Dashboard"
        st.session_state.transition_start = True

# Add a footer to the sidebar
st.sidebar.markdown("---")
st.sidebar.markdown(
    """
    <div style="text-align: center; font-size: 0.9rem; color: #6c757d;">
        <p><strong>Advanced EDA Tool</strong></p>
        <p>Version: <b>3.0</b></p>
        <p>By</p>
        <p><b>YKG365</b></p>
        <p>© 2026 All Rights Reserved</p>
    </div>
    """,
    unsafe_allow_html=True
)

# Display the selected section with transition effect
section_container = st.container()

with section_container:
    if st.session_state.get('transition_start', False):
        st.markdown('<div class="new-section">', unsafe_allow_html=True)

    # Home Section
    if 'selected_section' in st.session_state and st.session_state.selected_section == "Home":
        tracker.log_section("Home")
        with st.container():
            from data_loading import home_ui
            home_ui()

    # Data Cleaning Section
    if 'selected_section' in st.session_state and st.session_state.selected_section == "Data Cleaning":
        tracker.log_section("Data Cleaning")
        with st.container():
            from data_cleaning import render_data_cleaning_section
            render_data_cleaning_section()

    # Visualizations Section
    if 'selected_section' in st.session_state and st.session_state.selected_section == "Visualizations":
        tracker.log_section("Visualizations")
        with st.container():
            if 'df' in st.session_state:
                df = st.session_state.df
                from visualizations import render_visualizations_section
                render_visualizations_section(df)
            else:
                st.info("Please upload and load a dataset first to use visualization features.")

    # Chatbot Section
    if 'selected_section' in st.session_state and st.session_state.selected_section == "Chatbot":
        with st.container():
            from chatbot import chatbot_ui
            chatbot_ui()

    if 'selected_section' in st.session_state and st.session_state.selected_section == "Machine Learning":
        with st.container():
            from ml_integration import render_ml_section
            render_ml_section()

    if 'selected_section' in st.session_state and st.session_state.selected_section == "NLP Analysis":
        with st.container():
            from nlp import render_nlp_section
            render_nlp_section()

    if 'selected_section' in st.session_state and st.session_state.selected_section == "Time Series Analysis":
        with st.container():
            from time_series import render_time_series_section
            render_time_series_section()

    if 'selected_section' in st.session_state and st.session_state.selected_section == "SQL Querying":
        with st.container():
            from sql import sqlq_ui
            sqlq_ui()

    if 'selected_section' in st.session_state and st.session_state.selected_section == "Image Analysis":
        with st.container():
            from image_analysis import render_image_analysis_section
            render_image_analysis_section()

    if 'selected_section' in st.session_state and st.session_state.selected_section == "OCR Processing":
        with st.container():
            from extraction import extraction_ui
            extraction_ui()

    # Admin Dashboard Section
    if 'selected_section' in st.session_state and st.session_state.selected_section == "Admin Dashboard":
        if st.session_state.get('is_admin'):
            tracker.log_section("Admin Dashboard")
            with st.container():
                show_admin_dashboard()
        else:
            st.error("Access denied: Admins only.")


