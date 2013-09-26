# cython: profile=True

from contextlib import contextmanager

import sys

from wavefront.ctimebuf import TimeUtil


from Queue import Queue, Full

import logging
log = logging.getLogger(__name__)


cdef class Bin(object):
    cdef public int size
    cdef public double timestamp
    cdef public double max
    cdef public double min
    cdef public double mean 
    cdef public int nsamples

    def __init__(self, size, timestamp):
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
    cpdef add(self, sample):
        if self.nsamples >= self.size:
            sys.stderr.write("Warning: Bin overflow; probable duplicate data\n")
        ts, val = sample
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
        cdef int sampnum
        cdef double ts
        cdef Bin current
        """Update bins from samples, return set of updated bins."""
        # TODO take sample block instead of ts/sample pairs
        # TODO filter out stale samples
        # Something like this (but maybe more efficient)
        #for ts, val in samples:
        #    if ts >= self.timebuf.tail_time:
        #        updated = self.binner.update(((ts,val),))
        binsize = self.tbin * samprate
        updated = []
        for sampnum in xrange(len(samples)):
            val = samples[sampnum]
            ts = root_ts + 1.0/samprate * sampnum
            current = self.store.get(ts)
            if current is None:
                current = Bin(timestamp=self.floor(ts), size=binsize)
            current.add((ts, val))
            self.store.update(ts, current)
            if self.previous is None:
                self.previous = current
            if current.nsamples == binsize:
                updated.append(current)
            elif (self.previous.timestamp != current.timestamp and
                  self.previous.nsamples < binsize):
                updated.append(self.previous)
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



