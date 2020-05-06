Title: Publishing events in distributed applications. Obligations of publishers.
Category: Distributed and rock-solid
Date: 2020-4-30
Tags: Distributed applications, event streaming, event-sourcing, CDC, PostgreSQL, MySQL

Exposing state via "state change" events is a well known and well-used pattern in modern distributed applications. We all have reasons to use it in our systems. Scope of the article - discuss our obligations as event publishers.

## Recap

Let's quickly remind ourselves about event-streaming, event-sourcing, and why we care.

### What is event-sourcing?

EventSourcing (ES) is when your "Source of Truth" (SoT) is not a snapshot of a current state but a series of events, describing state transitions.

ES is not when:

1. You stream your SoT events.
1. You apply the CQRS pattern.

So, if persistence level stores state as a series of events describing the past - that's event-sourcing. Event streaming and CQRS usually come together with event-sourcing, but have nothing to do with it per se and _are possible without event-sourcing_.

### Which events we publish?

We publish any events that make sense for downstream services. Published events do not have to be SoT events. That's why we could publish events without our persistence level being event-sourced.

## Obligations of publishers

To provide downstream services consistent view on a state, publishers have to fulfill these obligations:

1. **No deviation from SoT**. Published Events must all the time be consistent with SoT state.
1. **Guarantee of publication**. Once entity state is changed - respective event _must_ be eventually published,
1. **No publication until the new state persisted**. Nobody should see events before corresponding state modification is persisted. _If it's not persisted, then it's not happened yet._

Bonus - what are not obligations of publishers:

1. Providing downstream services historical events - it's up to readers to persist your events and go back in time if they need/want to.
1. Providing downstream services projections of events aggregation - it's up to readers to build and maintain their projections/read models.


# No deviation from SoT

## Problem

It should all the time be possible to reconstruct state from events we publish, and this reconstructed state must not conflict with SoT.

Of course, downstream services may fail while building their view of state from the events, but nevertheless, we must ensure we are not messing up on our publishing side.

## Solutions

Make your state event-sourced and _publish SoT events_. In this case, your published events would be consistent with state by definition - they are the state.

Or, _Publish entire state on its every modification_. That's easy, so we assume we have to stream events due to reasons (say, our state is "big") and continue our discussion ignoring this option.

If you do not want or to can't expose your SoT - stick in stateless transformer between downstream services and your publisher. That adds risk of not fulfilling this obligation due to additional moving parts, but there are situations when it's necessary.

# Guarantee of publication

## Problem

Once a state of an entity changed and this change persisted in your SoT database, the corresponding event has to be eventually published. If you can't guarantee this then you corrupt state of downstream services, so:

1. "At most once" guarantee on event publication is not enough. Theoretically this is possible, but implies many complications for missing events corrections, and is not worth to be considered as an option.
1. "At least once" guarantee is enough. It's not hard for downstream to filter out duplicates if you attach unique sequence numbers to events.
1. "Exactly once" possible, but it costs a lot. Rarely makes sense in practice.

## Solutions

### Databases "for event-sourcing"

There are databases "designed for event-sourcing."

These databases optimized for persisting state as a series of read-only events, and they have built-in capability to publish events after persisting.

A side note. These DBs may come with reach functionality for building projections, recovering historical events etc. Thus it's tempting to let your downstream services to read from it directly. But, if this DB is used to persist SoT events, then this is your operational DB. Fulfillment of your service SLAs depends on this DB. So generally, it's a bad idea to have this DB public and let your downstream services read directly. We keep our _operational_ relational DBs private, why should we make _operational_ Event Stores public?

Examples - [EventStore](eventstore.com), or [Axon Server](https://axoniq.io/product-overview/axon-server).

### Change Data Capture (CDC) in Databases

CDC is when we capture changes in our data and then do something with these changes, say, publish as events. Example of homemade CDC - triggers in RDBMS.

```SQL
CREATE TRIGGER store_changes AFTER UPDATE, INSERT, DELETE ON source_table
FOR EACH ROW EXECUTE PROCEDURE store_change();
```
And then you try to do something useful in this `store_change().`

Most modern DBMSes have built-in CDC, and they usually publish a projection of a commit log.

Commit log is a log of all the changes made. It is typically used for data recovery by replaying them to get back to a desired state by replaying Commit Log transactions.

_The Commit Log is the actual source of truth about the state of a DB instance. You can think of the tables as a queryable projection of the log._

Commit log streaming makes sense in databases with Master-Slave orchestration. For example, Cassandra cluster of three instances would not have a master node; there could be conflicting states on different nodes, but CDC would publish corresponding events before Cassandra resolves the conflict. To mitigate it, we can publish from all three instances and build our conflict resolver, but we do not want to.

On the other hand, MySQL or PostgreSQL are DBMSes that suit us well - they have Master-Slave cluster architecture, thus streaming of commit log from Master node is a streaming of SoT modification events per se.

Commit log in PostgreSQL is called [Write-Ahead log](https://www.postgresql.org/docs/current/wal-intro.html)

MySQL calls Commit log a [REDO log](https://dev.mysql.com/doc/refman/5.7/en/innodb-redo-log.html), but CDC is from [binary log](https://dev.mysql.com/doc/refman/8.0/en/binary-log.html), which is created after modifications in table state. Still, it looks like it works.

### Message bus as persistence

There are durable message buses. For exampl, Kafka may retain messages for days. If we treat a message bus as SoT storage, then persisting and publishing of an event are strictly consistent and atomic, which is even more than we need! But Kafka does not provide selective reading of data, so it's practically useless as an operational SoT storage.

In practice, there is a hybrid approach - we back up a message bus with a DB for caching and read optimization. The flow would be:

1. Events are published to a message bus,
1. Events are read from the message bus and persisted in a DB by a utility app,
1. Service for which this data is the operational data, recovers from DB and read up tail (head?) from the message bus,
1. Consumers read only from the message bus.

That's complex, but if you have a strict SLA on data publication after persistence, that could be a way to go.

Check [kafka-journal](https://github.com/evolution-gaming/kafka-journal) for inspiration.

### Application level

We constrained only by our imagination. For example, you can add "event published" flag to the metadata of each event in your SoT database and:

1. initially persist event with the flag set to "false,"
2. publish your event in a message bus,
3. set the flag to "true,"
4. on each crash/outage recovery scan the SoT DB and go through steps 2 and 3 for all events with the flag equal to "false."

# No publication until new state persisted

## Problem

Until modification of state has persisted - this modification did not happen. If you crash split second before persisting new state and recovers - you would not know anything about the state you were about to persist. Your downstream services must know nothing about it as well; otherwise, they would have a corrupted view on actual state.

## Solution

If you publish on the Persistence level with one of the approaches above, this obligation is fulfilled for free.

If you publish on an application level, then just remember to publish events after you received confirmation from your persistence level. Discipline and/or shared utility libraries help.

# Feet wet, hands dirty

Let's set up an RDBMS as SoT Event Store and leverage its commit log streaming to publish all SoT events to Kafka.

## Debezium

[Debezium](https://debezium.io/) is an open-source distributed platform for change data capture. Start it up, point it at your databases, and your apps can start responding to all of the inserts, updates, and deletes that other apps commit to your databases. Debezium is durable and fast, so your apps can respond quickly and never miss an event, even when things go wrong. As they say.

Debezium is built on top of Apache Kafka and provides Kafka Connect compatible connectors that monitor specific database management systems. There are Production connectors for MySQL, PostgreSQL, MongoDB.

The project provides a tutorial for setting up CDC of MySQL and streaming the events to Kafka. They provide Docker images with all moving parts preconfigured. [Try it out](https://debezium.io/documentation/reference/1.1/tutorial.html)

# Conclusion

With great power of distributed systems and messaging Architectures comes great responsibility. Be responsible. Take care of your downstream fellows.
