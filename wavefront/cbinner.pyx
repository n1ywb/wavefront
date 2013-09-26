# cython: profile=True

import cython

from contextlib import contextmanager

import sys

from wavefront.ctimebuf cimport TimeUtil


from Queue import Queue, Full

import logging
log = logging.getLogger(__name__)


cdef class Bin:
    cdef public int size
    cdef public double timestamp
    cdef public double max
    cdef public double min
    cdef public double mean 
    cdef public int nsamples

    def __cinit__(self, int size, double timestamp):
        self.size = size
        self.timestamp = timestamp
        self.mean = 0
        self.nsamples = 0

#    cpdef __eq__(self, o):
#        return (self.timestamp, self.max, self.min, self.mean, self.nsamples ==
#                o.timestamp, o.max, o.min, o.mean, o.nsamples)
#
#    cpdef __ne__(self, o):
#        return not (self == o)
#
    cpdef add(self, double ts, val):
        if self.nsamples >= self.size:
            sys.stderr.write("Warning: Bin overflow; probable duplicate data\n")
        if self.nsamples == 0:
            self.max = val
            self.min = val
        else:
            self.max = max(self.max, val)
            self.min = min(self.min, val)
        self.mean += val / self.size
        self.nsamples += 1

    def __repr__(self):
        return str((self.timestamp, self.max, self.min, self.mean,
                        self.nsamples))

    cpdef asdict(self):
        return dict(
            timestamp=self.timestamp,
            max=self.max,
            min=self.min,
            mean=self.mean,
            nsamples=self.nsamples)


class Binner(TimeUtil):
    def __init__(self, srcname, twin, tbin, store):
        """
        binsize = 1 / samprate * timebuf.tbin
        """
        # won't know this until after we get the first packet
        # don't need to know it until update
        self.srcname = srcname
        self.twin = twin
        self.tbin = tbin
        self.store = store
        self.previous = None
        self.element_time = tbin
        self._queues = set()

    def update(self, double root_ts, samples, double samprate):
        """Update bins from samples, return set of updated bins."""
        cdef int sampnum
        cdef double ts
        cdef Bin current
        cdef Bin previous
        cdef object val
        cdef object store
        cdef int binsize
        cdef double floored

        assert samprate != 0.0
        store = self.store
        # TODO take sample block instead of ts/sample pairs
        # TODO filter out stale samples
        # Something like this (but maybe more efficient)
        #for ts, val in samples:
        #    if ts >= self.timebuf.tail_time:
        #        updated = self.binner.update(((ts,val),))
        binsize = int(self.tbin * samprate)
        updated = []
        for sampnum in xrange(len(samples)):
            val = samples[sampnum]
            with cython.cdivision(True):
                ts = root_ts + 1.0/samprate * sampnum
            current = store.get(ts)
            if current is None:
                floored = (<TimeUtil>self).floor(ts)
                current = Bin.__new__(Bin, floored, binsize)
            current.add(ts, val)
            store.update(ts, current)
            previous = self.previous
            if previous is None:
                self.previous = current
                previous = self.previous
            if current.nsamples == binsize:
                updated.append(current)
            elif (previous.timestamp != current.timestamp and
                  previous.nsamples < binsize):
                updated.append(previous)
            self.previous = current
        self._publish(updated)

    def _publish(self, obj):
        for queue in self._queues:
            try:
                queue.put(obj, block=False)
            except Full:
                log.warning("queue overflow")
                # todo disconnect slow client

    @contextmanager
    def subscription(self, queue):
        """Subscribe queue

        :param queue: The queue to which you would like packets to be published
        :type queue: Instance of ``Queue`` or compatible

        Example::

            queue = Queue()
            with publisher.subscription(queue):
                while True:
                    pickledpacket = queue.get()
                    ...
        """
        self._queues.add(queue)
        try:
            yield
        finally:
            # Stop publishing
            self._queues.remove(queue)



