"""Backup Dropbox for Business files.

See README.md for full instructions.
"""


import argparse
from datetime import date, datetime, timezone
import logging
import os
import requests
import string
import sys
import time


__version__ = '0.1.2'

MAXFILESIZE = 100  # Max file size in MB
LOGGING_FILE_LEVEL = logging.INFO
LOGGING_FILENAME = 'dfb.log'
LOGGING_CONSOLE_LEVEL = logging.INFO

# Date format used by Dropbox https://www.dropbox.com/developers/core/docs
DATE_FORMAT = r'%a, %d %b %Y %H:%M:%S %z'


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

    parser.add_argument('token', help='Dropbox for Business access token')

    args = parser.parse_args()

    # Create an output directory name if one was not given
    if not args.out:
        args.out = date.today().strftime('%Y-%m-%d') + ' backup'

        # If since was specified, append it to the output directory name
        if args.since:
            args.out = ' '.join((args.out, 'since', args.since))

    # Convert since to a datetime object
    if args.since:
        since = datetime.strptime(args.since, '%Y-%m-%d')

        if since > datetime.now():
            logging.error('"Since" date must not be later than today.')
            sys.exit(1)

        args.since = since.replace(tzinfo=timezone.utc)

    return args


def setup_logging(file_level=LOGGING_FILE_LEVEL,
                  console_level=LOGGING_CONSOLE_LEVEL):
    """Set up logging."""
    logger = logging.getLogger()
    logger.setLevel(min(file_level, console_level))

    # Remove any existing handlers
    for handler in logger.handlers:
        logger.removeHandler(handler)

    # Create a file handler to log to a file
    fh = logging.FileHandler(LOGGING_FILENAME)
    fh.setLevel(file_level)
    logger.addHandler(fh)

    # Create a stream handler to log to the terminal
    sh = logging.StreamHandler()
    sh.setLevel(console_level)
    logger.addHandler(sh)

    fmt = '%(asctime)s %(levelname)-8s %(name)s %(message)s'
    formatter = logging.Formatter(fmt)

    for handler in logger.handlers:
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


def get_metadata(headers, member_id, response=None):
    """Generate metadata for each path for the given member.

    member_id is the Dropbox member id
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

            # Warn if receive 403 response
            if r.status_code == 403:
                msg = '403 not allowed for member {}'
                logging.warning(msg.format(member_id))
                break

            # Raise an exception if status is not OK
            r.raise_for_status()

            response = r.json()

            # Set cursor in the POST data for the next request
            post_data['cursor'] = response['cursor']

        # Iterate path items
        for lowercase_path, metadata in response['entries']:

            if metadata is None:
                msg = 'metadata is None. path: {}; metadata: {}'
                logging.warning(msg.format(lowercase_path, metadata))
                continue

            # Remove unprintable characters
            metadata['path'] = remove_unprintable(metadata['path'])

            logging.debug('Found ' + metadata['path'])
            yield metadata

        # Stop looping if no more items are available
        has_more = response['has_more']

        # Clear the response
        response = None


def remove_unprintable(text):
    """Remove unprintable unicode characters."""
    return ''.join(c for c in text if c in string.printable)


def parse_metadata(metadata, since=None, maxsize=MAXFILESIZE):
    """Parse Dropbox path metadata."""
    # Return shared folders for storing
    if metadata['is_dir']:
        try:
            folder_id = metadata['shared_folder']['shared_folder_id']
            path = '/' + os.path.basename(metadata['path'])
            return {folder_id: path}

        except KeyError:
            # We do not need to parse unshared folders
            return

    # Ignore large files
    if metadata['bytes'] > 1e6 * maxsize:
        return

    # Only return those modified since given date
    if since is not None:
        last_mod = datetime.strptime(metadata['modified'], DATE_FORMAT)
        if since > last_mod:
            return

    logging.debug('Marked for download ' + metadata['path'])
    return metadata


def download_file(headers, member_id, path):
    """Return the data for the given file."""
    url = 'https://api-content.dropbox.com/1/files/auto' + path
    headers['X-Dropbox-Perform-As-Team-Member'] = member_id

    r = requests.get(url, headers=headers)

    # Raise an exception if status code is not OK
    r.raise_for_status()

    return r.content


def save_file(headers, member_id, root, metadata):
    """Save the file under the root directory given."""
    shared_path = metadata['shared_path']
    logging.info('Saving ' + shared_path)

    # Ignore leading slash in path
    local_path = os.path.join(root, shared_path[1:])

    # Create output directory if it does not exist
    os.makedirs(os.path.dirname(local_path), exist_ok=True)

    try:
        # Open file with x flag for exclusive open
        # which can raise a FileExistsError
        with open(local_path, 'xb') as fout:
            try:
                fout.write(download_file(headers, member_id, metadata['path']))
            except Exception:
                logging.exception('Could not download ' + shared_path)

            # Set the file modification time
            mtime = datetime.strptime(metadata['modified'],
                                      DATE_FORMAT).timestamp()
            os.utime(local_path, (mtime, mtime))

    except FileExistsError:
        logging.debug('File exists: ' + local_path)

    except Exception:
        logging.exception('Exception whilst saving {}'.format(local_path))


def main():
    """Main program."""
    setup_logging()

    # Parse command line arguments
    args = parse_args()
    logging.debug('args = {}'.format(str(args)))

    # Send the OAuth2 authorization token with every request
    headers = {'Authorization': 'Bearer ' + args.token}

    # Use a dict with shared folder ids as keys and shared folder paths as
    # values
    shared_id_to_path = {}

    # Get a list of Dropbox for Business members
    # This is a single POST request so does not parallelise
    for member_id in get_members(headers):

        # For each member, get a list of their files
        logging.info('Getting paths for ' + member_id)
        for metadata in get_metadata(headers, member_id):

            # Clean metadata into shared folders or paths
            metadata = parse_metadata(metadata, args.since, args.maxsize)

            if not metadata:
                continue

            if len(metadata) == 1:
                # If metadata is only 1 key-value pair long, it must be a
                # shared folder, not a file
                try:
                    # Iterate over the keys (even though there is only one)
                    for shared_id in metadata:
                        # Warn if the path already registered for the
                        # shared folder is equal to the path given in this
                        # metadata dict. Dropbox sometimes changes the case
                        # for an unknown reason
                        shared = shared_id_to_path[shared_id].lower()
                        meta_id = metadata[shared_id].lower()

                        if shared != meta_id:
                            msg = 'Shared ID {} not equal to metadata ID {}'
                            logging.warning(msg.format(shared, meta_id))

                except KeyError:
                    # shared_id was not recognised so add it to the dict
                    shared_id_to_path.update(metadata)

                continue

            # metadata is for a file
            try:
                # Assume that the file is in a shared folder
                shared_id = metadata['parent_shared_folder_id']
                # Correct the path relative to shared path
                try:
                    index = metadata['path'].index(
                        shared_id_to_path[shared_id])

                except ValueError:
                    msg = 'Cannot convert to shared path: {} not found in {}'
                    logging.error(msg.format(shared_id_to_path[shared_id],
                                  metadata['path']))
                    continue

                metadata['shared_path'] = metadata['path'][index:]

            except KeyError:
                # File is not in a shared folder so save as it is
                pass

            save_file(headers, member_id, args.out, metadata)


if __name__ == '__main__':
    try:
        start = time.time()
        main()
        logging.info('Exit OK at {} s'.format(time.time() - start))

    # Ignore SystemExit exceptions (raised by argparse.parse_args() etc.)
    except SystemExit:
        logging.info('SystemExit raised at {} s'.format(time.time() - start))

    # Report all other exceptions
    except:
        logging.exception('Uncaught exception at {} s'.format(
                          time.time() - start))
