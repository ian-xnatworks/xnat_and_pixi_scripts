import json
import argparse
from pathlib import Path
import os
import collections

def run_fast_scandir(dir):
    subfolders, files = [], []

    for f in os.scandir(dir):
        if f.is_dir():
            subfolders.append(f.path)
        if f.is_file():
            files.append(f.path)

    for dir in list(subfolders):
        f = run_fast_scandir(dir)
        for file in f: 
            if 'catalog' not in file:
                files.append(os.path.basename(file))
    return files

def perform_validation_on_project(cache_filepath, archive_filepath, input_project_name):
    source_path = cache_filepath+input_project_name+'/source_stats.json'

    try:
        with open(source_path, 'r') as file:
            data = json.load(file)
    except:
        return 'no_cache'

    project_label = data["projectLabel"]
    project_label = project_label.replace(' ', '_')
    project_group = data["group"]
    expected_sessions = data['totalSessions']
    expected_scans = data['totalAcquisitions']

    expected_files_json = data['files']

    list_of_expected_files = []

    for file in expected_files_json:
        list_of_expected_files.append(file['filename'])

    full_project_label = project_group+'_'+project_label
    destination_session_path = archive_filepath+'/'+full_project_label+'/arc001'

    try:
        session_list = os.listdir(destination_session_path)
    except:
        return 'not_started'

    found_session_count = len(session_list)
    found_scan_count = 0

    scan_list = []

    for session_dir in session_list:
        destination_scans_path_string = destination_session_path+'/'+session_dir+'/SCANS'
        if os.path.exists(destination_scans_path_string) == False:
            continue
        destination_scans_path = Path(destination_scans_path_string)
        count = sum(1 for entry in destination_scans_path.iterdir() if entry.is_dir())
        found_scan_count+=count

    files_list = run_fast_scandir(archive_filepath+'/'+full_project_label)

    files_validated = all([ele in list_of_expected_files for ele in files_list])

    print(list_of_expected_files)

    collections.Counter(files_list) == collections.Counter(list_of_expected_files)

    if expected_sessions == found_session_count and expected_scans == found_scan_count and files_validated:
        return 'success'
    return 'not_completed'

def perform_validation(cache_filepath, archive_filepath, input_project=None):
    if input_project is not None:
        project_path_string = cache_filepath + '/' + input_project
        project_path = Path(project_path_string)
        if not project_path.is_dir():
            return        
        project_valid = perform_validation_on_project(cache_filepath, archive_filepath, input_project)
        print(project_valid)
        return

    project_cache_folders = Path(cache_filepath)

    project_list = os.listdir(project_cache_folders)

    list_validated_projects = []
    list_not_cached_projects = []
    list_not_started_projects = []
    list_not_finished_projects = []
    
    for project in project_list:
        project_path_string = cache_filepath + '/' + project
        project_path = Path(project_path_string)
        if not project_path.is_dir():
            continue
        print(project)
        
        project_valid = perform_validation_on_project(cache_filepath, archive_filepath, project)
        
        if project_valid == 'success':
            list_validated_projects.append(project)
        elif project_valid == 'no_cache':
            list_not_cached_projects.append(project)
        elif project_valid == 'not_started':
            list_not_started_projects.append(project)
        elif project_valid == 'not_completed':
            list_not_finished_projects.append(project)

    print('\n\nNot Cached Projects: ')
    print(list_not_cached_projects)
    print('\n\nNot Started Projects')
    print(list_not_started_projects)
    print('\n\nNot Completed Projects')
    print(list_not_finished_projects)
    print('\n\nCompleted Projects')
    print(list_validated_projects)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cf', required=True, help='The filepath for the cache source stats folder')
    parser.add_argument('--a', required=True, help='The filepath to reach the archive folder')
    parser.add_argument('--p', required=False, help='Optional input project id to only run script on one')
    args = parser.parse_args()

    cache_filepath = args.cf
    archive_filepath = args.a
    input_project = args.p

    perform_validation(cache_filepath, archive_filepath, input_project)

if __name__ == '__main__':
    main()