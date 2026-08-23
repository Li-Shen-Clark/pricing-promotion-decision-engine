"""Streamlit entrypoint with explicit navigation.

The page files live in ``views/`` instead of Streamlit's reserved ``pages/``
folder so Streamlit Cloud does not auto-scan page filenames before the app can
register stable titles and URL paths.
"""
from __future__ import annotations

import streamlit as st


st.set_page_config(
    page_title='Pricing & Promotion Decision Engine',
    page_icon='📊',
    layout='wide',
)

page = st.navigation(
    {
        'Decision Workflow': [
            st.Page('views/0_Overview.py', title='Overview', url_path='', default=True),
            st.Page('views/3_Optimize.py', title='Cockpit', url_path='cockpit'),
            st.Page('views/2_Simulate.py', title='Simulator', url_path='simulator'),
            st.Page('views/4_Validate.py', title='Validation', url_path='validation'),
            st.Page('views/6_Upload.py', title='Upload Sandbox', url_path='upload'),
        ],
        'Research Notes': [
            st.Page('views/0_Product_Brief.py', title='Product Brief', url_path='brief'),
            st.Page('views/1_Evidence.py', title='Model Evidence', url_path='evidence'),
            st.Page('views/5_Boundaries.py', title='Trust & Boundaries', url_path='boundaries'),
        ],
    },
    position='hidden',
)
page.run()
