"""
PIXI complete study sheet creator
"""
import os
import streamlit as st
import pandas as pd
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

        self.init_session_state()
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
        self.init_options_sidebar()
        self.init_main_section()


    def init_options_sidebar(self):
        # Streamlit setup
        with st.sidebar:
            st.title("Complete Study Sheet Builder")
            st.markdown("*Create a complete study sheet based on PET/CT data within an XNAT project.*")
            
            with st.expander("Options", expanded=True):
                self.input_prefix = st.text_input("Experiment Prefix Filter", help='Experiment label must begin with this prefix to be included in study sheet.')

                self.filter_splits = st.checkbox("Only Include Split Data", help='Set to true if you wish to only include split experiments.')

            st.button("Create Sheet", on_click=self.extract_project_data)

    def extract_element_from_json_if_present(self, input_json, element_name):
        if element_name in input_json:
            return input_json[element_name]
        else:
            return ''

    def init_main_section(self):
        self.main = st.container()

        with self.main:
            st.write("Please set your optional parameters then click 'Create Sheet.'")
    
    def download_experiment_data_as_json(self, experiment_id):
        url = f"/data/experiments/{experiment_id}?format=json"
        
        try:
            response = self._connection.get(url)
            data = response.json()
            if 'items' in data:
                data_items = data['items'][0]
                response.raise_for_status()
                return data_items
            
        except requests.exceptions.RequestException as e:
            with self.main:
                st.write(f"Error downloading XML for {experiment_id}: {e}")
            return None

    def parse_pet_ct_data(self, experiment_json, experiment_id, experiment_filter, remove_splits):
        study_sheet_info = []
        
        try:
            data_fields = experiment_json['data_fields']
            study_name = data_fields['label']

            if experiment_filter and experiment_filter not in study_name:
                return []
            if remove_splits and 'split' not in study_name.lower():
                return []

            study_date = self.extract_element_from_json_if_present(data_fields, 'date')
            tracer_name = self.extract_element_from_json_if_present(data_fields, 'tracer/name')
            animal_weight = self.extract_element_from_json_if_present(data_fields, 'dcmPatientWeight')
            tracer_dose = self.extract_element_from_json_if_present(data_fields, 'tracer/dose')
            tracer_units = self.extract_element_from_json_if_present(data_fields, 'tracer/dose/units')
            injection_time = self.extract_element_from_json_if_present(data_fields, 'tracer/startTime')
            scanner_model = self.extract_element_from_json_if_present(data_fields, 'scanner/model')
            
            scans = experiment_json['children'][0]['items']

            for scan in scans:
                scan_data_fields = scan['data_fields']

                if 'modality' not in scan_data_fields:
                    continue
                
                modality = scan_data_fields['modality'].lower()
                if modality != 'pt' and modality != 'pet' and modality != 'ct':
                    continue

                if 'type' not in scan_data_fields:
                    continue
                scan_name = scan_data_fields['type']

                scan_time = self.extract_element_from_json_if_present(scan_data_fields, 'startTime')

                scan_info = {
                    'Study Name': study_name,
                    'Scan Name': scan_name,
                    'Modality': modality,
                    'Animal Weight': animal_weight,
                    'Tracer': tracer_name,
                    'Activity': '{} {}'.format(tracer_dose, tracer_units),
                    'Study Date': study_date,
                    'Scan Time': scan_time,
                    'Injection Time': injection_time,
                    'Scanner': scanner_model
                }
                study_sheet_info.append(scan_info)
                        
        except Exception as e:
            with self.main:
                st.write(f"Unexpected error processing {experiment_id}: {e}")
        
        return study_sheet_info

    def extract_project_data(self):
        experiment_filter = self.input_prefix
        remove_splits = self.filter_splits
        experiments = self._project.experiments.values()
        
        if not experiments:
            with self.main:
                st.write(f"No experiments found. Exiting.")
            return
        
        all_scan_data = []
        
        for i, experiment in enumerate(experiments, 1):
            exp_id = experiment.id
            experiment_json = self.download_experiment_data_as_json(exp_id)
            if experiment_json:
                scan_data = self.parse_pet_ct_data(experiment_json, exp_id, experiment_filter, remove_splits)
                all_scan_data.extend(scan_data)
        
        if all_scan_data:
            self.main = st.empty()
            df = pd.DataFrame.from_dict(all_scan_data)
            st.dataframe(df, height=600)            
        else:
            with self.main:
                st.write(f"No PET/CT scan data found in project")

app = App()