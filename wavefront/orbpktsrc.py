#!/usr/bin/env python
"""
Gevent based orb packet publisher.

Correct use of this module requires the `ANTELOPE_PYTHON_GILRELEASE`
environment variable to be set, to signal the Antelope Python bindings to
release the GIL when entering Antelope C functions. E.g.

    export ANTELOPE_PYTHON_GILRELEASE=1

"""

from contextlib import contextmanager
from cPickle import dumps
import os

from gevent import Greenlet
from gevent.threadpool import ThreadPool, wrap_errors
from gevent.queue import Queue, Empty, Full

from antelope.brttpkt import OrbreapThr, Timeout, NoData
from antelope.Pkt import Packet

import logging

from datetime import datetime


if 'ANTELOPE_PYTHON_GILRELEASE' not in os.environ:
    raise GilReleaseNotSetError("ANTELOPE_PYTHON_GILRELEASE not in environment")


log = logging.getLogger('wavefront.orbpktsrc')


class GilReleaseNotSetError(Exception): pass


class OrbPktSrc(Greenlet):
    """Gevent based orb packet publisher.

    :param transformation: Optional transformation function
    :type transformation: `func`

    Gets packets from an orbreap thread in a non-blocking fashion using the
    gevent threadpool functionality, and publishes them to subscribers.

    The transformation function should take a single argument, the unstuffed Packet
    object. It's return value is placed into the queue.

    Transformation function example::

        from pickle import dumps

        def transform(packet):
            return dumps(packet)

    """
    def __init__(self, orbname, select=None, reject=None, transformation=None,
                    orbreapthr_queuesize=8, block_on_full=True):
        Greenlet.__init__(self)
        self.orbname = orbname
        self.select = select
        self.reject = reject
        self.transformation = transformation
        self.orbreapthr_queuesize=orbreapthr_queuesize
        self.block_on_full=block_on_full
        self._queues = set()

    def _run(self):
        try:
            args = self.orbname, self.select, self.reject
            # TODO Review this queue size
            # TODO Review reasoning behind using OrbreapThr vs. normal ORB API
            # I think it had something to do with orb.reap() blocking forever
            # on comms failures; maybe we could create our own orbreapthr
            # implementation?
            with OrbreapThr(*args, timeout=1, queuesize=orbreapthr_queuesize) as orbreapthr:
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
                            self._publish(value, timestamp)
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

    def _publish(self, r, timestamp):
        pktid, srcname, orbtimestamp, raw_packet = r
        packet = Packet(srcname, orbtimestamp, raw_packet)
        if self.transformation is not None:
            packet = self.transformation(packet)
        for queue in self._queues:
            try:
                queue.put((packet, timestamp), block=self.block_on_full)
            except Full:
                log.debug("queue overflow")

    @contextmanager
    def subscription(self, queue):
        """This context manager returns a Queue object from which the
        subscriber can get pickled orb packets.

        :param queue: The queue to which you would like packets to be published
        :type queue: Instance of ``Queue`` or compatible

        Example::

            queue = Queue()
            with orbpktsrc.subscription(queue):
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

