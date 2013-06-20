Design Documentation
====================

Orb WF Packet Sequence
----------------------

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
-------------------------------------

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
--------------------------------------

.. uml::
	title Asynchronous User Agent Query Sequence

	actor UserAgent
	boundary WSConn
	control DataController
	entity Subscription

	UserAgent -> WSConn: open

	UserAgent ->> WSConn: stream(history=6)
	activate WSConn

	WSConn -> DataController: subscribe
	activate DataController
	DataController->Subscription: subscribe(WSConn)
	deactivate DataController
	activate Subscription

	WSConn ->> DataController: query(t - 6, t)
	activate DataController
	DataController ->> WSConn : response data(T - 0)

	WSConn ->> UserAgent: data(T - 0)

	DataController ->> WSConn : response data(T - 1)

	WSConn ->> UserAgent: data(T - 1)

	Subscription ->> WSConn: data(T + 1)

	WSConn ->> UserAgent: data(T + 1)


	DataController ->> WSConn : response data(T - 2)

	WSConn ->> UserAgent: data(T - 2)

	Subscription ->> WSConn: data(T + 2)

	WSConn ->> UserAgent: data(T + 2)

	DataController ->> WSConn : response data(T - 3)

	WSConn ->> UserAgent: data(T - 3)

	DataController ->> WSConn : response data(T - 4)

	WSConn ->> UserAgent: data(T - 4)

	DataController ->> WSConn : response data(T - 5)

	WSConn ->> UserAgent: data(T - 5)

	Subscription ->> WSConn: data(T + 3)

	WSConn ->> UserAgent: data(T + 3)


	Subscription ->> WSConn: data(T + 4)

	WSConn ->> UserAgent: data(T + 4)


	UserAgent ->> WSConn: close

	WSConn -> DataController: unsubscribe
	destroy WSConn
	activate DataController
	DataController -> Subscription: unsubscribe(WSConn)
	deactivate DataController
	destroy Subscription


(Note: sphinxcontrib-plantuml is required to render UML.)

