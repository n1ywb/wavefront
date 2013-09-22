#!/usr/bin/env python

from types import MethodType

from nose.tools import *

from mock import Mock, patch

import gevent

from antelope import brttpkt

from wavefront.controller import Orb

def test_app():
    class Dummy(object): pass

    count = [0,0]

    def makepkt(time):
        pkt = Dummy()
        srcname = Dummy()
        srcname.net = 'pktnet'
        srcname.sta = 'pktsta'
        srcname.chan = 'pktchan'
        srcname.loc = 'pktloc'
        srcname.suffix = 'pktsuffix'
        srcname.subcode = 'pktsubcode'
        pkt.srcname = srcname
        channel = Dummy()
        channel.data = [1,2,3,4,5]
        channel.samprate = 1
        channel.chan = 'chanchan'
        channel.loc = 'chanloc'
        channel.net = 'channet'
        channel.sta = 'chansta'
        channel.time = time
        pkt.channels = [channel]
        return pkt

    for n in xrange(2):
        brttpkt.get_rvals.appendleft((n, 'foobar', n*5, makepkt(n*5)))

    from wavefront.controller import App

    app = App()

    def _mock_proc(self, *args, **kwargs):
        Orb._process(self, *args, **kwargs)
        count[0] += 1
        if count[0] == 2:
            app.kill()

    orb = app.add_orb('anfprelim')
    orb._process = MethodType(_mock_proc, orb)

    orb.add_binner('channet_chansta_chanchan_chanloc', twin=10.0, tbin=5.0)
    app.start()
    gevent.wait()

    eq_('[(0.0, 5, 0, 3.0, 5), (5.0, 5, 0, 3.0, 5)]',
        str(list(orb.binners.binners['channet_chansta_chanchan_chanloc'].pop().store.itervalues())))

    ok_(app.successful())

if __name__ == '__main__':
    test_app()

