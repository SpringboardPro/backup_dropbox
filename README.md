# Dropbox Business local backup tool

`backup` is a tool to create local backups of files from Dropbox Business.

It logs into a Dropbox Business account using the administrator API key
and can access any user's files.

## Requirements

 * [Python](https://www.python.org/downloads) (tested on CPython 3.5)
 * [Dropbox Python SDK](https://www.dropbox.com/developers/core/sdks/python)
 * [requests](http://docs.python-requests.org/)

## Installation

1. Register a Dropbox Business API app with the “Team member file access”
   permission:
   https://www.dropbox.com/developers/business

   You can use the `auth.py` script from the command line to generate an
   authorization code from Dropbox.

2. Clone the git repository and run from the command line as described below.

## Command line usage

To backup all files since 1 January 2015, use:

`python backup.py --since=2015-01-01 --out="path/to/backup" <token>`

`token` is the OAuth2 authorisation token received from Dropbox. You can use
the auth.py utility to help generate this.

Note that dates are expected in ISO 8601 format.

To backup all files up to and including 100 MB in size:

`python backup.py --maxsize=100 --out="path/to/backup" <token>`

## Licence

This project is licensed under the
[Apache 2.0 License](https://www.apache.org/licenses/LICENSE-2.0), a copy of
which is included in the LICENSE file.

## Discussion of backup implementation

Overall strategy:

1. List all users:
   https://www.dropbox.com/developers/business/docs#members-list

2. For every user, use the Dropbox Business API to call /delta:
   https://www.dropbox.com/developers/business#member-file-access
   https://www.dropbox.com/developers/core/docs#delta

3. For every file returned by /delta call /files (GET) to download the file
   content:
   https://www.dropbox.com/developers/core/docs#files-GET


## Contributing to this project

1. Fork the repository on GitHub.
2. Create your local clone (`git clone <your_fork_URL>`).
3. Create your feature branch (`git checkout -b my-new-feature`).
4. Run the test suite (`python -m unittest discover`) and fix any errors.
5. Make your changes.
6. Run the test suite and fix any errors.
7. Run the program and fix any errors.
8. Commit your changes to your local repository
   (`git commit -am 'Add some feature'`).
9. Push your local changes to your fork on GitHub
   (`git push origin my-new-feature`).
10. Create new Pull Request on GitHub.
