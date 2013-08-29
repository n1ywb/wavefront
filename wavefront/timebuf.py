from wavefront.circbuf import CircularBuffer
from math import floor
from numbers import Number

class MagicList(list):
    def __getitem__(self, n):
        if isinstance(n, Number):
            return super(MagicList, self).__getitem__(n % len(self))
        elif isinstance(n, slice):
            start = 0 if n.start is None else (n.start % len(self))
            stop = len(self) if n.stop is None else (n.stop % len(self))
            step = 1 if n.step is None else n.step
            return [self[n] for n in xrange(start, stop, step)]
        else:
            raise TypeError('n must be int or slice')

    def __setitem__(self, n, v):
        if isinstance(n, Number):
            super(MagicList, self).__setitem__(n % len(self), v)
        elif isinstance(n, slice):
            start = 0 if n.start is None else (n.start % len(self))
            stop = len(self) if n.stop is None else (n.stop % len(self))
            step = 1 if n.step is None else n.step
            for n, v in zip(xrange(start, stop, step), v):
                self[n] = v
        else:
            raise TypeError('n must be int or slice')

class TimeBuffer(object):
    """Associative circular time series buffer of timestamp/value pairs.

    From tail to head timestamps are contiguous and monotonically increasing.

    head_num and head_time are plus one's. I.e. head_num equals the index of
    the newest element in the buffer plus 1. head_time equals the timestamp of
    the newest element in the array plus element_time.

    Supports extended slicing, but step must be an integer.
    """

    def __init__(self, size, head_time, element_time, item_factory=lambda: None):
        self.element_time = element_time
        self.head_num = int(head_time / element_time)
        self.item_factory = item_factory
        self.size = size
        self._buffer = MagicList([item_factory() for n in xrange(size)])

    @property
    def tail_num(self):
        return self.head_num - self._size

    @property
    def tail_time(self):
        return self.tail_num * self.element_time

    @property
    def head_time(self):
        return self.head_num * self.element_time

    def __repr__(self):
        return "<TimeBuffer %s: size=%s, head=%s>" % (id(self), self._size, self._head)

    def __str__(self):
        return str(dict(self.iteritems()))

    def index(self, timestamp):
        return int(timestamp / self.element_time)

    def timestamp(self, index):
        return float(index) * self.element_time

    def append(self, item):
        """Append exactly one item to the buffer. Item timestamp must be
        equal to head_time.
        """
        self._buffer[self.head_num] = item
        self.head_num += 1

    def update(self, items):
        """Update

        Values are put into the buffer. If a value is the newest, it's appended
        to the end. If there's a data gap, missing valures are initialized from
        item_factory.
        """
        for k, v in items:
            if self.index(k) >= self.head_num:
                for n in xrange(self.head_num, self.index(k)):
                    self.append(self.item_factory())
                self.append(v)
            else:
                try:
                    self[k] = v
                except IndexError:
                    pass

    def __getitem__(self, n):
        if isinstance(n, Number):
            if n not in self:
                raise IndexError
            return self._buffer[self.index(n)]
        elif isinstance(n, slice):
            start = self.tail_time if n.start is None else n.start
            stop = self.head_time if n.stop is None else n.stop
            step = self.element_time if n.step is None else n.step
            start, stop, step = [self.index(x) for x in start, stop, step]
            if start < self.tail_num:
                raise IndexError
            if stop > self.head_num:
                raise IndexError
            return self._buffer[start:stop:step]
        else:
            raise TypeError('n must be a number or a slice')

    def __setitem__(self, n, v):
        if isinstance(n, Number):
            if n not in self:
                raise IndexError
            return self._buffer[self.index(n)] = v
        elif isinstance(n, slice):
            start = self.tail_time if n.start is None else n.start
            start = self.index(start)
            stop = self.head_time if n.stop is None else n.stop
            stop = self.index(stop)
            step = 1 if n.step is None else n.step
            if start < self.tail_num:
                raise IndexError
            if stop > self.head_num:
                raise IndexError
            self._buffer[start:stop:step] = v
        else:
            raise TypeError('n must be int or slice')

    def has_key(self, timestamp):
        """True if timestamp is within the buffer boundaries."""
        return (True if timestamp >= self.tail_time and
                    timestamp < self.head_time else False)

    def __contains__(self, timestamp):
        """True if timestamp is within the buffer boundaries."""
        return self.has_key(timestamp)

    def iteritems(self, start=None, stop=None):
        start = self.tail_num if start is None else self.index(start)
        stop = self.head_num if stop is None else self.index(stop)
        for n in xrange(start, stop):
            try:
                k,v = self.timestamp(n), self._buffer[n]
            except IndexError:
                continue
            yield k,v

    def itervalues(self, start=None, stop=None):
        start = self.tail_num if start is None else self.index(start)
        stop = self.head_num if stop is None else self.index(stop)
        for n in xrange(start, stop):
            try:
                v = self._buffer[n]
                yield v
            except IndexError:
                pass

    def __iter__(self):
        return (n * self.element_time for n in xrange(self.tail_num, self.head_num))

