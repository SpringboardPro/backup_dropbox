"""Authenticate an app with Dropbox.

See https://www.dropbox.com/developers/core/start/python
"""

import os
import argparse
import sys
import webbrowser

import dropbox

__version__ = '0.1'


def parse_args():
    """Parse command line arguments.

    Get Dropbox key and secret from command line arguments and, failing that,
    get them from environment variables.
    """

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', action='version', version=__version__)

    msg = ('Dropbox API key.'
           'If not supplied, environment variable DFB_KEY is used.')
    parser.add_argument('--key', help=msg)

    msg = ('Dropbox API secret.'
           'If not supplied, environment variable DFB_SECRET is used.')
    parser.add_argument('--secret', help=msg)

    args = parser.parse_args()

    try:
        if not args.key:
            args.key = os.environ['DFB_KEY']

        if not args.secret:
            args.secret = os.environ['DFB_SECRET']

    except KeyError as ex:
        print('ERROR: Environment variable', ex, 'not found')
        sys.exit(1)

    return args


def main():
    args = parse_args()
    flow = dropbox.client.DropboxOAuth2FlowNoRedirect(args.key, args.secret)

    # Have the user sign in and authorize this token
    authorize_url = flow.start()
    print('1. Opening web browser at', authorize_url)
    webbrowser.open(authorize_url)
    print('2. Click "Allow" (you might have to log in first)')
    print('3. Copy the authorization code.')
    code = input("Enter the authorization code here: ").strip()
    access_token, user_id = flow.finish(code)
    print('Received token', access_token)
    print(('For convenience, save the access token as the DFB_TOKEN '
           'environment variable.'))


if __name__ == '__main__':
    main()
