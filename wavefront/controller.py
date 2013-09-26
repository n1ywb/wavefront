#!/usr/bin/env python
"""
Gevent based orb packet publisher.

Correct use of this module requires the `ANTELOPE_PYTHON_GILRELEASE`
environment variable to be set, to signal the Antelope Python bindings to
release the GIL when entering Antelope C functions. E.g.

    export ANTELOPE_PYTHON_GILRELEASE=1

"""

class GilReleaseNotSetError(Exception): pass

import os

if 'ANTELOPE_PYTHON_GILRELEASE' not in os.environ:
    raise GilReleaseNotSetError("ANTELOPE_PYTHON_GILRELEASE not in environment")


import atexit

from gevent import Greenlet, sleep
from gevent.threadpool import ThreadPool, wrap_errors

from antelope.brttpkt import OrbreapThr, Timeout, NoData
from antelope.Pkt import Packet

import logging

from datetime import datetime

from wavefront.cbinner import Binner, Bin
from wavefront.ctimebuf import TimeBuffer

log = logging.getLogger(__name__)

from collections import defaultdict


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
        self.binners = defaultdict(set)

    def add_binner(self, srcname, twin, tbin):
        """Add a new bin matching srcname, with size twin and tbin"""
        # is binsize given in samples or seconds?
        # print 'add_binner', srcname, twin, tbin
        timebuf = TimeBuffer(int(twin / tbin), 0, tbin)
        self.binners[srcname].add(Binner(srcname, twin, tbin, timebuf))
        # print self.binners[srcname]

    def get_binner(self, srcname, twin, tbin):
        for binner in self.binners[srcname]:
            if (binner.twin, binner.tbin) == (twin, tbin):
                return binner
        return None

    # TODO
    # def rm_binner
    # must be possible to remove stale ones later when we do regex matching

    # TODO
    # def query(self, srcname, binsize, tstart, tend):
    #    timebuf = self.binners[srcname].timebuf
    # Need this to support pre-filling the wf display, not just for unified
    # query API.

    def update(self, srcname, ts, samples, samprate):
        """Given some new data, dispatch it to the appropriate binners.

        Return set of updated bins.
        """

        # send to all binners; let binners filter out any stale data
        # todo: support dynamically creating new binners based on regex
        # srcnames

        for binner in self.binners[srcname]:
            binner.update(ts, samples, samprate)

now = datetime.utcnow()

npkts = 0
def _():
    then = datetime.utcnow()
    d = then - now
    print "Processed %s pkts in %s seconds at %s/sec" % (npkts,
    d.total_seconds() - 10,
                                            float(npkts) / (d.total_seconds() -
                                            10))
atexit.register(_)

class Orb(Greenlet):
    """
    Reaps packets from an orb connection, sends samples to the
    bincontroller, and sends updated bins to streaming connections.

    Gets packets from an orbreap thread in a non-blocking fashion using the
    gevent threadpool functionality, and publishes them to subscribers.

    I guess the connections are responsible for filtering out unwanted updates?

    Or do we have some per connection state here WRT what they want to get?
    That seems logical to have here.
    """

    def __init__(self, orbname, select=None, reject=None, tafter=None):
        super(Orb, self).__init__()
        self.binners = BinController()
        self.orbname = orbname
        self.select = select
        self.reject = reject
        self.tafter = tafter

    def add_binner(self, srcname, twin, tbin):
        self.binners.add_binner(srcname, twin, tbin)

    def _process(self, value, timestamp):
        global npkts
        npkts += 1
        pktid, srcname, orbtimestamp, raw_packet = value
        log.debug("Processing packet %s %s %s" % (pktid, srcname, orbtimestamp))
        packet = Packet(srcname, orbtimestamp, raw_packet)

        for channel in packet.channels:
            # print channel
            parts = [channel.net, channel.sta, channel.chan]
            if channel.loc is not '':
                    parts.append(channel.loc)
            srcname = '_'.join(parts)
            log.debug("srcname %s" % (srcname))
            self.binners.update(srcname, channel.time,
                                          channel.data, channel.samprate)

    def _run(self):
        """Main loop; reap and process pkts"""
        try:
            args = self.orbname, self.select, self.reject
            with OrbreapThr(*args, timeout=1, queuesize=8, after=self.tafter) as orbreapthr:
                log.info("Connected to ORB %s %s %s" % (self.orbname, self.select,
                                                        self.reject))
                threadpool = ThreadPool(maxsize=1)
                try:
                    while True:
                        try:
                            success, value = threadpool.spawn(
                                    wrap_errors, (Exception,), orbreapthr.get, [], {}).get()
                            timestamp = datetime.utcnow()
                            if not success:
                                raise value
                        except (Timeout, NoData), e:
                            log.debug("orbreapthr.get exception %r" % type(e))
                            pass
                        else:
                            if value is None:
                                raise Exception('Nothing to publish')
                            self._process(value, timestamp)
                finally:
                    # This blocks until all threads in the pool return. That's
                    # critical; if the orbreapthr dies before the get thread,
                    # segfaults ensue.
                    threadpool.kill()
        except Exception, e:
            log.error("OrbPktSrc terminating due to exception", exc_info=True)
            raise
        finally:
            log.info("Disconnected from ORB %s %s %s" % (self.orbname, self.select,
                                                         self.reject))


class App(Greenlet):
    """Owns Orbs, OrbControllers, Binners, and BinControllers.
    Handles queries from clients."""

    def __init__(self):
        super(App, self).__init__()
        self.orbs = set()

    def add_orb(self, *args, **kwargs):
        orb = Orb(*args, **kwargs)
        orb.link_exception(self._janitor)
        self.orbs.add(orb)
        return orb

    def _janitor(self, src):
        log.debug("Janitor, cleanup aisle 12")
        self.kill(src.exception)

    def _run(self):
        try:
            [orb.start() for orb in self.orbs]
            while True: sleep(10000)
        finally:
            [orb.kill() for orb in self.orbs]

