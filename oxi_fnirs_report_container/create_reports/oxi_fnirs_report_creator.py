import xnat
import re
import json
import warnings
import pandas as pd
import argparse
from dateutil import parser
from datetime import datetime
from dateutil.parser import UnknownTimezoneWarning

def clean_scan_name_for_scan_type(scan_name):
	non_letters_removed = re.sub(r'[^\w]|[\d_]', '', scan_name)
	scan_substring_removed = re.sub(r'scan', '', non_letters_removed, flags=re.IGNORECASE)
	return scan_substring_removed

def create_full_structure_json(base_element_type, base_element):
	if base_element_type == 'project':
		subjects = base_element.subjects.values()
		subject_json_list = []

		for subject in subjects:
			subject_json = create_subject_sctructure(subject)
			if subject_json != None:
				subject_json_list.append(subject_json)

		return subject_json_list
	elif base_element_type == 'subject':
		subject_json = create_subject_sctructure(base_element)
		if subject_json != None:
			return [subject_json]
	elif base_element_type == 'experiment':
		experiment_json = create_experiment_structure(base_element)
		if experiment_json != None:
			return experiment_json

def create_subject_sctructure(subject):
	subject_has_fnirs_qc_data = False
	subject_json = {}
	subject_json['id'] = subject.id
	subject_json['label'] = subject.label
	subject_experiment_jsons = []

	experiments = subject.experiments.values()

	for experiment in experiments:
		experiment_json = create_experiment_structure(experiment)
		if experiment_json != None:
			subject_has_fnirs_qc_data = True
			subject_experiment_jsons.append(experiment_json)

	if subject_has_fnirs_qc_data:
		subject_json['sessions'] = subject_experiment_jsons
		return subject_json
	return None

def create_experiment_structure(experiment):
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

				experiment_has_fnirs_qc_data = True
				data_fields = scan_assessor['data_fields']
				scan_json = scan_id_to_scan_json_dict[data_fields['imageScan_ID']]

				lightFalloff_assessment_json = create_assessment_json(scan_json, 'lightFalloff', data_fields, assessor.rater, scan_assessor['meta']['start_date'])
				pulseSnr_assessment_json = create_assessment_json(scan_json, 'pulseSnr', data_fields, assessor.rater, scan_assessor['meta']['start_date'])
				pulsatility_assessment_json = create_assessment_json(scan_json, 'pulsatility', data_fields, assessor.rater, scan_assessor['meta']['start_date'])
				motion_assessment_json = create_assessment_json(scan_json, 'motion', data_fields, assessor.rater, scan_assessor['meta']['start_date'])
				mapQuality_assessment_json = create_assessment_json(scan_json, 'mapQuality', data_fields, assessor.rater, scan_assessor['meta']['start_date'])

		if experiment_has_fnirs_qc_data:
			experiment_json['scans'] = list(scan_id_to_scan_json_dict.values())
			return experiment_json
		else:
			return None
	return None

def create_assessment_json(scan_json, assessment_type, data_fields_element, rater, datetime):
	assessment_json = {}
	assessment_json['rater'] = rater
	assessment_json['date'] = datetime
	assessment_json['type'] = assessment_type

	if assessment_type not in data_fields_element:
		return
	assessment_json['score'] = data_fields_element[assessment_type]

	scan_json['assessments'].append(assessment_json)

def convert_json_into_csv(json_list, base_element_type):
	list_of_csv_elements = []

	if base_element_type == 'project' or base_element_type == 'subject':
		for subject in json_list:
			subject_id = subject['id']
			subject_label = subject['label']
			for experiment in subject['sessions']:
				list_of_csv_elements.extend(convert_experiment_into_csv(experiment, True, subject_id, subject_label))
	else:
		list_of_csv_elements.extend(convert_experiment_into_csv(json_list, False, None, None))
	return list_of_csv_elements

def convert_experiment_into_csv(experiment, include_subject_elements, subject_id, subject_label):
	list_of_csv_elements = []
	experiment_id = experiment['id']
	experiment_label = experiment['label']

	for scan in experiment['scans']:
		scan_id = scan['id']
		scan_type = scan['type']

		list_of_csv_element_for_scan = []

		for assessment in scan['assessments']:
			rater = assessment['rater']
			assessment_date = assessment['date']
			assessment_type = assessment['type']
			score = assessment['score']

			overlapping_assessment = next(
				(assessment for assessment in list_of_csv_element_for_scan if assessment.get("Rater") == rater and assessment.get("Assessment") == assessment_type),
				None 
			)

			if overlapping_assessment != None:
				with warnings.catch_warnings():
					warnings.simplefilter("ignore", UnknownTimezoneWarning)
					overlapping_assessment_datetime = parser.parse(overlapping_assessment['Assessment Date'])
					new_assessment_datetime = parser.parse(assessment_date)
					if overlapping_assessment_datetime > new_assessment_datetime:
						continue
					else:
						list_of_csv_element_for_scan.remove(overlapping_assessment)

			row_info = {}
			if include_subject_elements:
				row_info['Subject ID'] = subject_id
				row_info['Subject Label'] = subject_label                  
            
			row_info['Experiment ID'] = experiment_id
			row_info['Experiment Label'] = experiment_label
			row_info['Scan ID'] = scan_id
			row_info['Scan Type'] = scan_type
			row_info['Rater'] =  rater
			row_info['Assessment Date'] = assessment_date
			row_info['Assessment'] = assessment_type
			row_info['Score'] = score
			list_of_csv_element_for_scan.append(row_info)
		list_of_csv_elements.extend(list_of_csv_element_for_scan)
	return list_of_csv_elements


argparser = argparse.ArgumentParser()
argparser.add_argument('--be', required=True, help='Base Element ID')
argparser.add_argument('--type', required=True, help='Base Element Type')
args = argparser.parse_args()

base_element_type = args.type
base_element_id = args.be

connection = xnat.connect("https://ian-jupyterhub-dash-test.dev.xnatworks.io/", user="admin", password="admin")

base_element = None
if base_element_type == 'project':
	base_element = connection.projects[base_element_id]
elif base_element_type == 'subject':
	base_element = connection.subjects[base_element_id]
elif base_element_type == 'experiment':
	base_element = connection.experiments[base_element_id]

json_list = create_full_structure_json(base_element_type, base_element)
list_of_csv_elements = convert_json_into_csv(json_list, base_element_type)

df = pd.DataFrame.from_dict(list_of_csv_elements)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
df.to_csv(f"/fNIRS-qc-reports/fNIRS-report-{timestamp}.csv", index=False)