"""Backup Dropbox for Business files.

See README.md for full instructions.
"""


import argparse
from datetime import datetime, timezone
import json
import logging
import os
import requests
import sys
from queue import Queue, Empty


__version__ = '0.1'

MAXFILESIZE = 100  # Max file size in MB
LOGGING_LEVEL = logging.DEBUG
DATE_FORMAT = r'%a, %d %b %Y %H:%M:%S %z'  # date format used by Dropbox


class SetQueue(Queue):
    """Queue which will not allow equal object to be put more than once."""

    def __init__(self, maxsize=0):
        super().__init__(maxsize)
        self.all_items = set()

    def _put(self, item):
        if item not in self.all_items:
            super()._put(item)
            self.all_items.add(item)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', action='version',
                        version='%(prog)s ' + __version__)

    msg = 'select only files modified since date in YYYY-MM-DD format'
    parser.add_argument('--since', help=msg)

    msg = 'select only files up to size in MB inclusive'
    parser.add_argument('--maxsize', type=int, default=MAXFILESIZE, help=msg)

    msg = 'path of output directory. Default is current directory.'
    parser.add_argument('--out', default=os.curdir, help=msg)

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
    """Return a list of Dropbox for Businesss member ids.

    response is an example response payload for unit testing.
    """
    url = 'https://api.dropbox.com/1/team/members/list'
    members = SetQueue()
    has_more = True
    data = '{}'

    while has_more:
        if response is None:
            r = requests.post(url, headers=headers, data=data)
            # Raise an exception if status is not OK
            r.raise_for_status()
            response = r.json()
            # Set cursor in the POST data for the next request
            data = json.dumps({'cursor': response['cursor']})

        for member in response['members']:
            prof = member['profile']
            fmt = 'Found {} {}'
            logging.debug(fmt.format(prof['given_name'], prof['surname']))
            members.put(prof['member_id'])

        # Stop looping if no more members are available
        has_more = response['has_more']

        # Clear the response
        response = None

    return members


def get_paths(headers, paths, member_id, since=None, maxsize=MAXFILESIZE,
              response=None):
    """Add eligible file paths to the list of paths.

    paths is a Queue of files to download later
    member_id is the Dropbox member id
    since is the datetime before which files are ignored
    maxsize is the size above which to ignore in MB
    response is an example response payload for unit testing
    """
    headers['X-Dropbox-Perform-As-Team-Member'] = member_id
    url = 'https://api.dropbox.com/1/delta'
    has_more = True
    data = '{}'

    while has_more:
        # If ready-made response is not supplied, poll Dropbox
        if response is None:
            logging.debug('Requesting delta with ' + data)
            r = requests.post(url, headers=headers, data=data)
            # Raise an exception if status is not OK
            r.raise_for_status()
            response = r.json()
            # Set cursor in the POST data for the next request
            data = json.dumps({'cursor': response['cursor']})

        # Iterate items for possible adding to file list
        for unused, entry in response['entries']:
            logging.debug('Assessing ' + entry['path'])

            # Set queue_this to True if the entry should be downloaded
            queue_this = False

            # Ignore directories
            if not entry['is_dir']:
                # Only list files under maxsize
                if entry['bytes'] <= 1e6 * maxsize:
                    # Only list those modified since
                    if since:
                        last_mod = datetime.strptime(entry['modified'],
                                                     DATE_FORMAT)
                        if last_mod >= since:
                            queue_this = True
                    else:
                        queue_this = True

            if queue_this:
                logging.info('Queued ' + entry['path'])
                paths.put(entry['path'])

        # Stop loop if no more items are available
        has_more = response['has_more']

        # Clear the response
        response = None


def get_file(headers, path):
    """Return the data for the given file."""
    url = 'https://api-content.dropbox.com/1/files/auto' + path
    r = requests.get(url, headers=headers)
    # Raise an exception if status code is not OK
    r.raise_for_status()
    return r.content


def main():
    setup_logging(LOGGING_LEVEL)

    # Parse command line arguments
    args = parse_args()
    headers = {'Content-Type': 'application/json',
               'Authorization': 'Bearer ' + args.token}

    # Get a list of Dropbox for Business members
    # This is a single POST request so does not parallelise
    logging.debug('Getting list of members')
    members = get_members(headers)

    # For each member, get a list of their files
    # TODO: Getting paths for each member could be parallelised
    logging.debug('Getting path list for each member')
    paths = SetQueue()

    # Iterate through the queue of members
    while True:
        try:
            member_id = members.get(block=False)
            logging.debug('Getting paths for ' + member_id)
            get_paths(headers, paths, member_id, args.since)

        except Empty:
            break

    # FIXME: Exit here until get_paths is fixed
    sys.exit(0)

    # Create output directory if it does not exist
    try:
        os.mkdir(args.out)
    except OSError:
        logging.exception('Error making output directory')
        raise

    # Download files in the queue
    # TODO: Downloading files could be paralellised
    while True:
        try:
            path = paths.get(block=False)
            logging.info('Downloading', path)
            local_path = os.path.join((args.out, path))
            with open(local_path, 'w') as fout:
                fout.write(get_file(headers, path))

        except Empty:
            break


if __name__ == '__main__':
    try:
        main()

    # Ignore SystemExit exceptions (raised by argparse.parse_args() etc.)
    except SystemExit:
        pass

    # Report all other exceptions
    except:
        logging.exception('Uncaught exception')
