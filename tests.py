import os
import unittest

import librsync

try:
    from BytesIO import BytesIO
except ImportError:
    from io import BytesIO


class TraceLevelTestCase(unittest.TestCase):
    def test_set(self):
        librsync.debug()

    def test_set_invalid(self):
        self.assertRaises(AssertionError, librsync.debug, level=40)


class SingleFileTestCase(unittest.TestCase):
    def setUp(self):
        self.rand = BytesIO(os.urandom(1024**2))


class DoubleFileTestCase(unittest.TestCase):
    def setUp(self):
        self.rand1 = BytesIO(os.urandom(1024**2))
        self.rand2 = BytesIO(os.urandom(1024**2))


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
        self.assertRaises(AssertionError, librsync.patch, None, self.rand2)

    def test_failure(self):
        "Ensure patch aborts when provided invalid delta."
        self.assertRaises(librsync.LibrsyncError, librsync.patch, self.rand1,
                          self.rand2)


class BigPatchTestCase(PatchTestCase):
    def setUp(self):
        "Use large enough test files to cause temp files to hit disk."
        self.rand1 = BytesIO(os.urandom(1024**2*5))
        self.rand2 = BytesIO(os.urandom(1024**2*5))


class Issue3TestCase(PatchTestCase):
    def setUp(self):
        "Use test data provided in issue #3."
        self.rand1 = BytesIO(b'Text.')
        self.rand2 = BytesIO(b'New text.\nText.')


class SimpleStringTestCase(unittest.TestCase):
    def setUp(self):
        self.src = b'FF'
        self.dst = b'FF123FF'

    def test_string_patch(self):
        src_sig = librsync.signature(BytesIO(self.src))
        delta = librsync.delta(BytesIO(self.dst), src_sig).read()
        out = librsync.patch(BytesIO(self.src), BytesIO(delta))

        self.assertEqual(self.dst, out.read())


if __name__ == '__main__':
    unittest.main()
