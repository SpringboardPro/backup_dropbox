"""Unit tests for the backup module."""

import logging
import unittest

import backup


class TestSetQueue(unittest.TestCase):

    def test_unique(self):
        q = backup.SetQueue()
        q.put(27)
        q.put(17)
        self.assertEqual(2, q.qsize())
        q.put(27)
        self.assertEqual(2, q.qsize())

    def test_nones(self):
        """Allow multiple Nones for sentinels to stop multiple threads."""
        q = backup.SetQueue()
        q.put(27)
        q.put(None)
        self.assertEqual(2, q.qsize())
        q.put(None)
        self.assertEqual(3, q.qsize())


class TestRemoveUnprintable(unittest.TestCase):

    def test_remove(self):
        input = 'some\u200c text'
        self.assertEqual('some text', backup.remove_unprintable(input))


class TestLogging(unittest.TestCase):

    @unittest.skip(('Normally skipped because it prints output and '
                    'creates log files'))
    def test_logging(self):
        backup.setup_logging(logging.DEBUG)
        logging.critical('Critical message')
        logging.error('Error message')
        logging.warning('Warning message')
        logging.info('Info message')
        logging.debug('Debug message')


if __name__ == '__main__':
    unittest.main()
