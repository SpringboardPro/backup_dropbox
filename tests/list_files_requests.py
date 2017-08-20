import os
import requests
from time import time
from typing import Iterator

import dropbox


def t():
    """Return string of elapsed time since start in seconds."""
    return '{:.2f}:'.format(time() - start)


def list_files(token: str, member_id: str, limit: int=1000) \
               -> Iterator[dropbox.files.Metadata]:
    """Recursively walk the folder tree, yielding files."""
    headers = {'Authorization': 'Bearer ' + token,
               'Dropbox-API-Select-User': member_id}
    list_folder = 'https://api.dropboxapi.com/2/files/list_folder'
    list_folder_continue = 'https://api.dropboxapi.com/2/files/list_folder/continue'
    post_data = {'path': '', 'recursive': True} #, 'limit': limit}

    print(f'Requesting {list_folder} with {post_data}')
    r = requests.post(list_folder, headers=headers, json=post_data)
    r.raise_for_status()
    response = r.json()

    for entry in response['entries']:
        yield entry

    post_data = {'cursor': response['cursor']}

    while response['has_more']:
        print(f'Requesting {list_folder_continue}')
        r = requests.post(list_folder_continue, headers=headers,
                          json=post_data)
        r.raise_for_status()
        response = r.json()

        for entry in response['entries']:
            yield entry

        post_data['cursor'] = response['cursor']


start = time()
token = os.environ['DROPBOX_TEAM_TOKEN']
team = dropbox.DropboxTeam(token)
members_list = team.team_members_list()

# Get the first member
member = members_list.members[0]

print(t(), 'Listing files for', member.profile.name.display_name)

for i, entry in enumerate(list_files(token, member.profile.team_member_id)):
    print(f"{i}: found {entry['path_display']}")
