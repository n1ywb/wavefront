class CircularBuffer(object):
    """Fixed sized pre-initialized circular buffer.

    :param size: Number of elements in buffer.
    :item_factory: Called ``size`` times to initialize buffer.

    If ``item_factory`` is not specified, each element is initialized to
    ``None``.

    Item 0 is the oldest element in the buffer. Item 1 is second oldest, and so
    on. Item -1 is the newest element, -2 is the second newest, and so on.

    Example:

    >>> from circbuf import CircularBuffer
    >>> cb = CircularBuffer(3)
    >>> str(cb)
    '[None, None, None]'
    >>> repr(cb) # doctest: +ELLIPSIS
    '<CircularBuffer ...: size=3, head=0>'
    >>> len(cb)
    3
    >>> cb.append('wensleydale')
    >>> str(cb)
    "[None, None, 'wensleydale']"
    >>> cb.extend(('chedder', 'limburger'))
    >>> str(cb)
    "['wensleydale', 'chedder', 'limburger']"
    >>> 'chedder' in cb
    True
    >>> 'gorgonzola' in cb
    False
    >>> cb[0]
    'wensleydale'
    >>> cb[-1]
    'limburger'
    >>> cb[-2]
    'chedder'
    >>> cb[1]
    'chedder'
    >>> cb[9999997]
    'chedder'
    >>> cb[0:2]
    ['wensleydale', 'chedder']
    >>> cb[-2:0]
    ['chedder', 'limburger']
    >>> cb[::2]
    ['wensleydale', 'limburger']
    >>> i = iter(cb)
    >>> i.next()
    'wensleydale'
    >>> i.next()
    'chedder'
    >>> i.next()
    'limburger'
    >>> i.next()
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
    StopIteration
    >>> cb[0] = 'gouda'
    >>> str(cb)
    "['gouda', 'chedder', 'limburger']"
    >>> cb[-2:0] = ('mozzarella', 'parmesan')
    >>> str(cb)
    "['gouda', 'mozzarella', 'parmesan']"
    """

    def __init__(self, size, item_factory=lambda: None):
        self._size = size
        self._head = 0
        self._buffer = [item_factory() for n in xrange(size)]

    def __repr__(self):
        return "<CircularBuffer %s: size=%s, head=%s>" % (id(self), self._size, self._head)

    def __str__(self):
        return str(list(self))

    def _absidx(self, n):
        return (self._head + n) % self._size

    def append(self, item):
        """Appends a new element to the buffer.

        The oldest element in the buffer is removed as a side effect.
        """
        self._buffer[self._head] = item
        self._head = self._absidx(1)

    def extend(self, items):
        """Append each element from iterable ``items``."""
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

