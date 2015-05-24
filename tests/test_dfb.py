"""Unit tests for the dfb module."""

from datetime import datetime, timezone
import logging
import unittest
from queue import Queue, Empty

import dfb


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


class TestSetQueue(unittest.TestCase):

    def test_normal_queue(self):
        """Prove that normal Queue allows duplicates."""
        q = Queue()
        q.put('item')
        q.put('item')
        self.assertEqual('item', q.get())
        self.assertEqual('item', q.get())
        self.assertRaises(Empty, q.get, block=False)

    def test_set_queue(self):
        """Prove that SetQueue disallows duplicates."""
        q = dfb.SetQueue()
        q.put('item')
        q.put('item')
        self.assertEqual('item', q.get())
        self.assertRaises(Empty, q.get, block=False)


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

        expected = ['dbmid:AAB_27FUspCzP-DA80EP4r4sr4kn8Uj7h1g',
                    'dbmid:Ak0W11tPO0Z_4wsBvbNyNQsqxBQcT9ccWOQ']

        members = dfb.get_members(None, response=resp)

        for index in range(members.qsize()):
            self.assertEqual(expected[index], members.get())


class TestDateFormat(unittest.TestCase):

    def test(self):
        expected = datetime(2015, 1, 21, 12, 00, 58, tzinfo=timezone.utc)

        date_string = r'Wed, 21 Jan 2015 12:00:58 +0000'
        actual = datetime.strptime(date_string, dfb.DATE_FORMAT)
        self.assertEqual(expected, actual)


if __name__ == '__main__':
    unittest.main()
