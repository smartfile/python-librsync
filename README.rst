.. image:: https://d2xtrvzo9unrru.cloudfront.net/brands/smartfile/logo.png
   :alt: SmartFile

A `SmartFile`_ Open Source project. `Read more`_ about how SmartFile
uses and contributes to Open Source software.

.. image:: https://travis-ci.org/smartfile/python-librsync.png
   :target: https://travis-ci.org/smartfile/python-librsync
   :alt: Travis CI Status

.. image:: https://coveralls.io/repos/smartfile/python-librsync/badge.png?branch=master
    :target: https://coveralls.io/r/smartfile/python-librsync
    :alt: Code Coverage

.. image:: https://pypip.in/v/python-librsync/badge.png
    :target: https://crate.io/packages/python-librsync/
    :alt: Latest PyPI version

.. image:: https://pypip.in/d/python-librsync/badge.png
    :target: https://crate.io/packages/python-librsync/
    :alt: Number of PyPI downloads

Introduction
------------

A ctypes wrapper for librsync. Provides ``signature()``, ``delta()``, and
``patch()`` functions.

There are three steps necessary to synchronize a file. Two steps are performed
on the source file and one on the destination.

1. Generate a signature for the destination file.
2. Generate a delta for the source file (using the signature).
3. Patch the destination file using the generated delta.

Usually, these steps involve remote systems. Here is an example of synchronizing
two local files.

.. code:: python

    import librsync

    # The destination file.
    dst = open('Resume-v1.0.pdf', 'rb')

    # The source file.
    src = open('Resume-v1.2.pdf', 'rb')

    # Where we will write the synchronized copy.
    synced = open('Resume-latest.pdf', 'wb')

    # Step 1: prepare signature of the destination file
    signature = librsync.signature(dst)

    # Step 2: prepare a delta of the source file
    delta = librsync.delta(src, signature)

    # Step 3: synchronize the files.
    # In many cases, you would overwrite the destination with the result of
    # synchronization. However, by default a new file is created.
    librsync.patch(dst, delta, synced)

Extending
---------

This wrapper only exposes the most common operations that librsync provides. It
is not meant to be a full wrapper, but should cover most use-cases. You can
easily extend this wrapper. Information about librsync is available in it's
manual which is linked below (I wish I had found this BEFORE writing this
wrapper!)

http://rproxy.samba.org/doxygen/librsync/refman.pdf

.. _SmartFile: http://www.smartfile.com/
.. _Read more: http://www.smartfile.com/open-source.html
