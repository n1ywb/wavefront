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


from gevent import Greenlet, sleep
from gevent.threadpool import ThreadPool, wrap_errors

from antelope.brttpkt import OrbreapThr, Timeout, NoData
from antelope.Pkt import Packet

import logging

from datetime import datetime

from wavefront.binner import BinController

log = logging.getLogger('wavefront.orbpktsrc')


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

    def __init__(self, orbname, callback, select=None, reject=None):
        super(Orb, self).__init__()
        self.callback = callback
        self.binners = BinController()
        self.orbname = orbname
        self.select = select
        self.reject = reject

    def add_binner(self, srcname, twin, tbin):
        self.binners.add_binner(srcname, twin, tbin)

    def _process(self, value, timestamp):
        pktid, srcname, orbtimestamp, raw_packet = value
        packet = Packet(srcname, orbtimestamp, raw_packet)

        for channel in packet.channels:
            # print channel
            srcname = '_'.join((channel.net, channel.sta, channel.chan, channel.loc))
            updated = self.binners.update(srcname, channel.time,
                                          channel.data, channel.samprate)
            # print updated
            #for binner, updates in updated:
            for update in updated:
                # emit updates
                self.callback(update)

    def _run(self):
        """Main loop; reap and process pkts"""
        try:
            args = self.orbname, self.select, self.reject
            with OrbreapThr(*args, timeout=1, queuesize=8) as orbreapthr:
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

