"""Backup Dropbox Business files.

See README.md for full instructions.
"""


import argparse
from datetime import date, datetime, timezone
import logging
import os
import string
import sys
import time
import queue

import dropbox

__version__ = '2.0.0'

MAXFILESIZE = 100  # Max file size in MB
LOGGING_FILENAME = 'backup.log'

# Date format used by Dropbox https://www.dropbox.com/developers/core/docs
DATE_FORMAT = r'%a, %d %b %Y %H:%M:%S %z'


class SetQueue(queue.Queue):
    """Queue which will allow a given object to be put once only.

    Objects are considered identical if hash(object) are identical.
    """

    def __init__(self, maxsize=0):
        """Initialise queue with maximum number of items.

        0 for infinite queue
        """
        super().__init__(maxsize)
        self.all_items = set()

    def _put(self, item):
        if item not in self.all_items:
            super()._put(item)
            self.all_items.add(item)


class File:
    """File on Dropbox.

    Class required to make files hashable and track the owning member
    """

    def __init__(self, file, member):
        """Initialise with unique ID and member ID."""
        self.file = file
        self.member = member

    def __hash__(self):
        """Make File hashable for use in sets."""
        return hash(self.file.id)

    def __eq__(self, other):
        """Must implement __eq__ if we implement __hash__."""
        try:
            return self.file.id == other.file.id

        except AttributeError:
            return False


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', action='version',
                        version='%(prog)s ' + __version__)

    msg = 'select only files modified since date in YYYY-MM-DD format'
    parser.add_argument('--since', help=msg)

    msg = 'select only files up to size in MB inclusive'
    parser.add_argument('--maxsize', type=int, default=MAXFILESIZE, help=msg)

    msg = 'path of output directory. Default is "yyyy-mm-dd backup".'
    parser.add_argument('--out', help=msg)

    msg = 'logging level: DEBUG=10; INFO=20; WARNING=30; ERROR=40; FATAL=50'
    parser.add_argument('--loglevel', help=msg, default=20, type=int)

    msg = 'Dropbox Business access token. The environment variable '
    'DROPBOX_TEAM_TOKEN is used if token is not supplied.'
    parser.add_argument('-t', '--token', help=msg)

    args = parser.parse_args()

    # Create an output directory name if one was not given
    if not args.out:
        args.out = date.today().strftime('%Y-%m-%d') + ' backup'

        # If since was specified, append it to the output directory name
        if args.since:
            args.out = ' '.join((args.out, 'since', args.since))

    # Convert since to a datetime object
    if args.since:
        args.since = datetime.strptime(args.since, '%Y-%m-%d')

        if args.since > datetime.now():
            logging.error('"Since" date must not be later than today.')
            sys.exit(1)

    if not args.token:
        try:
            args.token = os.environ['DROPBOX_TEAM_TOKEN']

        except KeyError:
            raise ValueError('Dropbox Team token required')

    return args


def setup_logging(level=logging.INFO):
    """Set up logging."""
    logger = logging.getLogger()
    logger.setLevel(level)

    # Remove any existing handlers
    for handler in logger.handlers:
        logger.removeHandler(handler)

    # Create a file handler to log to a file
    fh = logging.FileHandler(LOGGING_FILENAME)
    fh.setLevel(level)
    logger.addHandler(fh)

    # Create a stream handler to log to the terminal
    sh = logging.StreamHandler()
    sh.setLevel(level)
    logger.addHandler(sh)

    fmt = '%(asctime)s %(levelname)-8s %(name)s %(message)s'
    formatter = logging.Formatter(fmt)

    for handler in logger.handlers:
        handler.setFormatter(formatter)


def get_members(team):
    """Generate Dropbox Businesss members.

    team is a dropbox.dropbox.DropboxTeam instance.
    This function would not be necessary if the Dropbox Python SDK wasn't so
    bad.  The Dropbox API should have named the function
    team_members_list(limit=None) which would be a generator up to the number
    of team members in limit.
    """
    members_list_result = team.team_members_list()

    for member in members_list_result.members:
        yield member

    while members_list_result.has_more:
        cursor = members_list_result.cursor
        members_list_result = team.team_members_list_continue(cursor)

        for member in members_list_result.members:
            yield member


def get_file_list(team, member, args):
    """Generate files for the given member.

    team is a dropbox.dropbox.DropboxTeam
    member is a dropbox.team.TeamMemberProfile
    """
    user = team.as_user(member.profile.team_member_id)
    folder_list = user.files_list_folder("", True)

    for entry in folder_list.entries:
        f = filter_file(entry, args)
        if f:
            yield f

    while folder_list.has_more:
        folder_list = user.files_list_folder_continue(folder_list.cursor)

        for entry in folder_list.entries:
            f = filter_file(entry, args)
            if f:
                yield f


def filter_file(file, args):
    """Return the file if is passes the filters specified in args."""
    try:
        # Ignore large files
        if file.size > 1e6 * args.maxsize:
            logging.debug('Too large: ' + file.path_display)
            return

    except AttributeError:
        # File is a not a file e.g. it's a directory
        logging.debug('Not a file: ' + file.path_display)
        return

    # Ignore files modified before given date
    if args.since is not None:
        if args.since > file.server_modified:
            logging.debug('File too old: ' + file.path_display)
            return

    # Return all other files
    logging.debug('File queued: ' + file.path_display)
    return file


def remove_unprintable(text):
    """Remove unprintable unicode characters."""
    return ''.join(c for c in text if c in string.printable)


def save_file(team, file, root):
    """Save the file under the root directory given."""
    logging.info('Saving ' + file.file.path_display)

    # Ignore leading slash in path
    local_path = os.path.join(root, file.file.path_display)

    # Create output directory if it does not exist
    try:
        os.makedirs(os.path.dirname(local_path), exist_ok=True)

    except FileNotFoundError as ex:
        # FileNotFoundError raised if path is too long
        logging.error(str(ex))
        return

    try:
        user = team.as_user(file.member.member_id)
        user.files_download_to_file(local_path, file.file.path_display)

    except Exception:
        logging.exception('Exception whilst saving ' + local_path)


def list_and_save():
    """List and save Dropbox files (main program)."""
    # Parse command line arguments
    args = parse_args()
    setup_logging(args.loglevel)
    logging.debug('args = ' + str(args))
    logging.info('{} version {}'.format(__file__, __version__))

    team = dropbox.DropboxTeam(args.token)

    # Sycnhonised Queue of File objects to download
    files = SetQueue()

    # Get a list of Dropbox Business members
    for member in get_members(team):

        # For each member, get a list of their files
        logging.info('Getting paths for ' + member.profile.name.display_name)
        for file in get_file_list(team, member, args):
            files.put(File(file, member))

    # Download each file
    for file in files:
        save_file(team, file, args.out)


def main():
    try:
        start = time.time()
        list_and_save()
        logging.info('Exit OK at {:.2f} s'.format(time.time() - start))

    # Ignore SystemExit exceptions (raised by argparse.parse_args() etc.)
    except SystemExit:
        msg = 'SystemExit raised at {:.2f} s'
        logging.info(msg.format(time.time() - start))

    # Report all other exceptions
    except:
        msg = 'Uncaught exception at {:.2f} s'
        logging.exception(msg.format(time.time() - start))


if __name__ == '__main__':
    main()
