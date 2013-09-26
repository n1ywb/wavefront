# cython: profile=True

import logging

log = logging.getLogger(__name__)

import cython


cdef class MagicList:
    cdef list _list

    def __init__(self, iterable=None):
        self._list = list()
        if iterable is not None:
            self._list = list(iterable)

    @cython.cdivision(True)
    def __getitem__(self, int n):
        return self._list[n % len(self)]

    @cython.cdivision(True)
    def __setitem__(self, int n, v):
        self._list[n % len(self)] = v

    def __len__(self):
        return len(self._list)
        

cdef class TimeUtil:
#    cdef public double element_time

    @cython.cdivision(True)
    cpdef int index(self, double timestamp):
        return int(timestamp / self.element_time)

    cpdef double timestamp(self, int index):
        return float(index) * self.element_time

    cpdef double floor(self, double timestamp):
        return self.timestamp(self.index(timestamp))

cdef class TimeBuffer(TimeUtil):
    """Associative circular time series buffer of timestamp/value pairs.

    From tail to head timestamps are contiguous and monotonically increasing.

    head_num and head_time are plus one's. I.e. head_num equals the index of
    the newest element in the buffer plus 1. head_time equals the timestamp of
    the newest element in the array plus element_time.

    Supports extended slicing, but step must be an integer.
    """
#    cdef public double element_time
    cdef public int head_num
    cdef public object item_factory
    cdef public int size
    cdef public object _buffer
 
    filler = None

    def __init__(self, size, head_time, element_time):
        assert element_time != 0.0
        self.element_time = element_time
        self.head_num = int(head_time / element_time)
        self.size = size
        self._buffer = MagicList([self.filler,] * size)

    cpdef int tail_num(self):
        return self.head_num - self.size

    cpdef double tail_time(self):
        return self.tail_num() * self.element_time

    cpdef double head_time(self):
        return self.head_num * self.element_time

    def __repr__(self):
        return "<TimeBuffer %s: size=%s, head=%s>" % (id(self), self.size, self.head_num)

    def __str__(self):
        return str(dict(self.iteritems()))

    cpdef append(self, item):
        """Append exactly one item to the buffer. Item timestamp must be
        equal to head_time.
        """
        self._buffer[self.head_num] = item
        self.head_num += 1

    cpdef update(self, double k, v):
        """Update

        Values are put into the buffer. If a value is the newest, it's appended
        to the end. If there's a data gap, missing valures are initialized from
        item_factory.
        """
        if self.index(k) >= self.head_num:
            if self.index(k) > self.head_num + self.size:
                self.head_num = self.index(k) - self.size
            for n in xrange(self.head_num, self.index(k)):
                self.append(self.filler)
            self.append(v)
        else:
            try:
                self[k] = v
            except IndexError:
                pass

    def __getitem__(self, double n):
        if not self.has_key(n):
            raise IndexError
        return self._buffer[self.index(n)]

    def __setitem__(self, double n, v):
        if self.has_key(n) :
            raise IndexError
        self._buffer[self.index(n)] = v
        
    cpdef get(self, double key, default=None):
        try:
            return self[key]
        except IndexError:
            return default

    cpdef has_key(self, double timestamp):
        """True if timestamp is within the buffer boundaries."""
        return (True if timestamp >= self.tail_time() and
                    timestamp < self.head_time() else False)

    def __contains__(self, double timestamp):
        """True if timestamp is within the buffer boundaries."""
        return (True if timestamp >= self.tail_time() and
                    timestamp < self.head_time() else False)


    def iteritems(self, start=None, stop=None):
        cdef int n
        start = self.tail_num() if start is None else self.index(start)
        stop = self.head_num if stop is None else self.index(stop)
        for n in xrange(start, stop):
            try:
                k,v = self.timestamp(n), self._buffer[n]
            except IndexError:
                continue
            yield k,v

    def itervalues(self, start=None, stop=None):
        cdef int n
        start = self.tail_num() if start is None else self.index(start)
        stop = self.head_num if stop is None else self.index(stop)
        for n in xrange(start, stop):
            try:
                v = self._buffer[n]
                yield v
            except IndexError:
                pass

    def __iter__(self):
        return (n * self.element_time for n in xrange(self.tail_num(), self.head_num))

