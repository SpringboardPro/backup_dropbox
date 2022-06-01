# Dropbox Business local backup tool

`backup_dropbox` is a tool to create local backups of files from Dropbox Business.

It logs into a Dropbox Business account using the administrator API key
and can access any user's files.

## Requirements

 * [Python](https://www.python.org/downloads) (tested on CPython 3.6)
 * [Dropbox Python SDK](https://github.com/dropbox/dropbox-sdk-python)

## Installation

1. Register a Dropbox Business API app with the “Team member file access”
   permission: https://www.dropbox.com/developers/business

   You can use the `auth_dropbox` script (see below) to generate an
   authorization code from Dropbox.

2. `pip install git+https://github.com/SpringboardPro/backup_dropbox.git`

3. On the command line, run `auth_dropbox` to generate an authorization code.
   You can save this token to the environment variable `DROPBOX_TEAM_TOKEN` to
   avoid having to enter it on the command line every time.

4. Run `backup_dropbox` as described below.

## Command line usage

To backup all files since 01 January 2016, use:

`backup_dropbox --since=2016-01-01 [token]`

`token` is the OAuth2 authorisation token received from Dropbox. If the `token`
is not given, `backup_dropbox` looks for the token in the `DROPBOX_TEAM_TOKEN`
environment variable.

Note that dates are expected in ISO 8601 format (YYYY-MM-DD).

To backup all files up to and including 100 MB in size:

`backup_dropbox --maxsize=100 [token]`

For help on more options, use:

`backup_dropbox --help`

## Utilities

* `auth.py` helps guide the developer through the process of obtaining the
  OAuth2 token required to make API calls to Dropbox.  This only needs to be
  run once.

* `file_stats.py` can be run on a local backup tree to find the files with the
  50 longest file paths, and separately the 50 largest file sizes. Both factors
  cause issues for backups so users can be asked to fix problems.

* `find_projects.py` can be run on a local backup to check that all projects
  were backed up (at least partially).

* `list_owners.py` can be run to list Shared Folders and identify their owners.

## Logging

The default logging settings log brief messages to system output (the terminal)
and more detailed messages to a file called `backup.log`.

You can tailor the logging messages and levels by placing a JSON file in the
current working directory called `logging_config.json`.  See the example
settings in the `DEFAULT_LOGGING` dictionary in `backup.py`, and the
documentation at https://docs.python.org/3/library/logging.html

## Licence

This project is licensed under the
[Apache 2.0 License](https://www.apache.org/licenses/LICENSE-2.0), a copy of
which is included in the LICENSE file.

## Contributing to this project

1. Create an Issue on GitHub.
2. Create your local clone (`git clone <repo_URL>`).
3. Create your feature branch (`git checkout -b my-new-feature`).
4. Run the test suite (`python -m unittest discover`) and fix any errors.
5. Write unit tests to expose the issue.
6. Write your bug fixe or new feature.
7. Run the test suite and fix any errors.
8. Run the program and fix any errors.
9. Commit your changes to your local repository
   (`git commit -am 'Close:NNN Add some feature'`) where NNN is the GitHub
   issue number.
10. Push your local changes to GitHub (`git push origin my-new-feature`).
