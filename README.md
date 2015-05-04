# Dropbox for Business local backup tool

`dfb` is a tool to create local backups of
files from Dropbox for Business.

It logs into a Dropbox for Business account using the administrator API key
and can access any user's files.

## Requirements

 * [Python](https://www.python.org/downloads) (tested on CPython 3.4)
 * [Dropbox Python SDK](https://www.dropbox.com/developers/core/sdks/python)

## Installation

1. Register a Dropbox for Business API app with the “Team member file access”
   permission:
   https://www.dropbox.com/developers/business

   You can use the `tools/auth.py` script from the command line to generate an
   authorization code from Dropbox.

2. A proper setup.py has not yet been written. For now, simply clone the git
   repository to where you want to run the program.

## Command line usage

Backup all files since 1 January 2015. Note that dates are expected in ISO
8601 format:

`python dfb.py --since=2015-01-01 --out="path/to/backup"`

Backup all files up to and including 100 MB in size:

`python dfb.py --maxsize=1 --out="path/to/backup"`

## Licence

This project is licensed under the
[Apache 2.0 License](https://www.apache.org/licenses/LICENSE-2.0), a copy of
which is included in the LICENSE file.

## Discussion

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

### Assumptions and caveats

- This assumes eventual consistency is ok. That is, there will be some delay.
  This can be mitigated (only somewhat) by the use of webhooks:
  https://www.dropbox.com/developers/business#webhooks

- This assumes that you don’t need to get every single version of every file.
  That is, there are race conditions possible where when multiple versions of a
  single file are created quickly, the app will only get the latest version,
  not interim versions. This can be mitigated by calling /revisions every time
  a file is modified and downloading each version of the file that the app
  hasn’t seen. This would add some additional complexity:
  https://www.dropbox.com/developers/core/docs#revisions

The Dropbox for Business API can certainly be used via Python, but note that
the official Dropbox Python SDK isn't built to use the Dropbox for Business
API (it's only designed for the Core API), so you'd either need to modify it
or call the Dropbox for Business API endpoints directly.
