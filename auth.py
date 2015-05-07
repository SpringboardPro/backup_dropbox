"""Authenticate an app with Dropbox.

To get an OAuth2 access token from Dropbox, run this script using

python auth.py

and follow the instructions.

See https://www.dropbox.com/developers/core/start/python
"""

from getpass import getpass
import webbrowser

import dropbox


def main():
    key = getpass('Enter your Dropbox key:').strip()
    secret = getpass('Enter your Dropbox secret:').strip()
    flow = dropbox.client.DropboxOAuth2FlowNoRedirect(key, secret)

    # Have the user sign in and authorize this token
    authorize_url = flow.start()
    print('Opening web browser at', authorize_url)
    webbrowser.open(authorize_url)
    print('Click "Allow" (you might have to log in first)')
    print('Copy the authorization code.')
    code = getpass("Enter the authorization code here: ").strip()
    access_token, user_id = flow.finish(code)
    print('Received token', access_token)
    print('Save the access token somewhere safe.')


if __name__ == '__main__':
    main()
