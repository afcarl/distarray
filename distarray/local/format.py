# encoding: utf-8

__docformat__ = "restructuredtext en"


import pickle
import io
import six

import numpy as np
from numpy.lib.format import write_array_header_1_0
from numpy.lib.utils import safe_eval
from numpy.compat import asbytes

from distarray.utils import _raise_nie


MAGIC_PREFIX = asbytes('\x93DARRY')
MAGIC_LEN = len(MAGIC_PREFIX) + 2


def magic(major, minor, prefix=MAGIC_PREFIX):
    """ Return the magic string for the given file format version.

    Parameters
    ----------
    major : int in [0, 255]
    minor : int in [0, 255]

    Returns
    -------
    magic : str

    Raises
    ------
    ValueError if the version cannot be formatted.
    """
    if major < 0 or major > 255:
        raise ValueError("Major version must be 0 <= major < 256.")
    if minor < 0 or minor > 255:
        raise ValueError("Minor version must be 0 <= minor < 256.")
    if six.PY2:
        return prefix + chr(major) + chr(minor)
    elif six.PY3:
        return prefix + bytes([major, minor])
    else:
        raise _raise_nie()


def write_localarray(fp, arr, version=(1, 0)):

    if version != (1, 0):
        msg = "Only version (1, 0) is supported, not %s."
        raise ValueError(msg % (version,))

    fp.write(magic(*version))

    distbuffer = arr.__distarray__()
    metadata  = {'__version__': distbuffer['__version__'],
                 'dim_data': distbuffer['dim_data'],
                }

    write_array_header_1_0(fp, metadata)
    np.save(fp, distbuffer['buffer'])


def read_magic(fp):
    """ Read the magic string to get the version of the file format.

    Parameters
    ----------
    fp : filelike object

    Returns
    -------
    major : int
    minor : int
    """
    magic_str = _read_bytes(fp, MAGIC_LEN, "magic string")
    if magic_str[:-2] != MAGIC_PREFIX:
        msg = "the magic string is not correct; expected %r, got %r"
        raise ValueError(msg % (MAGIC_PREFIX, magic_str[:-2]))
    if six.PY2:
        major, minor = map(ord, magic_str[-2:])
    elif six.PY3:
        major, minor = magic_str[-2:]
    else:
        raise _raise_nie()
    return major, minor


def read_array_header_1_0(fp):
    """
    Read an array header from a filelike object using the 1.0 file format
    version.

    This will leave the file object located just after the header.

    Parameters
    ----------
    fp : filelike object
        A file object or something with a `.read()` method like a file.

    Returns
    -------
    __version__ : str
        Version of the Distributed Array Protocol used.
    dim_data : tuple
        A tuple containing a dictionary for each dimension of the underlying
        array, as described in the Distributed Array Protocol.

    Raises
    ------
    ValueError
        If the data is invalid.

    """
    # Read an unsigned, little-endian short int which has the length of the
    # header.
    import struct
    hlength_str = _read_bytes(fp, 2, "Array header length")
    header_length = struct.unpack('<H', hlength_str)[0]
    header = _read_bytes(fp, header_length, "Array header")

    # The header is a pretty-printed string representation of a literal Python
    # dictionary with trailing newlines padded to a 16-byte boundary. The keys
    # are strings.
    try:
        d = safe_eval(header)
    except SyntaxError as e:
        msg = "Cannot parse header: %r\nException: %r"
        raise ValueError(msg % (header, e))
    if not isinstance(d, dict):
        msg = "Header is not a dictionary: %r"
        raise ValueError(msg % d)
    keys = sorted(d.keys())
    if keys != ['__version__', 'dim_data']:
        msg = "Header does not contain the correct keys: %r"
        raise ValueError(msg % (keys,))

    # TODO: Sanity check with the DAP validator

    return d['__version__'], d['dim_data']


def read_localarray(fp):
    version = read_magic(fp)
    if version != (1, 0):
        msg = "only support version (1,0) of file format, not %r"
        raise ValueError(msg % (version,))

    __version__, dim_data = read_array_header_1_0(fp)

    buf = np.load(fp)

    distbuffer = {
        '__version__': __version__,
        'dim_data': dim_data,
        'buffer': buf,
        }

    return distbuffer


def _read_bytes(fp, size, error_template="ran out of data"):
    """
    Read from file-like object until size bytes are read.
    Raises ValueError if not EOF is encountered before size bytes are read.
    Non-blocking objects only supported if they derive from io objects.

    Required as e.g. ZipExtFile in python 2.6 can return less data than
    requested.
    """
    data = bytes()
    while True:
        # io files (default in python3) return None or raise on would-block,
        # python2 file will truncate, probably nothing can be done about that.
        # note that regular files can't be non-blocking
        try:
            r = fp.read(size - len(data))
            data += r
            if len(r) == 0 or len(data) == size:
                break
        except io.BlockingIOError:
            pass
    if len(data) != size:
        msg = "EOF: reading %s, expected %d bytes got %d"
        raise ValueError(msg %(error_template, size, len(data)))
    else:
        return data
