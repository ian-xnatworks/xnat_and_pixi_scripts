"""
Jupyter dashboard to create a outline of fNIRS Scan QC data within a project
"""
import os
import re
import streamlit as st
import pandas as pd
import xnat
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

    def __init__(self, host=None, user=None, password=None, project_id=None, subject_id=None, experiment_id=None):
        self.host = host or os.environ.get('XNAT_HOST')
        self.user = user or os.environ.get('XNAT_USER')
        self.password = password or os.environ.get('XNAT_PASS')
        self.project_id = project_id or (os.environ.get('XNAT_ITEM_ID') if os.environ.get('XNAT_XSI_TYPE') == 'xnat:projectData' else None)
        self.subject_id = subject_id or (os.environ.get('XNAT_ITEM_ID') if os.environ.get('XNAT_XSI_TYPE') == 'xnat:subjectData' else None)
        self.experiment_id = experiment_id or (os.environ.get('XNAT_ITEM_ID') if os.environ.get('XNAT_XSI_TYPE') == 'xnat:experimentData' else None)
        self.connection = xnat.connect(self.host, user=self.user, password=self.password)

        self.base_element_type = ''
        if self.project_id:
            try: 
                self.project = self.connection.projects[self.project_id]
                self.base_element_type = 'project'
            except Exception as e:
                raise Exception(f'Error connecting to project {self.project_id}', e)
        if self.subject_id:
            try: 
                self.subject = self.connection.subjects[self.subject_id]
                self.base_element_type = 'subject'
            except Exception as e:
                raise Exception(f'Error connecting to subject {self.subject_id}', e)
        if self.experiment_id:
            try: 
                self.experiment = self.connection.experiments[self.experiment_id]
                self.base_element_type = 'experiment'
            except Exception as e:
                raise Exception(f'Error connecting to subject {self.experiment_id}', e)

        if not self.base_element_type:
            raise Exception("Unable to locate base element for Jupyter Dashboard.")

        self.json_outline = self.create_full_structure_json()
        self.init_session_state()
        self.init_ui()

    def init_session_state(self):
        # Initialize streamlit session state
        # Values will be populated later
        if 'subject_labels' not in st.session_state:
            st.session_state.subject_labels = []

        if 'experiment_labels' not in st.session_state:
            st.session_state.experiment_labels = []

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
        self.init_options_sidebar()
        self.init_main_section()

    def set_limit_to_subjects(self):
        st.session_state.subject_filter_on = not st.session_state.limit_to_subjects

    def set_limit_to_experiments(self):
        st.session_state.experiment_filter_on = not st.session_state.limit_to_experiments

    def enable_disable_datetime_filter(self):
        st.session_state.datetimes_disabled = not st.session_state.filter_date

    def init_options_sidebar(self):
        # Streamlit setup
        with st.sidebar:
            st.title("fNIRS QC Assessment Report Creator")
            st.markdown("*Create a report outlining the information found in the QC Assessments for fNIRS scans within the project.*")
            
            with st.expander("Options", expanded=True):
                if self.base_element_type == 'project':
                    st.checkbox("Limit to Subjects", help='Set to true if you wish to limit the output to certain subjects.', key= 'limit_to_subjects', on_change=self.set_limit_to_subjects)
                    st.multiselect("Filter Subjects", st.session_state.subject_labels, default=[], help='Set which subjects will be used to make the output.',key='filter_subjects', disabled=st.session_state.get("subject_filter_on", True))

                if self.base_element_type == 'project' or self.base_element_type == 'subject':
                    st.checkbox("Limit to Experiments", help='Set to true if you wish to limit the output to certain experiments.', key= 'limit_to_experiments', on_change=self.set_limit_to_experiments)
                    st.multiselect("Filter Experiments", st.session_state.experiment_labels, default=[], help='Set which experiments will be used to make the output.',key='filter_experiments', disabled=st.session_state.get("experiment_filter_on", True))

                st.multiselect("Filter Assessment Type", ['lightFalloff', 'pulseSnr', 'pulsatility', 'motion', 'mapQuality'], default=[], help='Choose to only include certain assessment types in the report.',key='filter_assessment_type')

                st.checkbox("Filter Date", help='Set to true if you wish to filter assessments based on their date.', key= 'filter_date', on_change=self.enable_disable_datetime_filter)
                st.date_input("Date range start", datetime.today(), help='Beginning of date range to filter assessments.', key='assessment_date_range_start', disabled=st.session_state.get("datetimes_disabled", True))
                st.date_input("Date range end", datetime.today(), help='End of date range to filter assessments.', key='assessment_date_range_end', disabled=st.session_state.get("datetimes_disabled", True))
                
            st.button("Create Report", on_click=self.create_table)

    def init_main_section(self):
        self.main = st.container()

    def create_table(self):
        json_outline = self.json_outline
        csv_elements = self.convert_json_into_csv(json_outline)

        if csv_elements:
            df = pd.DataFrame.from_dict(csv_elements)
            st.dataframe(df, height=600, hide_index=True)            
        else:
            if st.session_state.limit_to_subjects or st.session_state.limit_to_experiments or st.session_state.filter_date or st.session_state.filter_assessment_type:
                 with self.main:
                    st.write(f"No fNIRS data found in the project that conforms to the input options.")
            else:
                with self.main:
                    st.write(f"No fNIRS data found within the project.")

    def create_full_structure_json(self):
        if self.base_element_type == 'project':
            subjects = self.project.subjects.values()
            subject_json_list = []

            for subject in subjects:
                subject_json = self.create_subject_sctructure(subject)
                if subject_json != None:
                    subject_json_list.append(subject_json)

            return subject_json_list
        elif self.base_element_type == 'subject':
            subject_json = self.create_subject_sctructure(self.subject)
            if subject_json != None:
                return [subject_json]
        elif self.base_element_type == 'experiment':
            experiment_json = self.create_experiment_structure(self.experiment)
            if experiment_json != None:
                return experiment_json

    def create_subject_sctructure(self, subject):
        subject_has_fnirs_qc_data = False
        subject_json = {}
        subject_json['id'] = subject.id
        subject_json['label'] = subject.label
        subject_experiment_jsons = []

        experiments = subject.experiments.values()

        for experiment in experiments:
            experiment_json = self.create_experiment_structure(experiment)
            if experiment_json != None:
                if subject.label not in st.session_state.subject_labels:
                    st.session_state.subject_labels.append(subject.label)
                subject_has_fnirs_qc_data = True
                subject_experiment_jsons.append(experiment_json)

        if subject_has_fnirs_qc_data:
            subject_json['sessions'] = subject_experiment_jsons
            return subject_json
        return None

    def create_experiment_structure(self, experiment):
        if experiment.__xsi_type__ == 'fnirs:fnirsSessionData':
            experiment_has_fnirs_qc_data = False
            experiment_json = {}
            experiment_json['id'] = experiment.id
            experiment_json['label'] = experiment.label

            scan_id_to_scan_json_dict = {}
            for scan in experiment.scans.values():
                if scan.__xsi_type__ == 'fnirs:fnirsScanData':
                    scan_json = {}
                    scan_json['id'] = scan.id
                    scan_json['type'] = clean_scan_name_for_scan_type(scan.id)
                    scan_json['assessments'] = []
                    scan_id_to_scan_json_dict[scan.id] = scan_json

            for assessor in experiment.assessors.values():
                scan_assessors = assessor.fulldata['children'][0]['items']
                for scan_assessor in scan_assessors:
                    if scan_assessor['meta']['xsi:type'] != 'fnirs:fnirsQcScanData':
                        continue

                    data_fields = scan_assessor['data_fields']
                    scan_json = scan_id_to_scan_json_dict[data_fields['imageScan_ID']]
                    
                    lightFalloff_assessment_json = self.create_assessment_json(scan_json, 'lightFalloff', data_fields, assessor.rater, scan_assessor['meta']['start_date'])
                    pulseSnr_assessment_json = self.create_assessment_json(scan_json, 'pulseSnr', data_fields, assessor.rater, scan_assessor['meta']['start_date'])
                    pulsatility_assessment_json = self.create_assessment_json(scan_json, 'pulsatility', data_fields, assessor.rater, scan_assessor['meta']['start_date'])
                    motion_assessment_json = self.create_assessment_json(scan_json, 'motion', data_fields, assessor.rater, scan_assessor['meta']['start_date'])
                    mapQuality_assessment_json = self.create_assessment_json(scan_json, 'mapQuality', data_fields, assessor.rater, scan_assessor['meta']['start_date'])
            
            if experiment_has_fnirs_qc_data:
                if experiment.label not in st.session_state.experiment_labels:
                        st.session_state.experiment_labels.append(experiment.label)
                experiment_json['scans'] = list(scan_id_to_scan_json_dict.values())
                return experiment_json
            else:
                return None
        return None

    def create_assessment_json(self, scan_json, assessment_type, data_fields_element, rater, datetime):
        assessment_json = {}
        assessment_json['rater'] = rater
        assessment_json['date'] = datetime
        assessment_json['type'] = assessment_type

        if assessment_type not in data_fields_element:
            return

        assessment_json['score'] = data_fields_element[assessment_type]
        scan_json['assessments'].append(assessment_json)

    def convert_json_into_csv(self, json_list):
        list_of_csv_elements = []

        if base_element_type == 'project' or base_element_type == 'experiment':
            for subject in json_list:
                if st.session_state.limit_to_subjects and subject['label'] not in st.session_state.subject_labels:
                    continue

                subject_id = subject['id']
                subject_label = subject['label']

                for experiment in subject['sessions']:
                    list_of_csv_elements.extend(self.convert_experiment_into_csv(experiment, True))
        else:
            list_of_csv_elements.extend(self.convert_experiment_into_csv(experiment, False))
        return list_of_csv_elements

    def convert_experiment_into_csv(self, experiment, include_subject_elements):
        if st.session_state.limit_to_experiments and experiment['label'] not in st.session_state.experiment_labels:
            return []

        list_of_csv_elements = []
        experiment_id = experiment['id']
        experiment_label = experiment['label']

        for scan in experiment['scans']:
            scan_id = scan['id']
            scan_type = scan['type']

            for assessment in scan['assessments']:
                rater = assessment['rater']
                assessment_date = assessment['date']
                assessment_type = assessment['type']
                score = assessment['score']

                if st.session_state.filter_date:
                    start_date = st.session_state.assessment_date_range_start
                    end_date = st.session_state.assessment_date_range_end
                    assessment_date_datetime = datetime.strptime(assessment_date, '%Y-%m-%d').date()
                    if start_date > assessment_date_datetime or end_date < assessment_date_datetime:
                        continue

                if st.session_state.filter_assessment_type and assessment_type not in st.session_state.filter_assessment_type:
                    continue

                if include_subject_elements:
                    row_info = {
                        'Subject ID': subject_id,
                        'Subject Label': subject_label,
                        'Experiment ID': experiment_id,
                        'Experiment Label': experiment_label,
                        'Scan ID': scan_id,
                        'Scan Type': scan_type,
                        'Rater': rater,
                        'Assessment Date': assessment_date,
                        'Assessment': assessment_type,
                        'Score': score
                    }
                else:
                    row_info = {
                        'Experiment ID': experiment_id,
                        'Experiment Label': experiment_label,
                        'Scan ID': scan_id,
                        'Scan Type': scan_type,
                        'Rater': rater,
                        'Assessment Date': assessment_date,
                        'Assessment': assessment_type,
                        'Score': score
                    }
                list_of_csv_elements.append(row_info)
        return list_of_csv_elements

def clean_scan_name_for_scan_type(scan_name):
        non_letters_removed = re.sub(r'[^\w]|[\d_]', '', scan_name)
        scan_substring_removed = re.sub(r'scan', '', non_letters_removed, flags=re.IGNORECASE)
        return scan_substring_removed

app = App()