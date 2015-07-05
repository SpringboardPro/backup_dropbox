"""Unit tests for the dfb module."""

from datetime import datetime, timezone
import logging
import unittest

import dfb


class TestGetMembers(unittest.TestCase):

    def test_get_members(self):
        resp = {'has_more': False,
                'members': [
                    {'profile':
                     {'member_id': 'dbmid:AAB_27FUspCzP-DA80EP4r4sr4kn8Uj7h1g',
                      'given_name': 'John',
                      'surname': 'Smith'}},
                    {'profile':
                     {'member_id': 'dbmid:Ak0W11tPO0Z_4wsBvbNyNQsqxBQcT9ccWOQ',
                      'given_name': 'Jane',
                      'surname': 'Example'}}]}

        expected = ('dbmid:AAB_27FUspCzP-DA80EP4r4sr4kn8Uj7h1g',
                    'dbmid:Ak0W11tPO0Z_4wsBvbNyNQsqxBQcT9ccWOQ')

        for i,  member_id in enumerate(dfb.get_members(None, response=resp)):
            self.assertEqual(expected[i], member_id)


class TestPath(unittest.TestCase):

    def setUp(self):
        self.unshared = dfb.Path(12, r'/folder/file.txt')
        self.lower = dfb.Path(123,
                              r'/unshared/shared folder/subfolder/file.txt',
                              r'/shared folder')
        self.mixed = dfb.Path(456,
                              r'/Unshared/Shared Folder/Subfolder/FILE.txt',
                              r'/Shared Folder')
        self.repeated = dfb.Path(789,
                                 r'/Unshared/Shared Folder/Subfolder/'
                                 r'Shared Folder/Subfolder2/FILE.txt',
                                 r'/Shared Folder')

    def test_no_shared(self):
        expected = r'/folder/file.txt'
        self.assertEqual(expected, self.unshared.shared_path)

    def test_lower(self):
        expected = r'/shared folder/subfolder/file.txt'
        self.assertEqual(expected, self.lower.shared_path)

    def test_mixed(self):
        expected = r'/Shared Folder/Subfolder/FILE.txt'
        self.assertEqual(expected, self.mixed.shared_path)

    def test_repeat(self):
        expected = (r'/Shared Folder/Subfolder/Shared Folder/Subfolder2/'
                    'FILE.txt')
        self.assertEqual(expected, self.repeated.shared_path)

    def test_equal(self):
        mixed = dfb.Path(543, r'/Shared Folder/Subfolder/FILE.txt')
        self.assertTrue(mixed == self.mixed)
        self.assertFalse(self.lower == self.mixed)


class TestDateFormat(unittest.TestCase):

    def test(self):
        expected = datetime(2015, 1, 21, 12, 00, 58, tzinfo=timezone.utc)

        date_string = r'Wed, 21 Jan 2015 12:00:58 +0000'
        actual = datetime.strptime(date_string, dfb.DATE_FORMAT)
        self.assertEqual(expected, actual)


class TestLogging(unittest.TestCase):

    @unittest.skip(('Normally skipped because it prints output and '
                    'creates log files'))
    def test_logging(self):
        dfb.setup_logging(logging.DEBUG)
        logging.critical('Critical message')
        logging.error('Error message')
        logging.warning('Warning message')
        logging.info('Info message')
        logging.debug('Debug message')


if __name__ == '__main__':
    unittest.main()
