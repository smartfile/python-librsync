.. figure:: https://travis-ci.org/smartfile/python-librsync.png
   :alt: Travis CI Status
   :target: https://travis-ci.org/smartfile/python-librsync

A `SmartFile`_ Open Source project. `Read more`_ about how SmartFile
uses and contributes to Open Source software.

.. figure:: http://www.smartfile.com/images/logo.jpg
   :alt: SmartFile

Introduction
------------

A ctypes wrapper for librsync. Provides :python:`signature()`,
:python:`delta()`, and :python:`patch()` functions.

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
    dst = file('Resume-v1.0.pdf', 'rb')
    # The source file.
    src = file('Resume-v1.2.pdf', 'rb')
    # Where we will write the synchronized copy.
    synced = file('Resume-latest.pdf', 'wb')
    
    # Step 1: prepare signature of the destination file
    signature = librsync.signature(dst)
    
    # Step 2: prepare a delta of the source file
    delta = librsync.delta(src, signature)
    
    # Step 3: synchronize the files.
    # In many cases, you would overwrite the destination with the result of
    # synchronization. However, by default a new file is created.
    librsync.patch(dst, delta, synced)


.. _SmartFile: http://www.smartfile.com/
.. _Read more: http://www.smartfile.com/open-source.html
.. role:: python(code)
    :language: python