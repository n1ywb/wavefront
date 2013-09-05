#!/usr/bin/env python

from Queue import Queue

class Bin(object):
    __slots__ = 'timestamp', 'max', 'min', 'mean', 'nsamples'
    def __init__(self, timestamp=None, max=None, min=None, mean=None, nsamples=0):
        self.timestamp = timestamp
        self.max = max
        self.min = min
        self.mean = mean
        self.nsamples = nsamples

    def __eq__(self, o):
        return (self.timestamp, self.max, self.min, self.mean, self.nsamples ==
                o.timestamp, o.max, o.min, o.mean, o.nsamples)

    def __ne__(self, o):
        return not (self == o)

class Binner(object):
    def __init__(self, nsamples, timebuf):
        """
        nsamples = 1 / samprate * timebuf.element_time
        """
        self.timebuf = timebuf
        self.nsamples = nsamples
        self.previous = None

    def update(self, samples):
        # How do we signal when a bin should be sent to clients? It could be
        # full, or it could be partial if we get out of order data
        for ts, val in samples:
            # If the bin is full or we have data that falls outside it (if
            # it's full and the data doesn't fall outside it, that's probably
            # duplicate data.)

            # old data may not be buffered, but it may be binned and or
            # streamed and or cached
            if ts < self.timebuf.tail_time:
                continue

            current = self.timebuf.get(ts)

            if current is None:
                # new current
                current = Bin(timestamp=ts, max=val, min=val, mean=val, nsamples=1)
            else:
                current.max = max(current.max, val)
                current.min = min(current.min, val)
                current.mean = (
                    (current.mean / nsamples) +
                        (val / (totsamples - nsamples)))
                current.nsamples += 1

            if current.nsamples > self.nsamples:
                sys.stderr.write("Warning: Bin overflow; probable duplicate data\n")

            # Maybe the timebuf could self-publish updates?
            # I think I already wrote some sort of update publishing dict
            # Or maybe it makes more sense to emit bin updates and let timebuf
            # subscribe
            # what about custom binning and datascope?
            # maybe best to fully decouple from timebuf. caller should supply a
            # method for retreiving partial bins (maybe .get?) and update can
            # just return a list of changed bins
            self.timebuf.update(((current.timestamp, current),))
            if self.previous is not current:
                #self._publish(current)
                self.previous = current

    def subscribe(self):
        """Returns subscription context"""
        def context():
            try:
                q = Queue()
                yield q
            finally:
                # expunge queue
                # I think I wrote some code for this in antelope_port_agent?
                del q

    def _publish(self):
        """Publish bin to subscribers"""
        pass

