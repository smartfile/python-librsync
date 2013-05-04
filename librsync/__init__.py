import ctypes
import tempfile

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

_librsync = ctypes.cdll.LoadLibrary('librsync.so.1')


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


patch_callback = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_int, ctypes.c_size_t, ctypes.POINTER(Buffer))


class LibRsyncError(Exception):
    def __init__(self, result):
        super(LibRsyncError, self).__init__(
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
        buff.next_out = ctypes.cast(out, ctypes.c_char_p)
        buff.next_in = ctypes.c_char_p(block)
        buff.avail_in = ctypes.c_size_t(len(block))
        buff.eof_in = ctypes.c_int(not block)
        buff.avail_out = ctypes.c_size_t(RS_JOB_BLOCKSIZE)
        result = _librsync.rs_job_iter(job, ctypes.byref(buff))
        if o:
            o.write(out.raw[:RS_JOB_BLOCKSIZE - buff.avail_out])
        if result == RS_DONE:
            break
        elif result != RS_BLOCKED:
            raise LibRsyncError(result)


def signature(f, s=None, block_size=RS_DEFAULT_BLOCK_LEN):
    if s is None:
        s = tempfile.SpooledTemporaryFile(max_size=MAX_SPOOL)
    job = _librsync.rs_sig_begin(block_size, RS_DEFAULT_STRONG_LEN)
    try:
        _execute(job, f, s)
    finally:
        _librsync.rs_job_free(job)
    s.seek(0)
    return s


def delta(f, s, d=None):
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
    d.seek(0)
    return d


def patch(f, d, o=None):
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
    o.seek(0)
    return o
