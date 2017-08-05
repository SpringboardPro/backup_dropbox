import os
import requests
import sys
from time import time

import dropbox

# Print versions
print('Python', sys.version)
for pkg in (requests, dropbox):
    print(pkg.__name__, pkg.__version__)

# Start timing
start = time()


def t():
    """Return string of elapsed time since start in seconds."""
    return '{:.2f}:'.format(time() - start)


team = dropbox.DropboxTeam(os.environ['DROPBOX_TEAM_TOKEN'])
members_list = team.team_members_list()

# Get the first member
member = members_list.members[0]

print(t(), 'Listing files for', member.profile.name.display_name,
      member.profile.team_member_id)
user = team.as_user(member.profile.team_member_id)

print(t(), 'Calling files_list_folder')
# FIXME: Dropbox server times-out when calling recursive=True
# see Dropbox support request #6264685
folder_list = user.files_list_folder("", True)

entries_count = len(folder_list.entries)
print(t(), 'entries =', entries_count)

while folder_list.has_more:
    print(t(), 'Calling files_list_folder_continue')
    print(folder_list.cursor, end='\n\n')
    folder_list = user.files_list_folder_continue(folder_list.cursor)
    entries_count += len(folder_list.entries)
    print(t(), 'entries =', entries_count)
