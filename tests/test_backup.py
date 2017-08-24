"""Unit tests for the backup module."""
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


class TestCleanPath(unittest.TestCase):

    def test_remove_illegal(self):
        dirty = r'/path/<with/>some:/ill"egal/char|s?/to*remove'
        expected = r'/path/with/some/illegal/chars/toremove'
        self.assertEqual(expected, backup.clean_path(dirty))


if __name__ == '__main__':
    unittest.main()
