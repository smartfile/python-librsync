import os
import unittest

import librsync

from StringIO import StringIO


class TraceLevelTestCase(unittest.TestCase):
    def test_set(self):
        librsync.debug()


class SingleFileTestCase(unittest.TestCase):
    def setUp(self):
        self.rand = StringIO(os.urandom(1024**2))


class DoubleFileTestCase(unittest.TestCase):
    def setUp(self):
        self.rand1 = StringIO(os.urandom(1024**2))
        self.rand2 = StringIO(os.urandom(1024**2))


class SignatureTestCase(SingleFileTestCase):
    def test_signature(self):
        s = librsync.signature(self.rand)


class DeltaTestCase(DoubleFileTestCase):
    def test_signature(self):
        s = librsync.signature(self.rand1)
        d = librsync.delta(self.rand2, s)

    def test_failure(self):
        "Ensure delta aborts when provided invalid signature."
        self.assertRaises(librsync.LibrsyncError, librsync.delta, self.rand2,
                          self.rand1)


class PatchTestCase(DoubleFileTestCase):
    def test_patch(self):
        s = librsync.signature(self.rand1)
        d = librsync.delta(self.rand2, s)
        self.rand1.seek(0)
        self.rand2.seek(0)
        o = librsync.patch(self.rand1, d)
        self.assertEqual(o.read(), self.rand2.read())

    def test_nonseek(self):
        self.assertRaises(ValueError, librsync.patch, None, self.rand2)

    def test_failure(self):
        "Ensure patch aborts when provided invalid delta."
        self.assertRaises(librsync.LibrsyncError, librsync.patch, self.rand1,
                          self.rand2)


if __name__ == '__main__':
    unittest.main()
