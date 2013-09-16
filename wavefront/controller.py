class TwistedOrbController(object):
    """ Reaps packets from an orb connection, sends samples to the
    bincontroller, and sends updated bins to streaming connections.

    I guess the connections are responsible for filtering out unwanted updates?

    Or do we have some per connection state here WRT what they want to get?
    That seems logical to have here.
    """
    def __init__(self):
        self.reap()

    # IO specific code (eg. twisted vs gevent) should be encapsulated here

    # This smells like twisted
    # reimplement for gevent

    def self.reap(self):
        deferToThread(self.orb.reap, cb=self.on_reap)

    def on_reap(self, srcname, pkt, timestamp, etc):
        samples = pkt.samples
        timestamp = timestamp
        updated = self.bins.update(srcname, timestamp, samples)
        for binner, updated in updated:
            # emit updates
        self.reap()

    # TODO query

class GeventOrbController(object):
    """ Reaps packets from an orb connection, sends samples to the
    bincontroller, and sends updated bins to streaming connections.

    I guess the connections are responsible for filtering out unwanted updates?

    Or do we have some per connection state here WRT what they want to get?
    That seems logical to have here.
    """
    def __init__(self):
        self.reap()

    # IO specific code (eg. twisted vs gevent) should be encapsulated here

    # This smells like twisted
    # reimplement for gevent

    def self.reap(self):
        # make sure this a greenlet
        while True:
            srcname, timestamp, data = self.orb.reap()
            updated = self.bins.update(srcname, timestamp, samples)
            for binner, updated in updated:
                # emit updates

    # TODO query

class AppController(object):
    """Owns Orbs, OrbControllers, Binners, and BinControllers.
    Handles queries from clients."""

