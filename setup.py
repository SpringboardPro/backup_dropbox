"""Setup commands for the backup_dropbox package.

See:
https://packaging.python.org/en/latest/distributing.html
https://github.com/pypa/sampleproject
"""

# Always prefer setuptools over distutils
from setuptools import setup
# To use a consistent encoding
from codecs import open
import io
from os import path
import re


here = path.abspath(path.dirname(__file__))


def read(*names, **kwargs):
    with io.open(
        path.join(here, *names),
        encoding=kwargs.get("encoding", "utf8")
    ) as fp:
        return fp.read()


def find_version(*file_paths):
    version_file = read(*file_paths)
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]",
                              version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")


# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='backup_dropbox',

    # Versions should comply with PEP440.  For a discussion on single-sourcing
    # the version across setup.py and the project code, see
    # https://packaging.python.org/en/latest/single_source_version.html
    version=find_version('', 'backup.py'),

    description='Backup Dropbox Business files',
    long_description=long_description,

    # The project's main homepage.
    url='https://github.com/SpringboardPro/backup_dropbox/',

    # Author details
    author='blokeley',
    # author_email='john@example.com',

    # Choose your license
    license='Apache 2.0',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 5 - Production/Stable',

        # Indicate who your project is intended for
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'Intended Audience :: System Administrators',

        # Pick your license as you wish (should match "license" above)
        'License :: OSI Approved :: Apache Software License',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',

        # Topics
        'Topic :: System :: Archiving :: Backup',
    ],

    # What does your project relate to?
    keywords='Dropbox Business backup',

    # Do not install any Python packages or modules
    # packages=find_packages(exclude=['contrib', 'docs', 'tests']),
    # py_modules=['backup'],

    # List run-time dependencies here.  These will be installed by pip when
    # your project is installed. For an analysis of "install_requires" vs pip's
    # requirements files see:
    # https://packaging.python.org/en/latest/requirements.html
    install_requires=['dropbox'],

    # Create executable script(s)
    entry_points={
        'console_scripts': ['backup_dropbox=backup:main',
                            'auth_dropbox=auth:main'],
    }
)
