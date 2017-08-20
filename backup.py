"""Backup Dropbox Business files.

See README.md for full instructions.
"""


import argparse
from datetime import date, datetime
from functools import partial, wraps
import logging
import os
import string
import sys
import time
from typing import Callable, Generic, Iterator, Set, TypeVar
import queue

import dropbox  # type: ignore

__version__ = '2.0.0'

MAX_FILE_SIZE = 100  # Max file size in MB
LOGGING_FILENAME = 'backup.log'

# Type for mypy generics
T = TypeVar('T')


class SetQueue(queue.Queue, Generic[T]):
    """Queue which will allow a given object to be put once only.

    Objects are considered identical if hash(object) are identical.
    """

    def __init__(self, maxsize: int=0) -> None:
        """Initialise queue with maximum number of items.

        0 for infinite queue
        """
        super().__init__(maxsize)
        self.all_items = set()  # type: Set[T]

    def _put(self, item: T) -> None:
        if item not in self.all_items:
            super()._put(item)
            self.all_items.add(item)


class File:
    """File on Dropbox.

    Class required to make files hashable and track the owning member
    """

    def __init__(self, file: dropbox.files.ListFolderResult,
                 member: dropbox.team.TeamMemberProfile) -> None:
        """Initialise with unique ID and member ID."""
        self.file = file
        self.member = member

    def __hash__(self) -> int:
        """Make File hashable for use in sets."""
        return hash(self.file.id)

    def __eq__(self, other) -> bool:
        """Must implement __eq__ if we implement __hash__."""
        try:
            return self.file.id == other.file.id

        except AttributeError:
            return False

    def __repr__(self):
        return self.file.path_display


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', action='version',
                        version=f'%(prog)s {__version__}')

    msg = 'select only files modified since date in YYYY-MM-DD format'
    parser.add_argument('--since', help=msg)

    msg = 'select only files up to size in MB inclusive'
    parser.add_argument('--maxsize', type=int, default=MAX_FILE_SIZE, help=msg)

    msg = 'path of output directory. Default is "yyyy-mm-dd backup".'
    parser.add_argument('--out', help=msg)

    msg = 'logging level: DEBUG=10; INFO=20; WARNING=30; ERROR=40; FATAL=50'
    parser.add_argument('--loglevel', help=msg, default=20, type=int)

    msg = 'Dropbox Business access token. The environment variable '
    'DROPBOX_TEAM_TOKEN is used if token is not supplied.'
    parser.add_argument('--token', help=msg)

    msg = 'Limit number of files to download per user.'
    parser.add_argument('--limit', type=int, help=msg)

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
            msg = '"Since" date must not be later than today.'
            raise argparse.ArgumentError(msg)

    if not args.token:
        try:
            args.token = os.environ['DROPBOX_TEAM_TOKEN']

        except KeyError:
            raise argparse.ArgumentError('Dropbox Team token required')

    return args


def setup_logging(level: int=logging.INFO) -> logging.Logger:
    """Set up logging."""
    logger = logging.getLogger('backup')
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

    return logger


def limit(limit: int):
    """Decorator to limit number of yielded items."""
    logger = logging.getLogger('backup.limit')
    # limit function above is used to take the numberical argument
    # decorator() is the real decorator

    def decorator(function: Callable):
        @wraps(function)
        def wrapper(*args, **kwargs):
            for i, item in enumerate(function(*args, **kwargs)):
                if i < limit:
                    yield item

                else:
                    logger.info(f'Breaking at {i}')
                    break

        return wrapper
    return decorator


def get_members(team: dropbox.dropbox.DropboxTeam) \
                -> Iterator[dropbox.team.TeamMemberProfile]:
    """Generate Dropbox Businesss members.

    This function would not be necessary if the Dropbox Python SDK wasn't so
    bad.  The Dropbox API should have named the function
    team_members_list(limit=None) which would be a generator up to the number
    of team members in limit.
    """
    members_list = team.team_members_list()

    for member in members_list.members:
        yield member

    while members_list.has_more:
        members_list = team.team_members_list_continue(members_list.cursor)

        for member in members_list.members:
            yield member


def enqueue_files(member: dropbox.team.TeamMemberProfile, q: queue.Queue,
                  getter: Callable, predicate: Callable) -> None:
    """Put files for member in the queue if predicate(file) is True."""
    for f in getter(member):
        if predicate(f):
            q.put(f)


def get_files(member: dropbox.team.TeamMemberInfo,
              team: dropbox.DropboxTeam,
              args: argparse.Namespace) -> Iterator[File]:
    """Generate files for the given member."""
    logger = logging.getLogger('backup.get_files')
    logger.info(f'Listing files for {member.profile.name.display_name}')

    user = team.as_user(member.profile.team_member_id)
    folder_list = user.files_list_folder('', True)

    for entry in folder_list.entries:
        logger.debug(f'Found {entry.path_display}')
        yield File(entry, member)

    while folder_list.has_more:
        folder_list = user.files_list_folder_continue(folder_list.cursor)

        for entry in folder_list.entries:
            logger.debug(f'Found {entry.path_display}')
            yield File(entry, member)


def should_download(file: dropbox.files.Metadata,
                    args: argparse.Namespace) -> bool:
    """Return the True if file passes the filters specified in args."""
    logger = logging.getLogger('backup.should_download')

    try:
        # Ignore large files
        if file.file.size > 1e6 * args.maxsize:
            logger.debug(f'Too large: {file}')
            return False

        # Ignore files modified before given date
        if args.since is not None and args.since > file.file.server_modified:
            logger.debug(f'File too old: {file}')
            return False

    except AttributeError:
        # Not a file.  Don't mark to download
        logger.debug(f'Not a file: {file}')
        return False

    # Return all other files
    logger.info(f'File queued: {file}')
    return True


def remove_unprintable(text: str) -> str:
    """Remove unprintable unicode characters."""
    return ''.join(c for c in text if c in string.printable)


def download(file: File, team: dropbox.dropbox.DropboxTeam,
             root: str) -> None:
    """Save the file under the root directory given."""
    logger = logging.getLogger('backup.download')
    printable_path = remove_unprintable(file.file.path_display)

    # Remove the leading slash from printable_path
    local_path = os.path.join(root, printable_path[1:])
    logger.info(f'Saving {local_path}')

    # Create output directory if it does not exist
    try:
        os.makedirs(os.path.dirname(local_path), exist_ok=True)

    except FileNotFoundError as ex:
        # FileNotFoundError raised if path is too long
        logger.error(str(ex))
        return

    try:
        user = team.as_user(file.member.profile.team_member_id)
        user.files_download_to_file(local_path, file.file.path_display)

    except Exception:
        logger.exception(f'Exception whilst saving {local_path}')


def list_and_save(args: argparse.Namespace) -> None:
    """List and save Dropbox files (main program)."""
    logger = logging.getLogger('backup.list_and_save')
    logger.info(f'{__file__} version {__version__}')

    team = dropbox.DropboxTeam(args.token)

    # Create a generator of members
    members = (m for m in get_members(team))

    # Sycnhonised Queue of File objects to download
    file_queue = SetQueue[File]()

    # Create partial functions to save fixed arguments
    _get_files = partial(get_files, team=team, args=args)
    _should_download = partial(should_download, args=args)
    _enqueue_files = partial(enqueue_files, q=file_queue, getter=_get_files,
                             predicate=_should_download)
    #  Enqueue the files
    #  Use map() for easier transition to concurrent map
    list(map(_enqueue_files, members))
    logger.info(f'Queue legnth = {file_queue.qsize()}')

    # Put a poison pill in the Queuue to stop it
    file_queue.put(None)

    # Download each file
    _download = partial(download, team=team, root=args.out)

    # Use iter() to repeatedly call q.get() until it returns None
    list(map(_download, iter(file_queue.get, None)))


def main() -> int:
    # Parse command line arguments
    args = parse_args()
    logger = setup_logging(args.loglevel)

    try:
        start = time.time()
        list_and_save(args)
        logger.info(f'Exit OK at {time.time() - start:.2f} s')
        return 0

    # Ignore SystemExit exceptions (raised by argparse.parse_args() etc.)
    except SystemExit:
        logger.info(f'SystemExit raised at {time.time() - start:.2f} s')
        return 1

    # Report all other exceptions
    except:
        logger.exception(f'Uncaught exception at {time.time() - start:.2f} s')
        return -1


if __name__ == '__main__':
    sys.exit(main())
