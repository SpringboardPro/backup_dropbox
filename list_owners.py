"""List all shared folders and their owners."""

import logging
import os
from typing import Iterator

import dropbox

from backup import File, setup_logging, get_members, get_files


def get_folder_members(team: dropbox.DropboxTeam,
                       folder: File) \
                       -> Iterator[dropbox.sharing.UserMembershipInfo]:
    """Yield UserMembershipInfo objects which contain access level information
    (whether user is an owner, editor or viewer of a shared folder).
    """
    user = team.as_user(folder.member.profile.team_member_id)
    members = user.sharing_list_folder_members(folder.file.shared_folder_id)

    for member in members.users:
        yield member

    while members.cursor:
        members = user.sharing_list_folder_members_continue(members.cursor)
        for member in members.users:
            yield member


def main():
    setup_logging()
    logger = logging.getLogger('main')

    logger.info('Please wait up to tens of minutes...')

    shared_folders = set()
    team = dropbox.DropboxTeam(os.environ['DROPBOX_TEAM_TOKEN'])

    for member in get_members(team):
        logger.debug(f'Checking {member.profile.name.display_name}')

        for f in get_files(member, team):

            path = f.file.path_display
            logger.debug(f'Checking {path}')

            # Find out if it is a shared folder
            try:
                if not f.file.sharing_info.parent_shared_folder_id:
                    shared_folders.add(f)

            except AttributeError:
                logger.debug(f'{path} is not a shared folder')

    for sf in shared_folders:
        path = sf.file.path_display

        for member in get_folder_members(team, sf):
            name = member.user.display_name
            logger.debug(f'{path} : {name} : {member.access_type}')

            if member.access_type.is_owner():
                logger.info(f'{path} is owned by {name}')
                break

        else:
            # No owner found for the shared folder
            logger.warning(f'No owner found for {path}')


if __name__ == "__main__":
    main()
