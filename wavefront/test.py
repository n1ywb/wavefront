#!/usr/bin/env python

from types import MethodType

from nose.tools import *

from mock import Mock, patch

import gevent

from antelope import brttpkt

from wavefront.controller import Orb

class Dummy(object): pass

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

def make_mock_proc_orb(maxcnt, app, orb):
    count = [0]

    def _mock_proc(self, *args, **kwargs):
        Orb._process(self, *args, **kwargs)
        count[0] += 1
        if count[0] >= maxcnt:
            app.kill()

    orb._process = MethodType(_mock_proc, orb)


def test_app():
    for n in xrange(2):
        brttpkt.get_rvals.appendleft((n, 'foobar', n*5, makepkt(n*5)))

    from wavefront.controller import App

    app = App()
    orb = app.add_orb('anfprelim')
    orb.add_binner('channet_chansta_chanchan_chanloc', twin=10.0, tbin=5.0)
    make_mock_proc_orb(2, app, orb)
    app.start()
    gevent.wait()

    eq_('[(0.0, 5, 0, 3.0, 5), (5.0, 5, 0, 3.0, 5)]',
        str(list(orb.binners.binners['channet_chansta_chanchan_chanloc'].pop().store.itervalues())))

    ok_(app.successful())

if __name__ == '__main__':
    test_app()

