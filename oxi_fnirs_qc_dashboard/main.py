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

    def init_session_state(self):
        # Initialize streamlit session state
        # Values will be populated later
        if 'project' not in st.session_state:
            st.session_state.project = self._project

        if 'project_id' not in st.session_state:
            st.session_state.project_id = self._project_id

        if 'experiments' not in st.session_state:
            st.session_state.experiments = []

        if 'scans' not in st.session_state:
            st.session_state.scans = []

        if 'qc_elements' not in st.session_state:
            st.session_state.qc_elements = []

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

def clean_scan_name_for_scan_type(scan_name):
    non_letters_removed = re.sub(r'[^\w]|[\d_]', '', scan_name)
    scan_substring_removed = re.sub(r'scan', '', non_letters_removed, flags=re.IGNORECASE)
    return scan_substring_removed

def create_assessment_json(scan_json, assessment_type, data_fields_element, rater, datetime):
    assessment_json = {}
    assessment_json['rater'] = rater
    assessment_json['date'] = datetime

    if assessment_type not in data_fields_element:
        return
    assessment_json['score'] = data_fields_element[assessment_type]

    if assessment_type in scan_json['assessments']:
        scan_json['assessments'][assessment_type].append(assessment_json)
    else:
        scan_json['assessments'][assessment_type] = [assessment_json]

def create_full_structure_json(project):
    subjects = project.subjects.values()

    subject_json_list = []

    for subject in subjects:
        subject_has_fnirs_qc_data = False
        subject_json = {}
        subject_json['id'] = subject.id
        subject_json['label'] = subject.label
        subject_experiment_jsons = []

        experiments = subject.experiments.values()

        for experiment in experiments:
            if experiment.__xsi_type__ == 'fnirs:fnirsSessionData':
                experiment_json = {}
                experiment_json['id'] = experiment.id
                experiment_json['label'] = experiment.label

                scan_id_to_scan_json_dict = {}
                for scan in experiment.scans.values():
                    if scan.__xsi_type__ == 'fnirs:fnirsScanData':
                        scan_json = {}
                        scan_json['id'] = scan.id
                        scan_json['type'] = clean_scan_name_for_scan_type(scan.id)
                        scan_json['assessments'] = {}
                        scan_id_to_scan_json_dict[scan.id] = scan_json

                for assessor in experiment.assessors.values():
                    scan_assessors = assessor.fulldata['children'][0]['items']
                    for scan_assessor in scan_assessors:
                        if scan_assessor['meta']['xsi:type'] != 'fnirs:fnirsQcScanData':
                            continue

                        subject_has_fnirs_qc_data = True
                        data_fields = scan_assessor['data_fields']
                        scan_json = scan_id_to_scan_json_dict[data_fields['imageScan_ID']]
                        
                        lightFalloff_assessment_json = create_assessment_json(scan_json, 'lightFalloff', data_fields, assessor.rater, scan_assessor['meta']['start_date'])
                        pulseSnr_assessment_json = create_assessment_json(scan_json, 'pulseSnr', data_fields, assessor.rater, scan_assessor['meta']['start_date'])
                        pulsatility_assessment_json = create_assessment_json(scan_json, 'pulsatility', data_fields, assessor.rater, scan_assessor['meta']['start_date'])
                        motion_assessment_json = create_assessment_json(scan_json, 'motion', data_fields, assessor.rater, scan_assessor['meta']['start_date'])
                        mapQuality_assessment_json = create_assessment_json(scan_json, 'mapQuality', data_fields, assessor.rater, scan_assessor['meta']['start_date'])
                
                experiment_json['scans'] = list(scan_id_to_scan_json_dict.values())
                subject_experiment_jsons.append(experiment_json)
        if subject_has_fnirs_qc_data:
            subject_json['sessions'] = subject_experiment_jsons
            subject_json_list.append(subject_json)

app = App()