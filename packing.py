import os
import shutil
import tempfile
import subprocess

from distutils.spawn import find_executable

__all__ = ['packing',
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
    prog = find_executable('pigz') or 'gzip'
    _call_external(prog, '--force', input_name)

    gzfile_name = input_name + '.gz'
    if os.path.exists(gzfile_name):
        shutil.move(gzfile_name, output_name)

    return os.path.exists(output_name)

def _do_bzip2(output_name, input_name):
    """ Compress the file with 'bzip2' utility.
    """
    prog = find_executable('pbzip2') or 'bzip2'
    _call_external(prog, '--force', input_name)

    bzfile_name = input_name + '.bz2'
    if os.path.exists(bzfile_name):
        shutil.move(bzfile_name, output_name)

    return os.path.exists(output_name)

def _do_lzop(output_name, input_name):
    """ Compress the file with 'lzop' utility.
    """
    prog = 'lzop'
    _call_external(prog, '--force', '--delete', input_name)

    lzofile_name = input_name + '.lzo'
    if os.path.exists(lzofile_name):
        shutil.move(lzofile_name, output_name)

    return os.path.exists(output_name)

def _make_tarball(archive_name, target_name, compressor=None):
    """ Create a tar file from all the files under 'target_name' or itself.

    'compressor' is a function to compress the tar file. It must accept
    at least two arguments including 'input_name' and 'output_name' and
    return boolean value indicating the compressor result.
    """
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

    if compressor and callable(compressor):
        compressor(output_name=archive_name, input_name=tarball_name)
    else:
        shutil.move(tarball_name, archive_name)

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
    'zip'   : ( _make_zipfile, {} ),
    'tar'   : ( _make_tarball, {'compressor' : None} ),
    'lzotar': ( _make_tarball, {'compressor' : _do_lzop} ),
    'gztar' : ( _make_tarball, {'compressor' : _do_gzip} ),
    'bztar' : ( _make_tarball, {'compressor' : _do_bzip2} ),
}

_ARCHIVE_SUFFIXES = {
    'zip'   : ['.zip'],
    'tar'   : ['.tar'],
    'lzotar': ['.tzo', '.tar.lzo'],
    'gztar' : ['.tgz', '.taz', '.tar.gz'],
    'bztar' : ['.tbz', '.tbz2', '.tar.bz', '.tar.bz2'],
}

def get_archive_formats():
    """ Returns a list of supported formats for archiving.

    Each element of the returned sequence is a tuple (name, [.suffix]).
    """
    formats = []

    for name in _ARCHIVE_FORMATS.keys():
        suffixes = _ARCHIVE_SUFFIXES.get(name, None)
        suffixes and formats.append((name, suffixes))

    return formats

def get_archive_suffixes(format=None):
    """ Return suffixes list of supported format.
    """
    suffixes = []

    if not format is None:
        return _ARCHIVE_SUFFIXES.get(format, [])

    for val in _ARCHIVE_SUFFIXES.itervalues():
        suffixes.extend(val)

    return suffixes

def register_archive_format(name, function, suffixes, extra_kwargs=None):
    """ Registers an archive format.

    'name' is the name of the format. 'function' is the callable that will
    be used to create archives. 'extra_kwargs' is a dictionary that will
    be passed as extend arguments to the callable, if provided. 'suffixes'
    is a sequence containing extensions belong to this format.
    """
    if extra_kwargs is None:
        extra_kwargs = {}

    if not callable(function):
        raise TypeError, "'%s' object is not callable' % function"
    if not isinstance(suffixes, list):
        raise TypeError, "'suffixes' needs to be a sequence"
    if not isinstance(extra_kwargs, dict):
        raise TypeError, "'extra_kwargs' needs to be a dictionary"

    _ARCHIVE_FORMATS[name] = (function, extra_kwargs)
    _ARCHIVE_SUFFIXES[name] = suffixes

def unregister_archive_format(name):
    """ Unregisters an archive format.
    """
    del _ARCHIVE_FORMATS[name]
    del _ARCHIVE_SUFFIXES[name]

def make_archive(archive_name, target_name):
    """ Create an archive file (eg. tar or zip).

    'archive_name' is the name of the file to create.
    'target_name' is the directory / file which we archive.
    """
    for format, suffixes in _ARCHIVE_SUFFIXES.iteritems():
        if filter(archive_name.endswith, suffixes):
            archive_format = format
            break
    else:
        raise ValueError, "unknown archive suffix '%s'" % archive_name

    try:
        func, kwargs = _ARCHIVE_FORMATS[archive_format]
    except KeyError:
        raise ValueError, "unknown archive format '%s'" % archive_format

    if not os.path.exists(target_name):
        raise OSError, "no such file or directory '%s'" % target_name

    return func(archive_name, target_name, **kwargs)

packing = make_archive
