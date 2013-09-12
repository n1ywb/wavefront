#!/usr/bin/env python

from wavefront.timebuf import TimeUtil

from Queue import Queue

class Bin(object):
    def __init__(self, size, timestamp):
        self.size = size
        self.timestamp = timestamp
        self.max = 0
        self.min = 0
        self.mean = 0
        self.nsamples = 0

    def __eq__(self, o):
        return (self.timestamp, self.max, self.min, self.mean, self.nsamples ==
                o.timestamp, o.max, o.min, o.mean, o.nsamples)

    def __ne__(self, o):
        return not (self == o)

    def add(self, sample):
        if self.nsamples >= self.size:
            sys.stderr.write("Warning: Bin overflow; probable duplicate data\n")
        ts, val = sample
        self.max = max(self.max, val)
        self.min = min(self.min, val)
        self.mean += val / self.size
        self.nsamples += 1


class Binner(TimeUtil):
    def __init__(self, binsize, element_time, store):
        """
        binsize = 1 / samprate * timebuf.element_time
        """
        self.binsize = binsize
        self.element_time = element_time
        self.store = store
        self.previous = None

    def update(self, samples):
        """Update bins from samples, return set of updated bins."""
        # TODO take sample block instead of ts/sample pairs
        # TODO filter out stale samples
        # Something like this (but maybe more efficient)
        #for ts, val in samples:
        #    if ts >= self.timebuf.tail_time:
        #        updated = self.binner.update(((ts,val),))

        updated = set()
        for ts, val in samples:
            current = self.store.get(ts)
            if current is None:
                current = Bin(timestamp=self.floor(ts), size=self.binsize)
            current.add((ts, val))
            self.store.update([(ts, current),])
            if self.previous is None:
                self.previous = current
            if current.nsamples == self.binsize:
                updated.add(current)
            elif self.previous.timestamp != current.timestamp and
                self.previous.nsamples < self.binsize:
                updated.add(self.previous)
            self.previous = current
        return updated

class BinController(object):
    """Receives packets from exactly one ORB, dispatches them to binners,
    returns updated bins

    you could probably use it for multiple orbs if you can guarantee that each
    orb has a unique set of source names; i.e. the same srcname does not appear
    on both orbs.

    how to configure binners?
    """

    # what kind of store for the binners that's aren't preconfigured
    # for streaming?
    # I guess it will be memcache based.
    # Probably need a different bin controller class for that

    def __init__(self):
        self.binners = {}

    def add_binner(self, srcname, twin, binsize, samprate):
        """Add a new bin matching srcname, with size twin and binsize"""
        # is binsize given in samples or seconds?
        timebuf = TimeBuffer(twin, binsize, ...)
        self.binners[srcname] = (Binner(timebuf, ...), timebuf, samprate)

    # TODO
    # def rm_binner
    # must be possible to remove stale ones later when we do regex matching

    # TODO
    # def query(self, srcname, binsize, tstart, tend):
    #    timebuf = self.binners[srcname].timebuf
    # Need this to support pre-filling the wf display, not just for unified
    # query API.

    def update(self, srcname, ts, samples):
        """Given some new data, dispatch it to the appropriate binners.

        Return set of updated bins.
        """

        # send to all binners; let binners filter out any stale data
        # todo: support dynamically creating new binners based on regex
        # srcnames

        updates = []
        for binner in self.binners[srcname]:
            updates.append(binner, binner.update(ts, samples))
        return updates


