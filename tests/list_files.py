import os
from time import time
from typing import Iterator

import dropbox


def t() -> str:
    """Return string of elapsed time since start in seconds."""
    return '{:.2f}:'.format(time() - start)


def list_files(user: dropbox.dropbox.Dropbox, dir_: str='') \
               -> Iterator[dropbox.files.Metadata]:
    """Recursively walk the folder tree, yielding files."""
    print('Listing files for', dir_)
    folder_list = user.files_list_folder(dir_, True)

    for entry in folder_list.entries:
        yield entry

    while folder_list.has_more:
        folder_list = user.files_list_folder_continue(folder_list.cursor)

        for entry in folder_list.entries:
            yield entry


start = time()
team = dropbox.DropboxTeam(os.environ['DROPBOX_TEAM_TOKEN'])
members_list = team.team_members_list()

# Get the first member
member = members_list.members[0]

print(t(), 'Listing files for', member.profile.name.display_name)
user = team.as_user(member.profile.team_member_id)

print(t(), 'Calling files_list_folder')

for i, f in enumerate(list_files(user)):
    print(f'{i}: {f.path_display}')
