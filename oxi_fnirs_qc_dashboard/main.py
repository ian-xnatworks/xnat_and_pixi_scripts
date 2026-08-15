"""
Jupyter dashboard to create a outline of fNIRS Scan QC data within a project
"""
import os
import streamlit as st
import pandas as pd
import xnat
import requests
import csv
import argparse
import json
from datetime import datetime

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