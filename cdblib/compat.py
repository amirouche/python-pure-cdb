from itertools import chain, cycle, islice, repeat
from mmap import mmap, ACCESS_READ
from os import rename

from .cdblib import Reader, Writer


class cdbmake:
    def __init__(self, cdb, tmp):
        """Create a new database to be stored at the path given by
        *cdb*. Records will be written to the file at the path given by
        *tmp*. After the ``finish()`` method is called, the file at *cdb*
        will be replaced by the one at *tmp*.
        """

        self.fn = cdb
        self.fntmp = tmp

        self._temp_obj = open(self.fntmp, 'wb')
        self._writer = Writer(self._temp_obj)
        self.numentries = 0

    def add(self, key, data):
        """Store a record in the database.
        """
        self._writer.put(key, data)
        self.numentries += 1

    def addmany(self, items):
        """Store each of the records in *items* in the the database.
        *items* should be an iterable of ``(key, value)`` pairs.
        """
        for key, value in items:
            self.add(key, value)

    @property
    def fd(self):
        return self._temp_obj.fileno()

    def finish(self):
        """Finalize the database being written to. Then move the temporary
        database to its final location.
        """
        self._writer.finalize()
        self._temp_obj.close()
        rename(self.fntmp, self.fn)


class cdb:
    def __init__(self, f):
        self._file_path = f
        self._file_obj = open(self._file_path, mode='rb')
        self._mmap_obj = mmap(self._file_obj.fileno(), 0, access=ACCESS_READ)
        self._reader = Reader(self._mmap_obj)

        self._keys = self._get_key_iterator()
        self._items = cycle(self._reader.iteritems(), [None])

    def _get_key_iterator(self):
        return cycle(chain(self._reader.iterkeys(), repeat(None)))

    def each(self):
        """Return successive ``(key, value)`` tuples from the database.
        After the last record is returned, the next call will return ``None``.
        The call after that will return the first record again.
        """

        return next(self._items)

    @property
    def fd(self):
        return self._file_obj.fileno()

    def firstkey(self):
        """Return the first key in the database.
        If ``nextkey()`` is called after ``firstkey()``, the second key will
        returned.
        """

        self._keys = self._get_key_iterator()
        return next(self._keys)

    def get(self, k, i=0):
        """Return the ``i``-th value stored under the key given by ``k``.
        If there are fewer than ``i`` items stored under key ``k``, return
        ``None``.
        """

        return next(islice(self._reader.gets(k), i, i + 1), None)

    def __getitem__(self, key):
        value = self.get(key)
        if value is None:
            raise KeyError(key)

        return value

    def getall(self, k):
        """Return a list of the values stored under key ``k``.
        """

        return list(self._reader.gets(k))

    def keys(self):
        """Return a list of the distinct keys stored in the database.
        """
        return self._reader.keys()

    @property
    def name(self):
        return self._file_path

    def nextkey(self):
        """Return the next key in the datbase, or ``None`` if there are no more
        keys to retrieve. Call ``firstkey()`` to start from the beginning
        again.
        """

        return next(self._keys)

    @property
    def size(self):
        return self._reader.length


def init(f):
    """Return a ``cdb`` object based on the database stored at file path
    *f*.
    """
    return cdb(f)
