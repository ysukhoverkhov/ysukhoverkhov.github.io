Title: Publishing Source of Truth events with CDC
Category: TODO
Date: 2020-4-26
Tags: TODO


TODO: find out proper name "messaging architecture" is a wrong term
# Publishing Source of Truth events in messaging architectures

## Recap

Before recapping about why and how we stream events, let's quickly remind ourselves about event-sourcing and why we care.

### What is event-sourcing?

EventSourcing (ES) is when your "Source of Truth" (SoT) stored not as a snapshot of a state, but as a seriece of events, descibing state transitions.

ES is not when:
1. You stream your SoT events.
1. You apply CQRS pattern.

Bottom line - if your persistence layer stores state of an entity as seriece of events descibing what happed with the entity in the past - that's EventSourced entity. Event streaming and CQRS usually comes together with ES, but have nothing to do with ES per se _and possible without ES_.

### Why we want to publish events, describing state modifications?

Because of CQRS, which is cool. Homework - readup on your own.

Events streamed do not have to be SoT events. This mean we could publish events without our peristence layer being EventSourced.

### How to publish events properly?

Ok, so you decided to publish events, describing your entity state and let your downstream services reason about your entity state by consuming your events.

WooHoo!!!:
1. You do not have to worry about who, when, for what reason consumes them anymore (unless you change scheme)!
2. No matter what these downstream services are doing - they would never DDoS your HTTP (or whatever) API, requesting updated state - you do not have that API :P!

Not so "WooHoo" - with this freedome come complications:
1. Pain-in-the-ass migrations,
1. Somebody has to install, configure and support message buses,
1. Perhaps something else I forgot.

... and obligations:
1. You have to ensure events you publish would never deviate from SoT state.
1. once entity state is changed - respective event must be eventually published,
1. no downstream services should see event before the event persisted in your SoT database.

**Scope of this article - disciss how to fulfil these three obligations.**

# No deviation from SoT

## Problem

From events we publish it should all the time be possible to reconstruct state and this reconstructed state must not conflict with SoT.

Of course, downstream servies may fail while building their view of state from event we publish, but we must ensure we are not messing up on our side.

## Solution

Make your state event sourced and stream SoT events directly. In this case your published events would be consistent with state by definition - they are the state.

That's why it's generally a good idea to be event sourced even if we do not have to.

Or

_Publish entire state on its every modification_. That's easy, so we assume we have to stream events due to reasons (say, our state is "big") and continue our discussion ignoring this option.

# All event must be eventually published in order of creation

## Problem

Once state of entity changed and this change persisted in your SoT persistence layer (say, database), respective event has to be eventually published. That's your obligation, your downstream services rely on this - their projections of your state would be corrupted unless this guarantee is satisfied, thus:

1. "At most once" guarantee on event publication is not enough. Actually theoretially this is possible, but implies a lot of complications for the missing event corections, and does not worth to be considered as an option.
1. "At least once" guarantee is enough. It's not hard for downstreams to filter out duplicates, if you attach unique sequence number to events.
1. "Exactly once" possible, but cost a lot. Does not make sence in practice.

## Solution

This could be done in application or persistence layer. There are several ways in persistence layera and infinite amount of ways on application layer. Lets review them.

### Databases "for event-sourcing"

There are databases "designed for event-sourcing".

These databases optimized for persisting state as a series of events which content never changes and they have built in capability to stream persisted event somewhere, once it's guaranteed to be persisted. Some of them could act as message buses, so, event consumers may subscrive to the database directly, but I consider it as an Anti-Pattern (TODO: add link to an article which describes it, once it would be written).

Examples - EventStore (TODO, link here), or Axon Server (TODO - link).

### Change Data Capture (CDC) in Databases

CDC is when we capture changes in databases and then stream if we like, or do simething else. Could be built-in or built by us.

Example of home made CDC - triggers in RDBMS.

```SQL
CREATE TRIGGER store_changes AFTER UPDATE, INSERT, DELETE ON source_table
FOR EACH ROW EXECUTE PROCEDURE store_change();
```
And then you try to do something useful in this `store_change()`

This example is for historical reasons and curiocity only, let's move on.

Built-in functionality for CDC usually is done through streaming of a commit log.

It make sence in databases with Master-Slave orchestration only. For example, Cassandra cluster of 3 instances would not have a master node, thus there could be conflicting state on different nodes, which could be streamed before conflict is resolved and state "repaired". We do can stream from all 3 instance and build our own conflict resolver, but we do not want to.

On the other hand, PostgreSQL is a DBMS which suits us well - it has Master-Slave cluster architecture, thus streaming of commit log from Master node is a streraming of SoT modification events per se.

Commit log is a log of all the changes that are made. It is typically used for data recovery by replaying them to get back to a desired state by replaying Commit Log transactions.

The Commit Log is the actual source of truth about the state of a DB instance. You can think of the tables as a queryable projection of the log.

Commit log in PostgreSQL called "Write-Ahead log".

### Exotic ways on persistence layer

Check "kafka-journal" for inspirtion (TODO: link).

### Application layer

You, for example, can add "event published" flag to metadata of each event in your SoT database And
1. initially persist event with the flag set to "false",
2. publish your event in a message bus once you are sure it's persisted,
3. set the flag to "true".

On each crash/outage recovery scan the SoT DB and go through steps 2 and 3 for all events with the flag equal to "false". Kinda pain in the ass, but "at least once" guarantie is here.

Other solutions possible, but that's out of scope of the discussion.

# No publication until new state persisted

## Problem

Until modification of state persisted - this modification is not happened.

Discussion of actions we want to take if persistence layer failed or we crashed before persisting is another topic, for now let's just accept it.

Our downstream services should not be exposed to a fact which is not happened yet, because they may execute their actions as response on the state change, but it's not happened yet! So do not publish event until state change is persisted in your SoT database. That's just common sence.

## Solution

Just do not publish on your own - leave it to Persistence layer with one of approaches above and this obligation fulfilment comes for free.

If you push this responsibility to your application - just remember to publish event after you received confirmation from your persistence layer while persisting state modifications and never before.

# Feet wet, hands dirty

Let's set up PostgreSQL as Event store and leverage its commit log streaming to publish all SoT events to Kafka.


### Setup PostgreSQL
####
