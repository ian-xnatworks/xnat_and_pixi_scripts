import xnat
import re
import sys
import json
import logging
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
	list_of_raters = []
	if base_element_type == 'project':
		subjects = base_element.subjects.values()
		subject_json_list = []

		for subject in subjects:
			subject_json = create_subject_sctructure(subject, list_of_raters)
			if subject_json != None:
				subject_json_list.append(subject_json)

		return subject_json_list, list_of_raters
	elif base_element_type == 'subject':
		subject_json = create_subject_sctructure(base_element, list_of_raters)
		if subject_json != None:
			return [subject_json], list_of_raters
	elif base_element_type == 'experiment':
		experiment_json = create_experiment_structure(base_element, list_of_raters)
		if experiment_json != None:
			return experiment_json, list_of_raters

def create_subject_sctructure(subject, list_of_raters):
	subject_has_fnirs_qc_data = False
	subject_json = {}
	subject_json['id'] = subject.id
	subject_json['label'] = subject.label
	subject_experiment_jsons = []

	experiments = subject.experiments.values()

	for experiment in experiments:
		experiment_json = create_experiment_structure(experiment, list_of_raters)
		if experiment_json != None:
			subject_has_fnirs_qc_data = True
			subject_experiment_jsons.append(experiment_json)

	if subject_has_fnirs_qc_data:
		subject_json['sessions'] = subject_experiment_jsons
		return subject_json
	return None

def create_experiment_structure(experiment, list_of_raters):
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
				scan_json['assessments'] = {}
				scan_id_to_scan_json_dict[scan.id] = scan_json

		for assessor in experiment.assessors.values():
			scan_assessors = assessor.fulldata['children'][0]['items']
			for scan_assessor in scan_assessors:
				if scan_assessor['meta']['xsi:type'] != 'fnirs:fnirsQcScanData':
					continue

				experiment_has_fnirs_qc_data = True
				data_fields = scan_assessor['data_fields']
				scan_json = scan_id_to_scan_json_dict[data_fields['imageScan_ID']]

				lightFalloff_assessment_json = create_assessment_json(scan_json, 'lightFalloff', data_fields, assessor.rater, scan_assessor['meta']['start_date'], list_of_raters)
				pulseSnr_assessment_json = create_assessment_json(scan_json, 'pulseSnr', data_fields, assessor.rater, scan_assessor['meta']['start_date'], list_of_raters)
				pulsatility_assessment_json = create_assessment_json(scan_json, 'pulsatility', data_fields, assessor.rater, scan_assessor['meta']['start_date'], list_of_raters)
				motion_assessment_json = create_assessment_json(scan_json, 'motion', data_fields, assessor.rater, scan_assessor['meta']['start_date'], list_of_raters)
				mapQuality_assessment_json = create_assessment_json(scan_json, 'mapQuality', data_fields, assessor.rater, scan_assessor['meta']['start_date'], list_of_raters)

		if experiment_has_fnirs_qc_data:
			experiment_json['scans'] = list(scan_id_to_scan_json_dict.values())
			return experiment_json
		else:
			return None
	return None

def create_assessment_json(scan_json, assessment_type, data_fields_element, rater, datetime, list_of_raters):
	assessment_json = {}
	assessment_json['rater'] = rater
	if rater not in list_of_raters:
		list_of_raters.append(rater)
	assessment_json['date'] = datetime

	if assessment_type not in data_fields_element:
		return
	assessment_json['score'] = data_fields_element[assessment_type]

	if assessment_type not in scan_json['assessments']:
		scan_json['assessments'][assessment_type] = [assessment_json]
	else:
		scan_json['assessments'][assessment_type].append(assessment_json)

def convert_json_into_csv(json_list, base_element_type, list_of_raters):
	type_to_csv_elements = {}

	if base_element_type == 'project' or base_element_type == 'subject':
		for subject in json_list:
			subject_id = subject['id']
			subject_label = subject['label']
			for experiment in subject['sessions']:
				convert_experiment_into_csv(type_to_csv_elements, experiment, True, subject_id, subject_label, list_of_raters)
	else:
		convert_experiment_into_csv(type_to_csv_elements, json_list, False, None, None, list_of_raters)
	return type_to_csv_elements

def convert_experiment_into_csv(type_to_csv_elements, experiment, include_subject_elements, subject_id, subject_label, list_of_raters):
	experiment_id = experiment['id']
	experiment_label = experiment['label']

	for scan in experiment['scans']:
		scan_id = scan['id']
		scan_type = scan['type']

		for type in scan['assessments'].keys():
			row_info = {}
			if include_subject_elements:
				row_info['Subject ID'] = subject_id
				row_info['Subject Label'] = subject_label                  
			     
			row_info['Experiment ID'] = experiment_id
			row_info['Experiment Label'] = experiment_label
			row_info['Scan ID'] = scan_id
			row_info['Scan Type'] = scan_type

			rater_to_assessment = {}

			for assessment in scan['assessments'][type]:
				rater = assessment['rater']
				assessment_date = assessment['date']

				if rater in rater_to_assessment:
					overlapping_assessment = rater_to_assessment[rater]
					with warnings.catch_warnings():
						warnings.simplefilter("ignore", UnknownTimezoneWarning)
						overlapping_assessment_datetime = parser.parse(overlapping_assessment['date'])
						new_assessment_datetime = parser.parse(assessment_date)
						if overlapping_assessment_datetime > new_assessment_datetime:
							continue
				rater_to_assessment[rater] = assessment

			for rater in list_of_raters:
				if rater in rater_to_assessment:
					assessment = rater_to_assessment[rater]
					row_info[rater] = assessment['score']
				else:
					row_info[rater] = ''

			if type in type_to_csv_elements.keys():
				type_to_csv_elements[type].append(row_info)
			else:
				type_to_csv_elements[type] = [row_info]

def delete_old_csv_elements(base_element, output_directory):
	resources = base_element.resources

	for resource in resources:
		if resource.label == output_directory:
			resource.delete()

if __name__ == "__main__":

	argparser = argparse.ArgumentParser()
	argparser.add_argument('--be', required=True, help='Base Element ID')
	argparser.add_argument('--type', required=True, help='Base Element Type')
	argparser.add_argument('--out', type=str, help='output directory')
	argparser.add_argument('--url', metavar='<str>', type=str, help='XNAT server')
	argparser.add_argument('--u', metavar='<str>', type=str, help='XNAT username')
	argparser.add_argument('--p', metavar='<str>', type=str, help='XNAT password')
	args = argparser.parse_args()

	base_element_type = args.type
	base_element_id = args.be
	output_directory = args.out
	xnat_username = args.u
	xnat_password = args.p
	xnat_server_url = args.url

	connection = xnat.connect(xnat_server_url, user=xnat_username, password=xnat_password)

	logging.basicConfig(handlers=[logging.StreamHandler(sys.stdout)],
		level=logging.getLevelName('DEBUG'),
		format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')

	base_element = None
	if base_element_type == 'project':
		base_element = connection.projects[base_element_id]
	elif base_element_type == 'subject':
		base_element = connection.subjects[base_element_id]
	elif base_element_type == 'experiment':
		base_element = connection.experiments[base_element_id]

	json_list, list_of_raters = create_full_structure_json(base_element_type, base_element)
	type_to_csv_elements = convert_json_into_csv(json_list, base_element_type, list_of_raters)

	delete_old_csv_elements(base_element, output_directory)

	for type in type_to_csv_elements.keys():
		csv_elements = type_to_csv_elements[type]
		df = pd.DataFrame.from_dict(csv_elements)
		logging.debug(f"Csv saved to: {output_directory}/fNIRS-report-{type}.csv")
		df.to_csv(f"{output_directory}/fNIRS-report-{type}.csv", index=False)