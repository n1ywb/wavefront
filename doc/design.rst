Design Documentation
====================

Definitions
-----------

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
#. Clients may query previously received WF data.
#. Asyncronous clients may request continuous real time streaming data.
#. It should be possible to query data which was previously received from an orb
   but which is not yet available in Datascope.

Discussion
++++++++++

We want to implement a back end system which will facilitate the development of
web applications useful for querying historical waveform data and monitoring WF
data in real time, like orbmonrtd.

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


Implementation
--------------

#. Receive and cache a configurable amount of streaming waveform data from orbs.
#. On query, look for orb data first, then retrieve and cache waveform data from datascope databases as needed.
#. Cached orb data has a higher priority than cached DB data
#. Use memcache for caching
    #. Cache contents survive program restarts
    #. Cache can be distributed accross multiple machines
    #. If cache contents are lost, e.g. due a system reboot, previously
       recieved orb data which is not yet present in datascope may be lost.
       This is unavoidable without journaling to disk or something, and is an
       acceptable compromise. This should be an infrequent ocurrance and data
       will be eventually available from datascope in any event.
    #. Because memcache has no priorities, use seperate instances of memcached for Orb and DB caches.
#. Client functions:
    #. query(Tstart, Tend)
        #. return all immediately available waveform data for window
        #. optionally stream newly received data which was acquired in the window but delayed (this only makes sense for async clients)
    #. monitor(Tstart, Tend, history=False)
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

