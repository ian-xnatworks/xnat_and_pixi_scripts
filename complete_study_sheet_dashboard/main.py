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

    def init_options_sidebar(self):
        # Streamlit setup
        with st.sidebar:
            st.title("Complete Study Sheet Builder")
            st.markdown("*Create a complete study sheet based on PET/CT data within XNAT.*")
            
            with st.expander("Options", expanded=True):
                self.input_prefix = st.multiselect("Experiment Prefix Filter", help='Experiment label must begin with this prefix to be included in study sheet.')

                self.filter_splits = st.checkbox("Only Include Split Data", help='Set to true if you wish to only include split experiments.')


app = App()