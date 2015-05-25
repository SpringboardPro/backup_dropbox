"""Tests for Dropbox for Business access."""

import argparse
import json
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
    print('Requesting', url, data)
    r = requests.post(url, headers=headers, data=data)
    r.raise_for_status()
    return r.json()


def main():
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
            data = json.dumps({'cursor': response['cursor']})


if __name__ == '__main__':
    main()
