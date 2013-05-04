import os
import unittest

import librsync

from StringIO import StringIO


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


class PatchTestCase(DoubleFileTestCase):
    def test_patch(self):
        s = librsync.signature(self.rand1)
        d = librsync.delta(self.rand2, s)
        self.rand1.seek(0)
        self.rand2.seek(0)
        o = librsync.patch(self.rand1, d)
        self.assertEqual(o.read(), self.rand2.read())

if __name__ == '__main__':
    unittest.main()
