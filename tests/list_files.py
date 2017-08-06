import os
from pprint import pprint
from time import time
from typing import Iterator

import dropbox


def t():
    """Return string of elapsed time since start in seconds."""
    return '{:.2f}:'.format(time() - start)


def get_metadata(obj):
    return {attr: getattr(obj, attr) for attr in
            dir(obj) if not attr.startswith('_')}


def should_download(file: dropbox.files.Metadata) -> bool:
    """Return the True if file passes the filters specified in args."""
    # Ignore large files
    if file.size > 10000:
        print('Too large: ' + file.path_display)
        return False

    return True


def list_files(user: dropbox.dropbox.Dropbox,
               dir_: str='') -> Iterator[dropbox.files.Metadata]:
    """Recursively walk the folder tree, yielding files."""
    print('Listing files for', dir_)
    folder_list = user.files_list_folder(dir_)

    for entry in folder_list.entries:
        try:
            if should_download(entry):
                yield entry

        except AttributeError:
            # Entry does not have the attributes of a file, so
            # treat as a folder
            yield from list_files(user, entry.path_display)


start = time()
team = dropbox.DropboxTeam(os.environ['DROPBOX_TEAM_TOKEN'])
members_list = team.team_members_list()

# Get the first member
member = members_list.members[0]

print(t(), 'Listing files for', member.profile.name.display_name)
user = team.as_user(member.profile.team_member_id)

print(t(), 'Calling files_list_folder')
print([f'OK{f.path_display}' for f in list_files(user)])

print([f'OK{f.path_display}' for f in list_files(user, '/Sandbox')])
