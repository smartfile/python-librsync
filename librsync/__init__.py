import os
import ctypes
import ctypes.util
import tempfile

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

if os.name == 'posix':
    path = ctypes.util.find_library('rsync')
    if path is None:
        raise ImportError('Could not find librsync, make sure it is installed')
    try:
        _librsync = ctypes.cdll.LoadLibrary(path)
    except OSError:
        raise ImportError('Could not load librsync at "%s"' % path)
elif os.name == 'nt':
    try:
        _librsync = ctypes.cdll.librsync
    except:
        raise ImportError('Could not load librsync, make sure it is installed')
else:
    raise NotImplementedError('Librsync is not supported on your platform')


MAX_SPOOL = 1024 ** 2 * 5

RS_DONE = 0
RS_BLOCKED = 1

RS_JOB_BLOCKSIZE = 65536
RS_DEFAULT_STRONG_LEN = 8
RS_DEFAULT_BLOCK_LEN = 2048


# librsync.h: rs_buffers_s
class Buffer(ctypes.Structure):
    _fields_ = [
        ('next_in', ctypes.c_char_p),
        ('avail_in', ctypes.c_size_t),
        ('eof_in', ctypes.c_int),

        ('next_out', ctypes.c_char_p),
        ('avail_out', ctypes.c_size_t),
    ]

_librsync.rs_strerror.restype = ctypes.c_char_p

patch_callback = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_int, ctypes.c_size_t,
                                  ctypes.POINTER(Buffer))


class LibrsyncError(Exception):
    def __init__(self, result):
        super(LibrsyncError, self).__init__(
            _librsync.rs_strerror(ctypes.c_int(result)))


def _execute(job, f, o=None):
    """
    Executes a librsync "job" by reading bytes from `f` and writing results to
    `o` if provided. If `o` is omitted, the output is ignored.
    """
    # Re-use the same buffer for output, we will read from it after each
    # iteration.
    out = ctypes.create_string_buffer(RS_JOB_BLOCKSIZE)
    while True:
        block = f.read(RS_JOB_BLOCKSIZE)
        buff = Buffer()
        # provide the data block via input buffer.
        buff.next_in = ctypes.c_char_p(block)
        buff.avail_in = ctypes.c_size_t(len(block))
        buff.eof_in = ctypes.c_int(not block)
        # Set up our buffer for output.
        buff.next_out = ctypes.cast(out, ctypes.c_char_p)
        buff.avail_out = ctypes.c_size_t(RS_JOB_BLOCKSIZE)
        result = _librsync.rs_job_iter(job, ctypes.byref(buff))
        if o:
            o.write(out.raw[:RS_JOB_BLOCKSIZE - buff.avail_out])
        if result == RS_DONE:
            break
        elif result != RS_BLOCKED:
            # TODO: I don't think error reporting works properly.
            raise LibrsyncError(result)
    if o and callable(getattr(o, 'seek', None)):
        # As a matter of convenience, rewind the output file.
        o.seek(0)
    return o


def signature(f, s=None, block_size=RS_DEFAULT_BLOCK_LEN):
    """
    Generate a signature for the file `f`. The signature will be written to `s`.
    If `s` is omitted, a temporary file will be used. This function returns the
    signature file `s`. You can specify the size of the blocks using the
    optional `block_size` parameter.
    """
    if s is None:
        s = tempfile.SpooledTemporaryFile(max_size=MAX_SPOOL)
    job = _librsync.rs_sig_begin(block_size, RS_DEFAULT_STRONG_LEN)
    try:
        _execute(job, f, s)
    finally:
        _librsync.rs_job_free(job)
    return s


def delta(f, s, d=None):
    """
    Create a delta for the file `f` using the signature read from `s`. The delta
    will be written to `d`. If `d` is omitted, a temporary file will be used.
    This function returns the delta file `d`. All parameters must be file-like
    objects.
    """
    if d is None:
        d = tempfile.SpooledTemporaryFile(max_size=MAX_SPOOL)
    sig = ctypes.c_void_p()
    try:
        job = _librsync.rs_loadsig_begin(ctypes.byref(sig))
        try:
            _execute(job, s)
        finally:
            _librsync.rs_job_free(job)
        _librsync.rs_build_hash_table(sig)
        job = _librsync.rs_delta_begin(sig)
        try:
            _execute(job, f, d)
        finally:
            _librsync.rs_job_free(job)
    finally:
        _librsync.rs_free_sumset(sig)
    return d


def patch(f, d, o=None):
    """
    Patch the file `f` using the delta `d`. The patched file will be written to
    `o`. If `o` is omitted, a temporary file will be used. This function returns
    the be patched file `o`. All parameters should be file-like objects. `f` is
    required to be seekable.
    """
    if not callable(getattr(f, 'seek', None)):
        raise ValueError('`f` must be a seekable file-like object')
    if o is None:
        o = tempfile.SpooledTemporaryFile(max_size=MAX_SPOOL)

    @patch_callback
    def read_cb(opaque, pos, len, buff):
        f.seek(pos)
        block = f.read(len)
        buff.next_in = ctypes.c_char_p(block)
        buff.avail_in = ctypes.c_size_t(len(block))

    job = _librsync.rs_patch_begin(read_cb, None)
    try:
        _execute(job, d, o)
    finally:
        _librsync.rs_job_free(job)
    return o
