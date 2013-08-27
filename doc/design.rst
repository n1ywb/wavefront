Design Documentation
====================

Definitions
-----------

binsize
    The number of samples per bin.

Window
    The time period of interest as specified by the client. Tstart and Tend may
    be specified in or absolute terms, or relative to Tnow.

Tstart
    Start time of window.

Tend
    End time of window.

Tnow
    The current time as of when Tnow is evaluated by the program.

DB
    Antelope Datascope database

ORB
    Antelope Object Ring Buffer

WF
    Waveform

history
    Keyword argument to monitor function. If True, return all immediately
    available data for the specified window.

subscribe
    Keyword argument to QueryController constructor and query client function.
    If true, subscribe to Orb publisher.

query
    Keyword argument to QueryController constructor. If true, query all
    immediately available data for window.

advance
    Keyword argument to QueryController constructor. If true, window moves
    forward in real time.

Requirements
------------

The program shall provide the following features:

#. Make waveform data available to web clients on demand.
#. Abstract data sources; clients see a single unified data set.
#. Data sources include Antelope Orbs and Datascope databases.
#. Ability to filter data prior to ingestion based on configurable criteria.
#. Clients may query previously received WF data.
#. Clients may request raw data or data reduced via max/min/median binning.
#. Asyncronous clients may request continuous real time streaming data.
#. It should be possible to query data which was previously received from an orb
   but which is not yet available in Datascope.

Use Cases
+++++++++

We want to implement a back end system which will facilitate the development of
browser-based applications useful for querying historical waveform data and
monitoring WF data in real time.

orbmonrtd
^^^^^^^^^

Low resolution data from many instruments updating in real time. Panning within
a limited range and zooming within limited levels should be possible.
Performance sensitive due to real time nature and potentially large number of
instruments being monitored.

Waveform Explorer
^^^^^^^^^^^^^^^^^

The other use case is interactive waveform exploration. Users could look at any
portion of any waveform(s) at any zoom level. Real time performance is less
critical because typically users will be looking at one or a few waveforms in
detail and data will often come from a slow datascope database. Web does not
lend itself to full resolution real time streaming. However we should support
streaming data anyway to support backfilling of missing data which has arrived
out of order.

A special case of the waveform explorer is browsing of predefined queries for
interesting events. It would be nice to make these load quickly.

Discussion
++++++++++

We do not want clients to be concerned with whether data came from an Orb or a
Datascope database or some other source.

We want clients to be able to query data which was received from an Orb but
which has not yet been written to a DB.

Stations transmit WF packets, they are recieved by our Orb, and orb2db writes
them to disk. However there are several caveats:

#. orb2db, etc may buffer WF data for up to 10 minutes before it is written to disk
#. long-lived programs may need to jump through hoops to see new data on disk
#. A stream of packets from a particular station may contain an arbitrary combination of:
    #. in order packets 
    #. out of order packets
    #. timely packets
    #. signficantly delayed packets (hours)

The system must accomodate this behaviour.

Latency of real time data should be minimized.



Implementation
--------------

All raw data is available at all times via orbs or datascope. However, to
service many clients with reasonable latency and server load, it's helpful to
improve data locality by judicious use of caching and buffering.

The system will have access to several different data stores. Queries will look
for data in this order:

#. Circular buffers of real time prebinned data
#. Cache of data with user specified bin sizes not available from RT buffers
#. Orb packet cache
#. Datascope query cache
#. Orb
#. Datascope

The system will continuously reap packets from the orb(s). Packets will be
cached in the orb packet cache as they are read. Samples within the packets
will be binned and stored in the real time-prebinned circular buffers. This
will make initial loading, panning and zooming within the buffer ranges and
binsizes very fast.

On startup the system shall play back the orb data to rebuild the prebinned
buffers. It may also periodically persist the prebinned buffer data to a
private data store to allow for survival accross restarts and reduce startup
time.

The length and binsize of the prebinned buffers shall be configurable.

Samples shall be streamed to clients when they are inserted into the buffer.

In the event of a data gap, the partial bin(s) will be written to the buffer
and streamed to clients.

When old out of order data arrives, the partial bin(s) will be updated in the
buffer and resent to clients.

Each slot in the buffer will store the following data

#. Timestamp
#. Max sample
#. Min sample
#. Mean sample
#. Number of samples

Number of samples permits updating partial bins when new data arrives. It
also offers some protection against duplicate data by making overflows
detectable.

When the system fufills a user query by reading data from an orb, the read data
shall be cached in the orb packet cache. This may cause recently recieved data
to be pushed out. This will not affect orbmonrtd users, however, because they
will primarily be looking at data in the prebinned buffers; it will only affect
other interactive waveform users looking at raw or custom binned data. The data
is not lost in any event, as it may be reread from the orb as needed.

However ANF Orb servers have large amounts of RAM and orb files
are memory mapped and most orb data is paged in most of the time, so most
queries do not go to disk. Even so, because Orb data comes over a socket from
an orb server, which is a seperate machine from the web server, some caching of
orb packets seems important for performance.

When a query is fufilled by reading from datascope, the read data shall be
cached in the datascope query cache.

Using a seperate cache for orb data vs datascope data prevents the continuous
flow of incoming real time packets from quickly displacing all cached datascope
data.

When a query is fufilled by binning data, the resultant binned data shall be
cached in the user specified binned data cache. Using a seperate cache for
binned data vs the raw data read from the orb or datascope has important
performance implications. The amount of raw data required to fufill a request
for binned data could be orders of magnitude larger than the resultant binned
data. Thus if they shared a cache, binned data would almost always be pushed
out to make room for raw data, completely eliminating the benefit of caching
the binned data.

Because data is written to datascope outside of this system, it's possible that
cached datascope query results could become stale due to a datascope update.
Unfortunately it does not seem that there is any way for the datascope writers
to notify this system when writes occur. A mechanism to expire stale results
from the cache is therefor necessary. It could be time based, or it could be
based on polling for changes to the wfdisc table.

Handling out of order data within the prebinned streaming system is easy. If
any of the partial bins are still in the buffers, update and stream them, done.

Handling out of order data with queries is more challanging. When the OOO data
arrives, we must first check if it falls within any current query windows. If
so, then we must reduce and stream it appropriately. The end-bins will probably
be partial, but that's OK, the client can take responsibility for combining
them. The server could do the combination but it would have to re-query the
adjascent data.

#. Receive, reduce, and buffer a configurable amount of streaming waveform data from orbs.
#. Use memcache for caching query results and binning results
    #. Cache contents survive program restarts
    #. Cache can be distributed accross multiple machines
    #. If cache contents are lost, e.g. due a system reboot, previously
       recieved orb data which is not yet present in datascope may be lost.
       This is unavoidable without journaling to disk or something, and is an
       acceptable compromise. This should be an infrequent ocurrance and data
       will be eventually available from datascope in any event.
    #. Because memcache has no priorities, use seperate instances of memcached for Orb and DB caches.
#. Client functions:
    #. query(Tstart, Tend, binsize, accept, reject)
        #. return all immediately available waveform data for window
        #. optionally stream newly received data which was acquired in the window but delayed (this only makes sense for async clients)
    #. monitor(Tstart, Tend, binsize, accept, reject, history=False)
        #. Stream live waveform data from the orb as it arrives (this only makes sense for async clients)
        #. Window from [Tstart:Tend]; packets with timestamps outside the window
           are not sent to client regardless of when they arrive.
        #. Tstart should be some time in the past, say 10 minutes.
        #. Tend should be some time in the future, say 10 minutes (set this
           inversely proportional to how much you trust your stations to accurately
           set their clocks and how annoyed you would be to have packets
           timestamped in the distant future streaming in.) If None, accept all
           packets with T >= Tstart.
        #. Window moves forward in real time.
        #. If history is True, immediately query and return all currently available
           data within the window as of Tnow. Otherwise data is only sent as it
           arrives from the orb.
    #. cancel(): stop the current operation, stream no more data


Orb WF Packet Sequence
++++++++++++++++++++++

.. uml::
	boundary OrbConnection
	control OrbClient
	control DataController
	control Binner
	boundary OrbCache
	entity Subscriptions

	OrbConnection ->> OrbClient: on_get(pkt)
	activate OrbClient
	OrbClient -> OrbClient: raw_data = unstuffPkt(pkt)
	note right
		Is packet actually new, or old OOO?
		Client should specify window of interest.
	end note
	OrbClient -> DataController: proc(raw_data)
	deactivate OrbClient
	activate DataController

	DataController -> Binner: binned_data = bin(raw_data)
	activate Binner
	Binner --> DataController
	deactivate Binner

	DataController -> OrbCache: set(binned_data)
	activate OrbCache
	deactivate OrbCache

	DataController -> Subscriptions: send(binned_data)
	deactivate DataController
	  activate Subscriptions
	Subscriptions -> Subscriptions: publish
	deactivate Subscriptions



Data Controller Query Sequence
++++++++++++++++++++++++++++++

.. uml::
	title Data Controller Query Sequence
	control DataController
	boundary OrbCache
	boundary DBCache
	database Datascope
	control Binner

	[-> DataController: query
	activate DataController

	DataController -> OrbCache: binned_data = query()
	activate OrbCache
	OrbCache --> DataController 
	deactivate OrbCache

	opt binned_data is None
		DataController -> DBCache: binned_data = query()
		activate DBCache
		DBCache --> DataController 
		deactivate DBCache
	end

	opt binned_data is None
		DataController -> Datascope: raw_data = query()
		activate Datascope
		Datascope --> DataController 
		deactivate Datascope
		DataController -> Binner: binned_data = bin(raw_data)
		activate Binner
		Binner --> DataController
		deactivate Binner
		DataController -> DBCache: set(binned_data)
		activate DBCache
		deactivate DBCache
	end

	[<-- DataController: binned_data
	deactivate DataController

		
Asynchronous User Agent Query Sequence
++++++++++++++++++++++++++++++++++++++

.. uml::
	title Asynchronous User Agent Query Sequence

	actor UserAgent
	'boundary WSConnection
	'control DataController
	'control Subscription
        'database Datascope
        'boundary OrbConnection

        create boundary WSConnection
	UserAgent -> WSConnection: open()
	deactivate WSConnection

	UserAgent ->> WSConnection: monitor(Tstart, Tend, history)
	activate WSConnection
        create control QueryController
        WSConnection -> QueryController: new(Tstart, Tend, advance, query, subscribe)
        activate QueryController

        create entity Window
        QueryController -> Window: window = new(Tstart, Tend, advance)
        deactivate Window

        control DataController
        opt subscribe is True
            QueryController -> DataController : subscription = get_subscription(window)
            activate DataController
            create control Subscription
            DataController -> Subscription: new(window)
            deactivate Subscription
            DataController --> QueryController: subscription
            deactivate DataController
        end

        opt query is True
            QueryController -> DataController: query(Window)
            activate DataController
            ref over DataController: Data Controller Query Sequence
            DataController --> QueryController: result_chunk_1
            QueryController -> Window: in_window = window.in_window(result_chunk_1)
            activate Window
            Window --> QueryController: True/False
            deactivate Window
            opt in_window is True
                QueryController --> WSConnection: result_chunk_1
                WSConnection --> UserAgent: result_chunk_1
            end
            ...
            DataController --> QueryController: result_chunk_n
            QueryController -> Window: in_window = window.in_window(result_chunk_n)
            activate Window
            Window --> QueryController: True/False
            deactivate Window
            opt in_window is True
                QueryController --> WSConnection: result_chunk_n
                WSConnection --> UserAgent: result_chunk_n
            end
            deactivate DataController

        end

        deactivate QueryController

        boundary OrbConnection
        OrbConnection -> DataController: on_get(pkt)
        activate DataController
        ref over DataController: Orb WF Packet Sequence
        opt subscribe is True
            DataController -> Subscription: publish(binned_data)
            deactivate DataController
            activate Subscription
            Subscription -> Window: in_window = window.in_window(binned_data)
            activate Window
            Window --> Subscription: True/False
            deactivate Window
            opt in_window
                Subscription -> WSConnection: publish()
                activate WSConnection
                WSConnection -> UserAgent: publish()
                deactivate WSConnection
            end
            deactivate Subscription
        end

        ...

	UserAgent ->> WSConnection: close()
        activate WSConnection
	WSConnection -> QueryController: cancel()
        note right : Should probably have a way to cancel DataController queries in progress.
        activate QueryController
	QueryController -> Subscription: unsubscribe()
        activate Subscription
	destroy Subscription
	QueryController -> Window: del()
        activate Window
        destroy Window
        destroy QueryController
	destroy WSConnection


(Note: sphinxcontrib-plantuml is required to render UML.)

Future Enhancements
-------------------

A future enhancement may be to eargerly pre-load and pre-bin data in the
neighborhood of the user's initial query, in the hopes that it will speed up a
subsequent query. The brute force approach would be to load as much as possible
and bin into as many different binsizes as possible. Heuristics based on actual
usage data may permit optimization.

Bin sizes increasing by powers of 2 (I.e. 2, 4, 8, 16, etc) up to a
configurable maximum would give the system a wide range of bin sizes to select
from. The system could limit the user to these bin sizes, or use them as
starting points to rebin to a custom size, possibly with interpolation.

This creates a high continuous load in exchange for a lower per-request
load. Some fine tuning of bin size steps may find an optimal compromise here.
Maybe fixing it at powers of two isn't such a good idea. A configurable divisor
might make more sense; e.g. 2, 3, 10 maybe. It would take some benchmarking to
determine the ideal value to balance continuous load vs request load.

Such a mechanism would probably require the system to partition cached data
into fixed size chunks. It could require the client to also work with these
chunk sizes or abstract away this detail.  

In the case of giving clients fixed size chunks, the size selection should be
small enough such that clients displaying small windows do not receive much
more data than they need, and large enough such that clients displaying large
windows do not need to request an unnecessarily large number of chunks.

The server would have to use fixed size bins and chunks internally; it's the
only way to make caching work efficiently. Clients may have to do a little bit
more work if they wish to display data in odd chunk sizes or bin sizes, but
this seems like a reasonable compromise between server load and client load.
Even an iPhone should have enough capacity to request one bin size smaller than
it wants to display and then further reduce.


Notes
-----

These are just chicken scratchings. Food for thought. They do not necessarily
reflect the actual application design, although they may influence it.

Data streaming off the orb can only be reduced so far. The maximum reduction
that can be performed on a single packet without looking at data from other
packets is 1 sample per packet. This may still be fairly high resolution for
some data streams. But further real time reduction seems impractical. It would
require access to both past and future data. This could probably be retrieved
from memcache and or datascope but that would add a huge IO load to the server.
Or the server could keep some data in memory but then you have issues at app
initialization and somewhat defeat the purpose of using memcache. 

A reasonable compromise may be to perform further reduction on-the-fly in
response to requests for such data.

So wait a minute; are we going to have memcache buckets with ONE sample? That's
NFG.

There's no way around it; the system is going to have to keep in memory partial
buckets, add data as packets arrive, and flush them to memcache when they are
full.

For higher reduction buckets, latency could become bad. Either the buckets need
to be really small, or we need to support streaming partial buckets.

For really slow rates it seems like a no brainer to stream binned samples to
clients as they are generated. Whether or not the updated partial bucket should
then be flushed to memcache is another story. If they're REALLY slow we could
even drop them from server memory and read from memcache, update, and write
back to memcache.

OOO data presents an interesting issue. Ideally every streaming bin bucket
would be full before flushing to memcache. In reality the first packet may not
arrive on a bucket boundary. Subsequent packets may arrive out of order after
significant delay (or not at all).

To overcome this, partial buckets must be flushed to memcache periodically. If
fill data arrives, these buckets must be read back in, from datascope if
necessary, updated, and rewritten to RT memcache. They should also be expired
from DS memcache to avoid the situtation where the fill data has been written
to datascope but queries are fufilled with the cached partial bucket.

Basically if packet 1 arrives followed by packet 3, packet 2's data must be
marked as unknown in the appropriate buckets and the partial buckets which
packet 2 would have completed must be flushed. 

Major issue with using memcache for RT data. Memcache uses LRU algorithm.
Queries for older data will keep it in the cache at the expense of newer data,
which could be flushed. Because the newer data may not yet be written to
datascope, it will simply disappear from the system. That is not acceptable. 

Instead, for RT data, we will have to use a fixed size FIFO buffer for each
pre-bin level for each instrument.

If we support custom bin levels, then using memcache to cache the custom binned
data might still make sense. When a bucket expires it can still be recreated by
going back to the FIFOs.

This does not affect using memcache for datascope.

There are really two distinct use cases here.

One is a web dlmon. That shows low resolution data from many instruments
updating in real time. We want the page to load quickly so having the data for
the default zoom level pre-binned makes lots of sense. Panning and zooming
around within the range of the RT FIFO is fast b/c it's all in RAM, even if it
has to be rebinned that's relatively cheap.

The other is interactive waveform exploration. Users could look at any portion
of any waveform at any zoom level. Prebinning the data at many levels could
decrease latency but at the cost of greater server complexity and high
continuous load. Going to datascope is expensive. Do we cache raw datascope
results, binned data, or both? If we cache the raw datascope results it will be
faster to recalculate different bins, but the raw data will always hog up
most/all of the cache. In fact it's entirely possible the results of a single
large query could overflow the cache. Then doing the same query we'd miss on
the first chunk, the reload it, forcing out the next chunk, which would then
miss and be reloaded, etc, basically causing cache thrash. That can be avoided
somewhat by serving up all cached data before going to datascope. If we only
cache binned data we have to go to datascope more often. We might need some
sort of multilayered or priority cache; memcache may not be a good fit here. At
least two layers, one for raw data, and one for binned data. A future
enhancement could spool expiring binned chunks to disk instead of just zapping
them.

So the levels of data really are, in lookup order:

#. FIFOs, raw and pre-binned
#. Custom binned data cache
#. Datascope query cache
#. Datascope

The query should supply enough information to determine if the FIFO's contain
the data, and if so, which FIFO to use. If the FIFO's do not contain the data,
then check the custom binned cache, then datascope cache, then query datascope.

Do we permit streaming of custom binned RT data?

Top priority: orbmontrd backend
Neccessary functionality:

#. Streaming
#. Full res?
#. Pre-binned

No caching, no querying, no custom binning, no datascope.

What about if data is not present in the RT system but partial data is present
in datascope and the datascope query cache and then an update arrives? How do
we know when to flush that query from the cache?

Samples flow from orb packets into a raw ring buffer and then into reduced ring buffers

max, min, med, starting T, ending T

compare Tstart Tend to see if it's complete 

be sure to support partials and updates

use pub/sub pattern to chain buffers and pub updates to clients

does chaning buffers make sense, or is that dumb? I think I'm going with dumb. They can all just listen to the RT buffer.

Geoff sez Orb data is mostly in ram anyhow so really no reason to buffer RT
data just get it w orbafter/orbreap. Course this goes over a socket. If the
performance sucks consider buffering afterall.

Wait. orb data comes over a SOCKET. And yeah it's in ram on the orb server,
which isn't necessarily the machine hosting the web app, which means it has to
come over the LAN.

(04:56:10 PM) n1ywb: so then in the future when we support querying backdata, it might be helpful to use a small local memcache on the web server to reduce traffic to the orb server, although that only really helps if people are repeatedly looking at the same data, which might not happen much in practice
(04:57:51 PM) n1ywb: once we have some users and some usage data it should be easy enough to calculate what the benefit would be and that will make it obvious if it's worth implementing or not

(04:39:18 PM) n1ywb: wait a minute
(04:39:37 PM) n1ywb: orb data is in ram, on the orb server, which isn't necessarily the machine which is going to run the web service, and so the data has to come over the lan, right?
(04:40:54 PM) n1ywb: that's wicked slow
(04:44:51 PM) n1ywb: i mean, it might be a fast lan, but it's still orders of magnitude slower than having it in local ram on the web server
(04:45:13 PM) n1ywb: i guess memcached would have that issue too, except it could be run locally on the web server
(04:47:41 PM) piratepork: Correct on all counts. Plus the data in memcached is already set up for consumption
(04:48:07 PM) n1ywb: does orbmonrtd even let you see full res data right now?
(04:48:15 PM) n1ywb: or is it always reduced?
(04:48:31 PM) piratepork: Always reduced
(04:48:57 PM) piratepork: It does a rolling pixmap
(04:49:00 PM) n1ywb: k so maybe we don't need to push full res data over weborbmonrtd anyway, then it's a non issue, no need to keep any more full res data in ram then is necessary to fill the next bin
(04:49:19 PM) piratepork: Can't resize traces dynamically
(04:49:34 PM) n1ywb: hm?
(04:49:52 PM) piratepork: Orbmonrtd can't
(04:50:03 PM) n1ywb: ok
(04:50:22 PM) piratepork: Sorry on phone on a bus so brevity is the rule for a bit
(04:50:31 PM) n1ywb: np
(04:56:10 PM) n1ywb: so then in the future when we support querying backdata, it might be helpful to use a small local memcache on the web server to reduce traffic to the orb server, although that only really helps if people are repeatedly looking at the same data, which might not happen much in practice
(04:57:51 PM) n1ywb: once we have some users and some usage data it should be easy enough to calculate what the benefit would be and that will make it obvious if it's worth implementing or not

It almost feels like streaming and querying are two seperate services. The only streamy thing about querying would be live backfills.

Feature roadmap

1. Stream pre-binned real time WF data, enough to facility weborbmonrtd
2. Query data from orb
3. Query data from datascope with simple caching
4. Performance analysis and advanced caching


