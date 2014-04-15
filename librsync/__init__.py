import os
import ctypes
import ctypes.util
import syslog
import tempfile

from functools import wraps


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

TRACE_LEVELS = (
    syslog.LOG_EMERG, syslog.LOG_ALERT, syslog.LOG_CRIT, syslog.LOG_ERR,
    syslog.LOG_WARNING, syslog.LOG_NOTICE, syslog.LOG_INFO, syslog.LOG_DEBUG,
)

RS_DONE = 0
RS_BLOCKED = 1

RS_JOB_BLOCKSIZE = 65536
RS_DEFAULT_STRONG_LEN = 8
RS_DEFAULT_BLOCK_LEN = 2048


# DEFINES FROM librsync.h:
#-------------------------

# librsync.h: rs_buffers_s
class Buffer(ctypes.Structure):
    _fields_ = [
        ('next_in', ctypes.c_char_p),
        ('avail_in', ctypes.c_size_t),
        ('eof_in', ctypes.c_int),

        ('next_out', ctypes.c_char_p),
        ('avail_out', ctypes.c_size_t),
    ]

# char const *rs_strerror(rs_result r);
_librsync.rs_strerror.restype = ctypes.c_char_p
_librsync.rs_strerror.argtypes = (ctypes.c_int, )

# rs_job_t *rs_sig_begin(size_t new_block_len, size_t strong_sum_len);
_librsync.rs_sig_begin.restype = ctypes.c_void_p
_librsync.rs_sig_begin.argtypes = (ctypes.c_size_t, ctypes.c_size_t, )

# rs_job_t *rs_loadsig_begin(rs_signature_t **);
_librsync.rs_loadsig_begin.restype = ctypes.c_void_p
_librsync.rs_loadsig_begin.argtypes = (ctypes.c_void_p, )

# rs_job_t *rs_delta_begin(rs_signature_t *);
_librsync.rs_delta_begin.restype = ctypes.c_void_p
_librsync.rs_delta_begin.argtypes = (ctypes.c_void_p, )

# rs_job_t *rs_patch_begin(rs_copy_cb *, void *copy_arg);
_librsync.rs_patch_begin.restype = ctypes.c_void_p
_librsync.rs_patch_begin.argtypes = (ctypes.c_void_p, ctypes.c_void_p, )

# rs_result rs_build_hash_table(rs_signature_t* sums);
_librsync.rs_build_hash_table.restype = ctypes.c_size_t
_librsync.rs_build_hash_table.argtypes = (ctypes.c_void_p, )

# rs_result rs_job_iter(rs_job_t *, rs_buffers_t *);
_librsync.rs_job_iter.restype = ctypes.c_int
_librsync.rs_job_iter.argtypes = (ctypes.c_void_p, ctypes.c_void_p, )

# void rs_trace_set_level(rs_loglevel level);
_librsync.rs_trace_set_level.restype = None
_librsync.rs_trace_set_level.argtypes = (ctypes.c_int, )

# void rs_free_sumset(rs_signature_t *);
_librsync.rs_free_sumset.restype = None
_librsync.rs_free_sumset.argtypes = (ctypes.c_void_p, )

# rs_result rs_job_free(rs_job_t *);
_librsync.rs_job_free.restype = ctypes.c_int
_librsync.rs_job_free.argtypes = (ctypes.c_void_p, )

# A function declaration for our read callback.
patch_callback = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_longlong,
                                  ctypes.c_size_t, ctypes.POINTER(Buffer))


class LibrsyncError(Exception):
    def __init__(self, r):
        super(LibrsyncError, self).__init__(_librsync.rs_strerror(
            ctypes.c_int(r)))


def seekable(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        s = args[0]
        assert callable(getattr(s, 'seek', None)), 'Must provide seekable ' \
            'file-like object'
        return f(*args, **kwargs)
    return wrapper


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
        r = _librsync.rs_job_iter(job, ctypes.byref(buff))
        if o:
            o.write(out.raw[:RS_JOB_BLOCKSIZE - buff.avail_out])
        if r == RS_DONE:
            break
        elif r != RS_BLOCKED:
            raise LibrsyncError(r)
        if buff.avail_in > 0:
            # There is data left in the input buffer, librsync did not consume
            # all of it. Rewind the file a bit so we include that data in our
            # next read. It would be better to simply tack data to the end of
            # this buffer, but that is very difficult in Python.
            f.seek(f.tell() - buff.avail_in)
    if o and callable(getattr(o, 'seek', None)):
        # As a matter of convenience, rewind the output file.
        o.seek(0)
    return o


def debug(level=syslog.LOG_DEBUG):
    assert level in TRACE_LEVELS, "Invalid log level %i" % level
    _librsync.rs_trace_set_level(level)


@seekable
def signature(f, s=None, block_size=RS_DEFAULT_BLOCK_LEN):
    """
    Generate a signature for the file `f`. The signature will be written to `s`.
    If `s` is omitted, a temporary file will be used. This function returns the
    signature file `s`. You can specify the size of the blocks using the
    optional `block_size` parameter.
    """
    if s is None:
        s = tempfile.SpooledTemporaryFile(max_size=MAX_SPOOL, mode='wb+')
    job = _librsync.rs_sig_begin(block_size, RS_DEFAULT_STRONG_LEN)
    try:
        _execute(job, f, s)
    finally:
        _librsync.rs_job_free(job)
    return s


@seekable
def delta(f, s, d=None):
    """
    Create a delta for the file `f` using the signature read from `s`. The delta
    will be written to `d`. If `d` is omitted, a temporary file will be used.
    This function returns the delta file `d`. All parameters must be file-like
    objects.
    """
    if d is None:
        d = tempfile.SpooledTemporaryFile(max_size=MAX_SPOOL, mode='wb+')
    sig = ctypes.c_void_p()
    try:
        job = _librsync.rs_loadsig_begin(ctypes.byref(sig))
        try:
            _execute(job, s)
        finally:
            _librsync.rs_job_free(job)
        r = _librsync.rs_build_hash_table(sig)
        if r != RS_DONE:
            raise LibrsyncError(r)
        job = _librsync.rs_delta_begin(sig)
        try:
            _execute(job, f, d)
        finally:
            _librsync.rs_job_free(job)
    finally:
        _librsync.rs_free_sumset(sig)
    return d


@seekable
def patch(f, d, o=None):
    """
    Patch the file `f` using the delta `d`. The patched file will be written to
    `o`. If `o` is omitted, a temporary file will be used. This function returns
    the be patched file `o`. All parameters should be file-like objects. `f` is
    required to be seekable.
    """
    if o is None:
        o = tempfile.SpooledTemporaryFile(max_size=MAX_SPOOL, mode='wb+')

    @patch_callback
    def read_cb(opaque, pos, length, buff):
        f.seek(pos)
        block = f.read(length)
        buff.next_in = ctypes.c_char_p(block)
        buff.avail_in = ctypes.c_size_t(len(block))
        return RS_DONE

    job = _librsync.rs_patch_begin(read_cb, None)
    try:
        _execute(job, d, o)
    finally:
        _librsync.rs_job_free(job)
    return o
