packing
=======

what is packing
---------------

`packing` provides functions to save many files together into a single (possibly 
compressed) archive. All you need to do is to provide archive's name and target's 
name. `packing` could select proper archiver and compressor according the suffix 
of archive name automatically.

`packing` also provides a friendly way to add archiver or compressor, if `packing` 
couldn't meet your needs.

how to use
----------

```
import packing

# list all available formats and their sufffixs
packing.get_archive_formats()

# create a tarball file named 'example.tar' from 'example'
packing.make_archive('example.tar', 'example')

# create a zip file named 'example.zip' from 'example'
packing.make_archive('example.zip', 'example')

# create a compressed tarball file named 'example.tar.gz' from 'example'
packing.make_archive('example.tar.gz', 'example')

```

license
-------


author
------

Written by Myth
