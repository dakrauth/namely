namely
======

.. code-block:: shell

    namely [OPTIONS] [ARGS ...]

    For the following examples, assume we have a directory /var/photos which
    looks like this:

        $ ls -1 /var/photos
        FOO123.JPG
        IMG1010.JPG
        IMG1011.JPG
        IMG1012.JPG
        IMG_XYZ.JPG

    Example #1 - regex:

        $ %prog --dry-run --start 7 --width 3 --increment 2 --regex "IMG(\d\d)(\d+).*" \
            "foo-\2-\#.jpg"  /var/photos/*
        > /var/photos/IMG1010.JPG -> /var/photos/foo-10-007.jpg
        > /var/photos/IMG1011.JPG -> /var/photos/foo-11-009.jpg
        > /var/photos/IMG1012.JPG -> /var/photos/foo-12-011.jpg

    Example #2 - lowercase file names

        $ %prog --dry-run --lower  /var/photos/*
        > /var/photos/FOO123.JPG -> /var/photos/foo123.jpg
        > /var/photos/IMG1010.JPG -> /var/photos/img1010.jpg
        > /var/photos/IMG1011.JPG -> /var/photos/img1011.jpg
        > /var/photos/IMG1012.JPG -> /var/photos/img1012.jpg
        > /var/photos/IMG_XYZ.JPG -> /var/photos/img_xyz.jpg

    Example #3 - complex regex:

        $ %prog -dry-run -width 2 --lower --normalize --regex "" "\@-\#.jpg" Sailing\ 5\:12/
        > Sailing 5:12/P1000354.JPG -> Sailing 5:12/sailing-5-12-001.jpg
        > Sailing 5:12/P1000355.JPG -> Sailing 5:12/sailing-5-12-002.jpg
        > Sailing 5:12/P1000357.JPG -> Sailing 5:12/sailing-5-12-003.jpg
