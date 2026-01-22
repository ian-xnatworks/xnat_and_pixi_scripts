"""
PIXI complete study sheet creator
"""
import requests
import csv
import argparse
import json
        
def get_project_experiments(xnat_url, session, project_id):
    url = f"{xnat_url}/data/projects/{project_id}/experiments"
    params = {'format': 'json'}
    
    try:
        response = session.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        experiments = []
        if 'ResultSet' in data and 'Result' in data['ResultSet']:
            experiments = [exp['ID'] for exp in data['ResultSet']['Result']]
        
        print(f"Found {len(experiments)} experiments in {project_id}")
        return experiments
        
    except requests.exceptions.RequestException as e:
        print(f"Error retrieving experiments: {e}")
        return []

def download_experiment_data_as_json(xnat_url, session, experiment_id):
    url = f"{xnat_url}/data/experiments/{experiment_id}"
    params = {'format': 'json'}
    
    try:
        response = session.get(url, params=params)
        data = response.json()
        if 'items' in data:
            data_items = data['items'][0]
            response.raise_for_status()
            return data_items
        
    except requests.exceptions.RequestException as e:
        print(f"Error downloading XML for {experiment_id}: {e}")
        return None

def parse_pet_ct_data(experiment_json, experiment_id, experiment_filter):
    study_sheet_info = []
    
    try:
        data_fields = experiment_json['data_fields']
        # if 'dcmPatientName' not in data_fields:
        #     print(experiment_json)
        study_name = data_fields['label']

        if experiment_filter and experiment_filter not in study_name:
            return []

        study_date = data_fields['date']
        if 'tracer/name' in data_fields: 
            tracer_name = data_fields['tracer/name']
        else:
            tracer_name = ''
        animal_weight = data_fields['dcmPatientWeight']
        tracer_dose = data_fields['tracer/dose']
        tracer_units = data_fields['tracer/dose/units']
        injection_time = data_fields['tracer/startTime']
        scanner_model = data_fields['scanner/model']
                    
        scans = experiment_json['children'][0]['items']
        
        for scan in scans:
            scan_data_fields = scan['data_fields']
            if 'modality' not in scan_data_fields:
                continue
            modality = scan_data_fields['modality'].lower()
            if modality != 'pt' and modality != 'pet' and modality != 'ct':
                continue
            
            scan_name = scan_data_fields['type']
            scan_time = scan_data_fields['startTime']

            scan_info = {
                'Study Name': study_name,
                'Scan Name': scan_name,
                'Animal Weight': animal_weight,
                'Tracer': tracer_name,
                'Activity': '{} {}'.format(tracer_dose, tracer_units),
                'Study Date': study_date,
                'Scan Time': scan_time,
                'Injection Time': injection_time,
                'Scanner': scanner_model
            }
            study_sheet_info.append(scan_info)
        
        if not study_sheet_info:
            print(f"No PET/CT scans found in experiment {experiment_id}")
            
    except Exception as e:
        print(f"Unexpected error processing {experiment_id}: {e}")
    
    return study_sheet_info

def extract_project_data(xnat_url, session, project_id, output_csv, experiment_filter=None):
    print(f"Starting extraction for project: {project_id}")
    print("-" * 60)
    
    experiments = get_project_experiments(xnat_url, session, project_id)
    
    if not experiments:
        print("No experiments found. Exiting.")
        return
    
    all_scan_data = []
    
    for i, exp_id in enumerate(experiments, 1):
        print(f"Processing experiment {i}/{len(experiments)}: {exp_id}")
        
        experiment_json = download_experiment_data_as_json(xnat_url, session, exp_id)
        if experiment_json:
            scan_data = parse_pet_ct_data(experiment_json, exp_id, experiment_filter)
            all_scan_data.extend(scan_data)
    
    if all_scan_data:
        fieldnames = ['Study Name', 'Scan Name', 'Animal Weight', 'Tracer', 'Activity', 'Study Date', 'Scan Time', 'Injection Time', 'Scanner']
        
        with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_scan_data)
        
        print("-" * 60)
        print(f"Successfully extracted {len(all_scan_data)} PET/CT scans")
        print(f"Data written to: {output_csv}")
    else:
        print("-" * 60)
        print("No PET/CT scan data found in project")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', required=True, help='XNAT server URL (e.g. https://example.xnat.com)')
    parser.add_argument('--username', required=True, help='XNAT username')
    parser.add_argument('--password', required=True, help='XNAT password')
    parser.add_argument('--project', required=True, help='XNAT project ID')
    parser.add_argument('--output', required=True, help='Output CSV filename')
    parser.add_argument('--filter', required=False, help='Input to customize what experiments are returned')
    args = parser.parse_args()
    
    xnat_url = args.url.rstrip('/')
    project_id = args.project
    session = requests.Session()
    session.auth = (args.username, args.password)
    output_csv = args.output
    experiment_filter = args.filter

    extract_project_data(xnat_url, session, project_id, output_csv, experiment_filter)

if __name__ == '__main__':
    main()