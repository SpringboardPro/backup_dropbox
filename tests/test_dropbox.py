"""Tests for Dropbox for Business access."""

import argparse
from pprint import pprint
import requests


def parse_args():
    """Get Dropbox authorisation token from command line."""
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument('--member_id', help='List files for given member')
    parser.add_argument('--file', help='Download the given file')
    parser.add_argument('token', help='Dropbox for Business access token')

    return parser.parse_args()


def post(headers, url, data='{}'):
    """Post request to Dropbox.

    Args:
        headers (dict): HTTP headers for request
        url (str): url to request
        data (dict): metadata attached to request

    Returns:
        dict: response body (from JSON)
    """
    print('Requesting', url, data)
    r = requests.post(url, headers=headers, data=data)
    r.raise_for_status()
    return r.json()


def main():
    """Main program."""
    args = parse_args()
    headers = {'Content-Type': 'application/json',
               'Authorization': 'Bearer ' + args.token}

    if not args.member_id and not args.file:
        pprint(post(headers, 'https://api.dropbox.com/1/team/get_info'))
        pprint(post(headers, 'https://api.dropbox.com/1/team/members/list'))

    if args.member_id:
        headers['X-Dropbox-Perform-As-Team-Member'] = args.member_id
        pprint(post(headers, 'https://api.dropbox.com/1/account/info'))

        has_more = True
        data = '{}'

        while has_more:
            response = post(headers, 'https://api.dropbox.com/1/delta', data)
            pprint(response)
            has_more = response['has_more']
            data['cursor'] = response['cursor']


if __name__ == '__main__':
    main()
