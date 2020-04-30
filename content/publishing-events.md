Title: Publishing events in distributed applications. Obligations of publishers.
Category: TODO
Date: 2020-4-30
Tags: TODO


# Publishing events in distributed applications. Obligations of publishers.

Exposing state via "state change" events stream is well known and used pattern distributed systems. We all have reasons to do it in our systems. Scope of the article - discuss our obligations as event publishers and how to fulfill them.

## Recap

Let's quickly remind ourselves about event-sourcing and why we care.

### What is event-sourcing?

EventSourcing (ES) is when your "Source of Truth" (SoT) stored not as a snapshot of a state but as a series of events, describing state transitions.

ES is not when:
1. You stream your SoT events.
1. You apply CQRS pattern.

Bottom line - if your persistence level stores state of an entity as a series of events describing what happed with the entity in the past - that's EventSourced entity. Event streaming and CQRS usually comes together with ES, but have nothing to do with ES per se _and possible without ES_.


### Are these events all the time SoT events?

Events streamed do not have to be SoT events. That's why we could publish events without our persistence level being EventSourced.


## Obligations of publishers

To provide downstream services consistent state publishers have to fulfill obligations:

1. **No deviation from SoT**. Published Events must be all the time consistent with SoT state.
1. **Guarantee of publication**. Once entity state is changed - respective event _must_ be eventually published,
1. **No publication until the new state persisted**. No events should be seen before they are persisted in the SoT database. If it's not persisted, then it's not happened yet. Always think of "What if it crashes split second before I persist?"


Bonus - that is not obligations of publishers:
1. Providing downstream services historical events - it's up to readers to persist your events and go back in time if they need/want to.
1. Providing downstream services projections of events aggregation - it's up to readers to build and maintain their projections/read models.


# No deviation from SoT

## Problem

It should all the time be possible to reconstruct state from events we publish, and this reconstructed state must not conflict with SoT.

Of course, downstream services may fail while building their view of state from events we publish, but we must ensure we are not messing up on our side.

## Solutions

Make your state event-sourced and stream SoT events directly. In this case, your published events would be consistent with state by definition - they are the state.

Or, _Publish entire state on its every modification_. That's easy, so we assume we have to stream events due to reasons (say, our state is "big") and continue our discussion ignoring this option.

If you do not want to expose your SoT in both cases - stick in stateless transformer between message bus and SoT events.

# Guarantee of publication

## Problem

Once a state of entity changed, and this change persisted in your SoT persistence level, the corresponding event has to be eventually published. That's your obligation. Projections of your state in downstream services would be corrupted unless this guarantee is satisfied, thus:

1. "At most once" guarantee on event publication is not enough. Theoretically this is possible, but implies many complications for the missing event corrections, and does not worth to be considered as an option.
1. "At least once" guarantee is enough. It's not hard for downstream to filter out duplicates if you attach unique sequence numbers to events.
1. "Exactly once" possible, but cost a lot. Rarely makes sense in practice.

## Solutions

We can do it in application or persistence level.

### Databases "for event-sourcing"

There are databases "designed for event-sourcing."

These databases optimized for persisting state as a series of read-only events, and they have built-in capability to stream/publish persisted events once it's guaranteed to be persisted.

A side note. This DB is your operational DB. Fulfillment of your service SLAs depends on this DB. So it can be a bad idea to have this DB public and let your downstream services to read directly.

Examples - [EventStore](eventstore.com), or [Axon Server](https://axoniq.io/product-overview/axon-server).

### Change Data Capture (CDC) in Databases

CDC is when we capture changes in our data and then do something with this change, for example - stream somewhere as a series of events. It could be built-in DBMS or built by us.

Example of homemade CDC - triggers in RDBMS.

```SQL
CREATE TRIGGER store_changes AFTER UPDATE, INSERT, DELETE ON source_table
FOR EACH ROW EXECUTE PROCEDURE store_change();
```
And then you try to do something useful in this `store_change()`

This example is for historical reasons and curiosity only.

Built-in functionality for CDC usually is done through the streaming of a commit log.

It make sense in databases with Master-Slave orchestration only. For example, Cassandra cluster of 3 instances would not have a master node; thus there could be conflicting states on different nodes, which would be streamed before Cassandra resolves the conflict. We can stream from all 3 instances and build our conflict resolver, but we do not want to.

On the other hand, MySQL or PostgreSQL is a DBMSes that suits us well - it has Master-Slave cluster architecture, thus streaming of commit log from Master node is a streaming of SoT modification events per se.

Commit log is a log of all the changes that are made. It is typically used for data recovery by replaying them to get back to a desired state by replaying Commit Log transactions.

The Commit Log is the actual source of truth about the state of a DB instance. You can think of the tables as a queryable projection of the log.

Commit log in PostgreSQL called [Write-Ahead log](https://www.postgresql.org/docs/current/wal-intro.html)

MySQL calls Commit log a [REDO log](https://dev.mysql.com/doc/refman/5.7/en/innodb-redo-log.html), but streaming is possible from [binary log](https://dev.mysql.com/doc/refman/8.0/en/binary-log.html), which is created after modifications in table state.

### Message bus as persistence

There are durable message buses. For Example, Kafka may retain messages for days. If we treat a message bus as SoT storage, then persisting and publication of an event are strictly consistent and atomic, which is even more than we need!

But:
1. Kafka is not designed for storing a significant amount of data during a long period of time, typical retention time in Kafka - days,
2. Kafka does not provide selective reading of data, so it's practically useless as operational SoT storage.

In practice, a hybrid approach is used - we back up a message bus with a "proper" DB for caching and read optimization.

The flow would be:

1. Events are published to a message bus,
1. Events are read from the message bus and persisted in a DB by a utility app,
1. Service for which this SoT is an operational data, recovers from DB and read up tail (head?) from the message bus.
1. Consumers read the message bus only.

That's complex, but if you have a strict SLA on data publication after persistence, that could be a way to go.

Check [kafka-journal](https://github.com/evolution-gaming/kafka-journal) for inspiration.

### Application level

We constraint only by our imagination.

For example, you can add "event published" flag to metadata of each event in your SoT database and:
1. initially persist event with the flag set to "false"
2. publish your event in a message bus
3. set the flag to "true"
4. On each crash/outage recovery scan the SoT DB and go through steps 2 and 3 for all events with the flag equal to "false"


# No publication until new state persisted

## Problem

Until modification of state persisted - this modification does not happen. If you crash split second before persisting and recovers - you would not know anything about the event which is not persisted, nor do your downstream services must know nothing about it.

## Solution

If you publish from the Persistence level with one of the approaches above, this obligation fulfillment comes for free.

If you publish on an application level, then just remember to publish events after you received confirmation from your persistence level. Discipline and/or shared utility libraries help.


# Feet wet, hands dirty

Let's set up an RDBMS as SoT Event Store and leverage its commit log streaming to publish all SoT events to Kafka.

## Debezium

[Debezium](https://debezium.io/) is an open-source distributed platform for change data capture. Start it up, point it at your databases, and your apps can start responding to all of the inserts, updates, and deletes that other apps commit to your databases. Debezium is durable and fast, so your apps can respond quickly and never miss an event, even when things go wrong. As they say.

Debezium is built on top of Apache Kafka and provides Kafka Connect compatible connectors that monitor specific database management systems.

There are Production connectors for MySQL, PostgreSQL, MongoDB. Some others in development.

The project provides a tutorial for setting up CDC of MySQL and streaming the events to Kafka. They provide Docker images with all moving parts preconfigured. [Try it out](https://debezium.io/documentation/reference/1.1/tutorial.html)

## Table for events

Debezium is low level - it streams changes in table, it's up to us to set up proper table structure for even storage if our storage is event-sourced.

```MySQL
CREATE TABLE available_car
(
    aggregate_id bigint NOT NULL,
    seq_nr bigint NOT NULL,
    tags varchar(255),
    payload BLOB,
    PRIMARY KEY (aggregate_id, seq_nr)
);
```

* `aggregate_id` - is ID of entry we store events for
* `seq_nr` - sequence number of event in the journal
* `tags` - whatever you need to find events later
* `payload` - content of an event.

You may add timestamp - it could be handy, or other information you need.

`DELETE` and `UPDATE` statements on the table should not be allowed. Once your event persisted and published - it can't be modified. All hotfixes should be done via other events for corrections.

# Conclusion

With great power of distributed systems and messaging Architectures comes great responsibility. Be responsible. Take care of your downstream fellows. Also, stay home.

TODO: add diagrams for solutions, and, perhaps, initial problem statement.
TODO: hands dirty with other solutions.
