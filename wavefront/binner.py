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
        updated = set()
        for ts, val in samples:
            # If the bin is full or we have data that falls outside it (if
            # it's full and the data doesn't fall outside it, that's probably
            # duplicate data.)
            current = self.store.get(ts)
            if current is None:
                current = Bin(timestamp=self.floor(ts), size=self.binsize)
            current.add((ts, val))
            self.store[ts] = current
            if self.previous is None:
                self.previous = current
            if self.previous.timestamp != current.timestamp:
                updated.add(self.previous)
            if self.previous.nsamples == self.binsize:
                updated.add(self.previous)
            self.previous = current
        return updated

