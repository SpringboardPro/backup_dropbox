"""Backup Dropbox Business files.

See README.md for full instructions.
"""

import argparse
from datetime import date, datetime
from concurrent.futures import ThreadPoolExecutor
from functools import partial
import json
import logging
import logging.config
import os
import re
import string
import sys
import time
from typing import Callable, Generic, Iterator, Set, TypeVar
import queue

import dropbox  # type: ignore

__version__ = '2.1.3'

DOWNLOAD_THREADS = 8
MAX_QUEUE_SIZE = 100_000

# Characters that are illegal in Windows paths.
# See https://msdn.microsoft.com/en-us/library/aa365247
ILLEGAL_PATH_CHARS = r'<>:"|?*'
ILLEGAL_PATH_PATTERN = re.compile(f'[{re.escape(ILLEGAL_PATH_CHARS)}]')

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
        #  Allow multiple Nones to be queued to act as sentinels
        if item not in self.all_items or item is None:
            super()._put(item)
            self.all_items.add(item)


class File:
    """File on Dropbox.

    Class required to make files hashable and track the owning member.
    """

    def __init__(self, file: dropbox.files.ListFolderResult,
                 member: dropbox.team.TeamMemberProfile) -> None:
        self.file = file
        self.member = member

    def __hash__(self) -> int:
        """Make File hashable for use in sets."""
        return hash(self.file.id)

    def __eq__(self, other: object) -> bool:
        """Must implement __eq__ if we implement __hash__."""
        if isinstance(other, File):
            return self.file.id == other.file.id

        return NotImplemented

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
    parser.add_argument('--maxsize', type=int, help=msg)

    msg = 'path of output directory. Default is "yyyy-mm-dd backup".'
    parser.add_argument('--out', help=msg)

    msg = ('Dropbox Business access token. The environment variable '
           'DROPBOX_TEAM_TOKEN is used if token is not supplied.')
    parser.add_argument('--token', help=msg)

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


def setup_logging() -> None:
    DEFAULT_LOGGING = {
        "version": 1,
        "formatters": {
            "standard": {
                "format": "%(asctime)s %(levelname)-8s %(name)s: %(message)s"
            },
            "brief": {
                "format": "%(asctime)s %(levelname)-8s %(message)s",
                "datefmt": "%H:%M:%S"
            }
        },
        "handlers": {
            "console": {
                "formatter": "brief",
                "class": "logging.StreamHandler"
            },
            "file": {
                "formatter": "standard",
                "class": "logging.handlers.RotatingFileHandler",
                "filename": "backup.log",
                "maxBytes": 10_000_000,
                "backupCount": 5
            }
        },
        "loggers": {
            # Prevent numerous INFO messages from the dropbox package
            "dropbox": {
                "level": "WARNING"
            }
        },
        "root": {
            "level": "INFO",
            "handlers": ["console", "file"]
        }
    }

    try:
        with open('logging_config.json') as f:
            logging.config.dictConfig(json.load(f))

    except FileNotFoundError:
        logging.config.dictConfig(DEFAULT_LOGGING)


def get_members(team: dropbox.dropbox.DropboxTeam) \
                -> Iterator[dropbox.team.TeamMemberProfile]:
    """Generate Dropbox Businesss members."""
    members_list = team.team_members_list()

    for member in members_list.members:
        yield member

    while members_list.has_more:
        members_list = team.team_members_list_continue(members_list.cursor)

        for member in members_list.members:
            yield member


def enqueue(member: dropbox.team.TeamMemberProfile, q: queue.Queue,
            getter: Callable[[dropbox.team.TeamMemberInfo], Iterator[File]],
            predicate: Callable[[dropbox.files.Metadata], bool]) -> None:
    """Enqueue files for member if predicate(file) is True."""
    for f in getter(member):
        if predicate(f):
            q.put(f)


def dequeue(q: queue.Queue, download: Callable[[File], None]) -> None:
    """Call download on each item in queue until q.get() returns None."""
    logger = logging.getLogger('backup.dequeue')

    while True:
        file = q.get()

        if file is None:
            logger.info(f'Poison pill found with {q.qsize()} left in queue')
            break

        member_name = file.member.profile.name.display_name
        msg = f'{q.qsize()} left in queue. Downloading {file} as {member_name}'
        logger.info(msg)
        download(file)


def get_files(member: dropbox.team.TeamMemberInfo,
              team: dropbox.DropboxTeam) -> Iterator[File]:
    """Generate files for the given member."""
    logger = logging.getLogger('backup.get_files')
    display_name = member.profile.name.display_name
    logger.info(f'Listing files for {display_name}')

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

    logger.info(f'No more files for {display_name}')


def should_download(file: dropbox.files.Metadata,
                    args: argparse.Namespace) -> bool:
    """Return the True if file passes the filters specified in args."""
    logger = logging.getLogger('backup.should_download')

    try:
        # Ignore large files
        if args.maxsize is not None and file.file.size > 1e6 * args.maxsize:
            logger.debug(f'Too large: {file}')
            return False

        # Ignore files modified before given date
        if args.since is not None and args.since > file.file.server_modified:
            logger.debug(f'Too old: {file}')
            return False

    except AttributeError:
        # Not a file.  Don't mark to download
        logger.debug(f'Not a file: {file}')
        return False

    # Return all other files
    logger.debug(f'OK: {file}')
    return True


def remove_unprintable(text: str) -> str:
    """Remove unprintable unicode characters."""
    return ''.join(c for c in text if c in string.printable)


def remove_illegal(path: str) -> str:
    """Remove illegal characters."""
    return re.sub(ILLEGAL_PATH_PATTERN, '', path)


def download(file: File, team: dropbox.dropbox.DropboxTeam,
             root: str) -> None:
    """Save the file under the root directory given."""
    logger = logging.getLogger('backup.download')
    path = remove_illegal(remove_unprintable(file.file.path_display))

    # Remove the leading slash from printable_path
    local_path = os.path.join(root, path[1:])
    member_name = file.member.profile.name.display_name
    logger.debug(f'Saving {local_path} as {member_name}')

    # Create output directory if it does not exist
    try:
        os.makedirs(os.path.dirname(local_path), exist_ok=True)

    except FileNotFoundError as ex:
        # FileNotFoundError raised if path is too long
        # If this occurs, see https://bugs.python.org/issue27731
        logger.exception('Path might be too long')
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

    # Sycnhonised Queue of File objects to download
    file_queue = SetQueue[File](MAX_QUEUE_SIZE)

    # Create partial functions to save invariant arguments
    _get_files = partial(get_files, team=team)
    _should_download = partial(should_download, args=args)
    _downloader = partial(download, team=team, root=args.out)

    with ThreadPoolExecutor(DOWNLOAD_THREADS) as consumer_exec:
        # Start the threads to download files
        for _ in range(DOWNLOAD_THREADS):
            consumer_exec.submit(dequeue, file_queue, _downloader)

        # Start the threads to get file names
        with ThreadPoolExecutor() as producer_exec:
            for member in get_members(team):
                producer_exec.submit(enqueue, member, file_queue, _get_files,
                                     _should_download)

        # Tell the threads we're done
        logger.debug('Shutting down the consumer threads')
        for _ in range(DOWNLOAD_THREADS):
            file_queue.put(None)


def main() -> int:
    setup_logging()
    logger = logging.getLogger('backup.main')
    # Parse command line arguments
    args = parse_args()

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
