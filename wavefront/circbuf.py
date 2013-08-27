class CircularBuffer(object):
    def __init__(self, size, item_factory=lambda: None):
        self._size = size
        self._head = 0
        self._buffer = [item_factory() for n in xrange(size)]

    def __repr__(self):
        return "<CircularBuffer %s: size=%s, head=%s>" % (id(self), self._size, self._head)

    def _absidx(self, n):
        return (self._head + n) % self._size

    def append(self, item):
        self._buffer[self._head] = item
        self._head = self._absidx(1)

    def extend(self, items):
        for item in items:
            self.append(item)

    def __len__(self):
        return self._size

    def __getitem__(self, n):
        if isinstance(n, int):
            return self._buffer[self._absidx(n)]
        elif isinstance(n, slice):
            start = 0 if n.start is None else n.start
            stop = self._size if n.stop is None else n.stop
            step = 1 if n.step is None else n.step
            return [self[n] for n in xrange(start, stop, step)]
        else:
            raise TypeError('n must be int or slice')

    def __setitem__(self, n, v):
        if isinstance(n, int):
            self._buffer[self._absidx(n)] = v
        elif isinstance(n, slice):
            start = 0 if n.start is None else n.start
            stop = self._size if n.stop is None else n.stop
            step = 1 if n.step is None else n.step
            for n, v in zip(xrange(start, stop, step), v):
                self[n] = v
        else:
            raise TypeError('n must be int or slice')

    def __iter__(self):
        return (self[n] for n in xrange(self._size))

    def __contains__(self, v):
        return v in self._buffer

