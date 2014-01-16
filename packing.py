import os
import shutil
import tempfile
import subprocess

from functools import partial
from distutils.spawn import find_executable

__all__ = ['packing',
           'compressing',
           'make_archive',
           'get_archive_formats',
           'get_archive_suffixes',
           'register_archive_format',
           'unregister_archive_format']

def _call_external(*cmdln):
    """ Wapper for subprocess calls.

    'cmdln[0]' is just the program to run. 'cmdln[1:]' is the rest of
    its options and arguments. They will be joined before execution.
    Return value is a tuple (retcode, outdata, errdata).
    """
    if len(cmdln) < 1:
        raise TypeError, "_call_external() takes at least 1 arguments"

    exe = find_executable(cmdln[0]) or cmdln[0]
    cmd = ' '.join((exe,) + cmdln[1:])
    proc = subprocess.Popen(cmd, shell=True,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT)
    (outdata, errdata) = proc.communicate()

    return (proc.returncode, outdata, errdata)

def _do_gzip(output_name, input_name):
    """ Compress the file with 'gzip' utility.
    """
    for util in ('pgzip', 'pigz'):
        prog = find_executable(util)
        if prog:
            break
    else:
        prog = 'gzip'

    _call_external(prog, '--force', input_name)

    gzfile_name = input_name + '.gz'
    if os.path.exists(gzfile_name):
        shutil.move(gzfile_name, output_name)

    return os.path.exists(output_name)

def _do_bzip2(output_name, input_name):
    """ Compress the file with 'bzip2' utility.
    """
    prog = find_executable('pbzip2')
    if not prog:
        prog = 'bzip2'

    _call_external(prog, '--force', input_name)

    bzfile_name = input_name + '.bz2'
    if os.path.exists(bzfile_name):
        shutil.move(bzfile_name, output_name)

    return os.path.exists(output_name)

def _do_lzop(output_name, input_name):
    """ Compress the file with 'lzop' utility.
    """
    _call_external('lzop', '--force', '--delete', input_name)

    lzofile_name = input_name + '.lzo'
    if os.path.exists(lzofile_name):
        shutil.move(lzofile_name, output_name)

    return os.path.exists(output_name)

def _do_compress(output_name, input_name, format):
    """ Compress the file with the proper compressor.

    'format' must be "gz", "bz2" or "lzo".
    """
    compression = {
        'gz' : _do_gzip,
        'bz2': _do_bzip2,
        'lzo': _do_lzop,
    }

    try:
        compressor = compression[format]
    except KeyError, err:
        raise ValueError, "unknown compression format '%s'" % format

    return compressor(output_name, input_name)

def _make_tarball(archive_name, target_name, compress=None):
    """ Create a (possibly compressed) tar file from all the files under
    'target_name' or itself.

    'compress' must be None (the default), "gz", "bz2" or "lzo".
    """
    if compress not in (None, 'gz', 'bz2', 'lzo'):
        raise ValueError, \
            ("bad value for 'compress': must be None, 'gz', 'bz2' or 'lzo'")

    archive_dir = os.path.dirname(archive_name)

    if not os.path.exists(archive_dir):
        os.makedirs(archive_dir)

    import tarfile

    tarball_name = tempfile.mktemp(suffix='.tar', dir=archive_dir)
    tar = tarfile.open(tarball_name, 'w')

    if os.path.isdir(target_name):
        for child in os.listdir(target_name):
            tar.add(os.path.join(target_name, child), child)
    else:
        tar.add(target_name, os.path.basename(target_name))

    tar.close()

    if compress is None:
        shutil.move(tarball_name, archive_name)
    else:
        _do_compress(archive_name, tarball_name, compress)

    return os.path.exists(archive_name)

def _make_zipfile(archive_name, target_name):
    """ Create a zip file from all the files under 'target_name' or itself.
    """
    archive_dir = os.path.dirname(archive_name)

    if not os.path.exists(archive_dir):
        os.makedirs(archive_dir)

    import zipfile

    arv = zipfile.ZipFile(archive_name, 'w', compression=zipfile.ZIP_DEFLATED)

    if os.path.isdir(target_name):
        for dirpath, dirname, filenames in os.walk(target_name):
            for filename in filenames:
                filepath = os.path.normpath(os.path.join(dirpath, filename))
                arcname = os.path.relpath(filepath, target_name)
                if os.path.isfile(filepath):
                    arv.write(filepath, arcname)
    else:
        arv.write(target_name, os.path.basename(target_name))

    arv.close()

    return os.path.exists(archive_name)

_ARCHIVE_FORMATS = {
    'zip'   : ( _make_zipfile, ['.zip'] ),
    'tar'   : ( _make_tarball, ['.tar'] ),
    'lzotar': ( partial(_make_tarball, compress='lzo'), ['.tzo', '.tar.lzo'] ),
    'gztar' : ( partial(_make_tarball, compress='gz'),  ['.tgz', '.taz', '.tar.gz'] ),
    'bztar' : ( partial(_make_tarball, compress='bz2'), ['.tbz', '.tbz2', '.tar.bz', '.tar.bz2'] ),
}

def get_archive_formats():
    """ Return a list of supported formats for archiving.

    Each element of the returned sequence is a tuple (name, extensions).
    """
    formats = [ (name, registry[1]) for name, registry in
                _ARCHIVE_FORMATS.items() ]
    formats.sort()
    return formats

def get_archive_extensions(*formats):
    """ Return extensions list of supported formats.
    """
    if len(formats) == 0:
        formats = _ARCHIVE_FORMATS.keys()

    extensions = []

    for fmt in formats:
        registry = _ARCHIVE_FORMATS.get(fmt, None)
        if registry:
            extensions.extend(registry[1])

    return extensions

def register_archive_format(name, function, extensions):
    """ Register an archive format.

    'name' is the name of the archive format. 'function' is the callable
    that will be used to create archives. 'extensions' is a sequence
    containing extensions belong to this format.
    """
    if not callable(function):
        raise TypeError, "'%s' object is not callable' % function"
    if not isinstance(extensions, (list, tuple)):
        raise TypeError, "'suffixes' needs to be a sequence"

    _ARCHIVE_FORMATS[name] = (function, extensions)

def unregister_archive_format(name):
    """ Unregister an archive format.
    """
    del _ARCHIVE_FORMATS[name]

def make_archive(archive_name, target_name):
    """ Create an archive file (eg. tar or zip).

    'archive_name' is the name of the file to create. Its extension will
    determine archive format. 'target_name' is the directory / file which
    we archive.
    """
    for format, registry in _ARCHIVE_FORMATS.iteritems():
        if filter(archive_name.endswith, registry[1]):
            archive_format = format
            archive_runner = registry[0]
            break
    else:
        raise ValueError, "unknown archive extension '%s'" % archive_name

    if not os.path.exists(target_name):
        raise OSError, "no such file or directory '%s'" % target_name

    return archive_runner(archive_name, target_name)

packing = make_archive
compressing = _do_compress
