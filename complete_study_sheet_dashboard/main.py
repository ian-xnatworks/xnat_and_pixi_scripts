"""
PIXI complete study sheet creator
"""
import os
import streamlit as st
import xnat
import requests
import csv
import argparse
import json

css='''
<style>
    section.main > div {max-width: 80%;}
</style>
'''
st.markdown(css, unsafe_allow_html=True)

class App:

    def __init__(self, host=None, user=None, password=None, project_id=None):
        self._host = host or os.environ.get('XNAT_HOST')
        self._user = user or os.environ.get('XNAT_USER')
        self._password = password or os.environ.get('XNAT_PASS')
        self._project_id = project_id or (os.environ.get('XNAT_ITEM_ID') if os.environ.get('XNAT_XSI_TYPE') == 'xnat:projectData' else None)
        self._connection = xnat.connect(self._host, user=self._user, password=self._password)

        if self._project_id:
            try: 
                self._project = self._connection.projects[self._project_id]
            except Exception as e:
                raise Exception(f'Error connecting to project {self._project_id}', e)
        else:
            raise Exception('Must be started from an XNAT project.')

        self._init_session_state()
        self.init_ui()

    def init_session_state(self):
        # Initialize streamlit session state
        # Values will be populated later
        if 'project' not in st.session_state:
            st.session_state.project = self._project

        if 'project_id' not in st.session_state:
            st.session_state.project_id = self._project_id

        if 'experiments' not in st.session_state:
            st.session_state.experiments = []

    def init_ui(self):
        # Hide streamlit deploy button
        st.markdown("""
            <style>
                .reportview-container {
                    margin-top: -2em;
                }
                #MainMenu {visibility: hidden;}
                .stDeployButton {display:none;}
                footer {visibility: hidden;}
                #stDecoration {display:none;}
            </style>
        """, unsafe_allow_html=True)

        # Initialize UI
        self._init_sidebar()


    def init_options_sidebar(self):
        # Streamlit setup
        with st.sidebar:
            st.title("Complete Study Sheet Builder")
            st.markdown("*Create a complete study sheet based on PET/CT data within XNAT.*")
            
            with st.expander("Options", expanded=True):
                self.input_prefix = st.multiselect("Experiment Prefix Filter", help='Experiment label must begin with this prefix to be included in study sheet.')

                self.filter_splits = st.checkbox("Only Include Split Data", help='Set to true if you wish to only include split experiments.')


app = App()