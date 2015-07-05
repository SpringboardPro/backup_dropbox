"""Backup Dropbox for Business files.

See README.md for full instructions.
"""


import argparse
from datetime import datetime, timezone
import logging
import os
import requests
import sys


__version__ = '0.1.1'

MAXFILESIZE = 100  # Max file size in MB
LOGGING_LEVEL = logging.INFO

# Date format used by Dropbox https://www.dropbox.com/developers/core/docs
DATE_FORMAT = r'%a, %d %b %Y %H:%M:%S %z'


class Path():
    """Path object to encapsulate shared folder and member id.

    Path objects should be treated as immutable - don't try to set attributes.
    """

    def __init__(self, member_id, full_path, shared_folder=''):
        self.__member_id = member_id
        self.__full_path = full_path
        self.__shared_folder = shared_folder

    # Use property decorator to set attributes to raed-only
    @property
    def member_id(self):
        return self.__member_id

    @property
    def full_path(self):
        return self.__full_path

    @property
    def shared_folder(self):
        return self.__shared_folder

    @property
    def shared_path(self):
        """Return path with the shared folder at the root.

        That is, any unshared folders above the shared folder are removed.
        """

        index = self.__full_path.index(self.__shared_folder)
        return self.__full_path[index:]

    def __hash__(self):
        # Implement __hash__() so that object can be used for dict keys
        return hash(self.shared_path)

    def __eq__(self, other):
        # __eq__() must be implemented to make the object hashable
        if not isinstance(other, self.__class__):
            return False

        return self.shared_path == other.shared_path


def parse_args():
    """Parse command line arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', action='version',
                        version='%(prog)s ' + __version__)

    msg = 'select only files modified since date in YYYY-MM-DD format'
    parser.add_argument('--since', help=msg)

    msg = 'select only files up to size in MB inclusive'
    parser.add_argument('--maxsize', type=int, default=MAXFILESIZE, help=msg)

    # TODO: Change default directory to have date in YYYY-MM-DD format
    msg = 'path of output directory. Default is "backup".'
    parser.add_argument('--out', default='backup', help=msg)

    parser.add_argument('token', help='Dropbox for Business access token')

    args = parser.parse_args()

    # Convert since to a datetime object
    if args.since:
        since = datetime.strptime(args.since, '%Y-%m-%d')

        if since > datetime.now():
            logging.error('"Since" date must not be later than today.')
            sys.exit(1)

        args.since = since.replace(tzinfo=timezone.utc)

    return args


def setup_logging(level):
    """Set up logging."""

    logger = logging.getLogger()
    logger.setLevel(level)

    # Remove any existing handlers
    for handler in logger.handlers:
        logger.removeHandler(handler)

    # Create a file handler to log to a file
    fh = logging.FileHandler('dfb.log')
    logger.addHandler(fh)

    # Create a stream handler to log to the terminal
    sh = logging.StreamHandler()
    logger.addHandler(sh)

    fmt = '%(asctime)s %(levelname)-8s %(name)s %(message)s'
    formatter = logging.Formatter(fmt)

    for handler in logger.handlers:
        handler.setLevel(level)
        handler.setFormatter(formatter)


def get_members(headers, response=None):
    """Generate Dropbox for Businesss member ids.

    response is an example response payload for unit testing.
    """

    url = 'https://api.dropbox.com/1/team/members/list'
    has_more = True
    post_data = {}

    while has_more:
        if response is None:
            # Note that POST data must be submitted as application/json
            r = requests.post(url, headers=headers, json=post_data)

            # Raise an exception if status is not OK
            r.raise_for_status()

            response = r.json()

            # Set cursor in the POST data for the next request
            post_data['cursor'] = response['cursor']

        for member in response['members']:
            profile = member['profile']
            logging.info('Found {} {} \t\t{}'.format(
                profile['given_name'],
                profile['surname'],
                profile['member_id'],
                ))

            yield profile['member_id']

        # Stop looping if no more members are available
        has_more = response['has_more']

        # Clear the response
        response = None


def get_paths(headers, member_id, since=None, maxsize=MAXFILESIZE,
              response=None):
    """Generate eligible file paths for the given member.

    member_id is the Dropbox member id
    since is the datetime before which files are ignored
    maxsize is the size above which to ignore in MB
    response is an example response payload for unit testing
    """

    headers['X-Dropbox-Perform-As-Team-Member'] = member_id
    url = 'https://api.dropbox.com/1/delta'
    has_more = True
    post_data = {}

    while has_more:
        # If ready-made response is not supplied, poll Dropbox
        if response is None:
            logging.debug('Requesting delta with {}'.format(post_data))

            # Note that POST data must be sent as
            # application/x-www-form-urlencoded
            r = requests.post(url, headers=headers, data=post_data)

            # Raise an exception if status is not OK
            r.raise_for_status()

            response = r.json()

            # Set cursor in the POST data for the next request
            post_data['cursor'] = response['cursor']

        # Iterate items for possible adding to file list
        for lowercase_path, metadata in response['entries']:
            logging.debug('Assessing ' + metadata['path'])

            # Set queue_this to True if the file should be downloaded
            queue_this = False

            # Ignore directories
            if not metadata['is_dir']:
                # Only list files under maxsize
                if metadata['bytes'] <= 1e6 * maxsize:
                    # Only list those modified since
                    if since:
                        last_mod = datetime.strptime(metadata['modified'],
                                                     DATE_FORMAT)
                        if last_mod >= since:
                            queue_this = True
                    else:
                        queue_this = True

            if queue_this:
                logging.debug('Marked for download ' + metadata['path'])
                yield metadata['path']

        # Stop looping if no more items are available
        has_more = response['has_more']

        # Clear the response
        response = None


def get_file(headers, path, member_id):
    """Return the data for the given file."""

    url = 'https://api-content.dropbox.com/1/files/auto' + path
    headers['X-Dropbox-Perform-As-Team-Member'] = member_id

    r = requests.get(url, headers=headers)

    # Raise an exception if status code is not OK
    r.raise_for_status()

    return r.content


def main():
    setup_logging(LOGGING_LEVEL)

    # Parse command line arguments
    args = parse_args()

    # Send the OAuth2 authorization token with every request
    headers = {'Authorization': 'Bearer ' + args.token}

    # Use a dict with paths as keys and member_ids as values
    # This automatically causes the paths to be a set (no duplicates)
    paths_to_member_ids = {}

    # Get a list of Dropbox for Business members
    # This is a single POST request so does not parallelise
    for member_id in get_members(headers):

        # For each member, get a list of their files
        logging.info('Getting paths for ' + member_id)
        for path in get_paths(headers, member_id, args.since, args.maxsize):
            paths_to_member_ids[path] = member_id

    # Download files in the queue
    # However, do not download file data into a queue for writing later because
    # the queue could rapidly run out of memory
    for path, member_id in paths_to_member_ids.items():
        logging.info('Downloading ' + path)

        # Ignore leading slash in path
        local_path = os.path.join(args.out, path[1:])

        # Create output directory if it does not exist
        os.makedirs(os.path.dirname(local_path), exist_ok=True)

        try:
            with open(local_path, 'wb') as fout:
                fout.write(get_file(headers, path, member_id))
        except Exception:
            logging.error('Could not download {}'.format(path))


if __name__ == '__main__':
    try:
        main()

    # Ignore SystemExit exceptions (raised by argparse.parse_args() etc.)
    except SystemExit:
        pass

    # Report all other exceptions
    except:
        logging.exception('Uncaught exception')
