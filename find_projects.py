"""Find projects which have not been backed up."""

from glob import glob
import os
from pathlib import Path
import sys
from typing import List

import pandas as pd


def main():
    dbx_folder = Path.home() / 'Dropbox (Springboard)'
    os.chdir(dbx_folder)
    reports_folders = glob(f'**{os.sep}Project reports{os.sep}',
                           recursive=True)

    if not reports_folders:
        print('ERROR: No project reports folder found')
        sys.exit(1)

    elif len(reports_folders) > 1:
        print('ERROR: More than one project reports folder found.')
        print(reports_folders)
        sys.exit(2)

    proj_reg_path = dbx_folder / reports_folders[0] / 'Project register.xlsm'
    projects = pd.read_excel(proj_reg_path)
    projects.dropna(inplace=True)

    client_projects = projects[projects['Client'] != 'Springboard']

    client_folders = client_projects['Client'] + ' - ' + \
        client_projects['Project name'] + '.' + \
        client_projects['Code']

    paths: List[str] = []

    if len(sys.argv) == 1:
        print('No target folder given.  Using local Dropbox folder.')
        target = dbx_folder

    else:
        target = sys.argv[1]

    for root, dirs, files in os.walk(target):
        for name in dirs:
            paths.append(os.path.join(root, name))

    not_found: List[str] = []

    for project in client_folders:

        for path in paths:
            if project in path:
                print(f'Found: {path}')
                break

        else:
            not_found.append(project)

    for project in not_found:
        print(f'Not found: {project}')


if __name__ == "__main__":
    main()
