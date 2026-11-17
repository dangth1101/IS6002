"""Small presentation-only helpers for the BIRD-VN Streamlit pages."""

import streamlit as st


def hide_secondary_bird_vn_pages() -> None:
    """Hide auxiliary BIRD-VN links from the sidebar without removing their pages."""
    st.markdown(
        """
        <style>
        [data-testid="stSidebarNav"] a[href*="BIRD_VN_Analysis"],
        [data-testid="stSidebarNav"] a[href*="BIRD_VN_Validation_Review"],
        [data-testid="stSidebarNav"] a[href*="BIRD_VN_Reports"] {
            display: none !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
