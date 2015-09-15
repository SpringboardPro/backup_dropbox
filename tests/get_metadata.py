"""Utility program to examine file metadata"""

from datetime import datetime
import logging

import requests

import dfb


def get_metadata(headers, member_id, since=None, maxsize=dfb.MAXFILESIZE,
                 response=None):
    """Generate file metadata for the given member.

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

        # Iterate items, printing metadata
        for lowercase_path, metadata in response['entries']:
            # Ignore files modified before since
            if not metadata['is_dir'] and since:
                last_mod = datetime.strptime(metadata['modified'],
                                             dfb.DATE_FORMAT)
                if last_mod < since:
                    continue
            yield metadata

        # Stop looping if no more items are available
        has_more = response['has_more']

        # Clear the response
        response = None


def main():
    dfb.setup_logging(logging.INFO)
    args = dfb.parse_args()

    # Send the OAuth2 authorization token with every request
    headers = {'Authorization': 'Bearer ' + args.token}

    # Get a list of Dropbox for Business members
    for member_id in dfb.get_members(headers):

        # For each member, get a list of their files
        logging.info('Getting paths for ' + member_id)
        for metadata in get_metadata(headers, member_id, args.since,
                                     args.maxsize):
            logging.info(metadata)


if __name__ == '__main__':
    main()
