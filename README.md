# Dropbox for Business local backup tool

`dfb` is a tool to create local backups of files from Dropbox for Business.

It logs into a Dropbox for Business account using the administrator API key
and can access any user's files.

## Requirements

 * [Python](https://www.python.org/downloads) (tested on CPython 3.4)
 * [Dropbox Python SDK](https://www.dropbox.com/developers/core/sdks/python)
 * [requests](http://docs.python-requests.org/)

## Installation

1. Register a Dropbox for Business API app with the “Team member file access”
   permission:
   https://www.dropbox.com/developers/business

   You can use the `auth.py` script from the command line to generate an
   authorization code from Dropbox.

2. Clone the git repository and run from the command line as described below.

## Command line usage

To backup all files since 1 January 2015, use:

`python dfb.py --since=2015-01-01 --out="path/to/backup" <token>`

`token` is the OAuth2 authorisation token received from Dropbox. You can use
the auth.py utility to help generate this.

Note that dates are expected in ISO 8601 format.

To backup all files up to and including 100 MB in size:

`python dfb.py --maxsize=100 --out="path/to/backup" <token>`

## Licence

This project is licensed under the
[Apache 2.0 License](https://www.apache.org/licenses/LICENSE-2.0), a copy of
which is included in the LICENSE file.

## Discussion of dfb implementation

Overall strategy:

1. List all users, and keep track of new users/removed users:
   https://www.dropbox.com/developers/business/docs#members-list
   https://www.dropbox.com/developers/business/docs#log-get-events

2. For every user, use the Dropbox for Business API apps Core API access to
   call /delta:
   https://www.dropbox.com/developers/business#member-file-access
   https://www.dropbox.com/developers/core/docs#delta

3. For every file returned by /delta call /files (GET) to download the file
   content:
   https://www.dropbox.com/developers/core/docs#files-GET


## Contributing to this project

1. Fork the repository on GitHub.
2. Create your local clone (`git clone <your_fork_URL>`).
3. Create your feature branch (`git checkout -b my-new-feature`).
4. Commit your changes to your local repository
   (`git commit -am 'Add some feature'`).
5. Push your local changes to your fork on GitHub
   (`git push origin my-new-feature`).
6. Create new Pull Request on GitHub.
