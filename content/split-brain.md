Title: Horizontal scaling of microservices. Data consistency concerns or "A definitive guide of how to not split one's brain".
Category: Distributed and rock-solid
Date: 2020-6-16
Tags: microservices, distributed applications, CQRS, event-sourcing, commands, fault tolerance, scalability
Status: draft
Summary: If several instances of a microservice are running in parallel there is no reliable way to predict that instance receives commands/requests. This makes a task of ensuring data consystency not as trivial as it may look like, especially in "high contention" applications. Thinking aloud about possible solutions...


TODO: add link to related article about guaranties in command and event processing.
TODO: Copy-paste summary.

## What's the problem?

It's obvious, but I'll write it anyway to make sure all of us are on the same page.

### (Fictional) case study

We are Elon Musk and as we usually do we want to give away 10000 bitcoins. We split the prize among folks who resolve a "2+2*2" problem and submit a solution via simple Web interface. Here are rules:

1. Everybody is split into "divisions by age". There are 100 divisions (for example, first division is 0-1 years old, second 1-2, etc).
2. Each division would splint 100 bitcoins among participants.
3. First 10000 winners in each division get 0.01 bitcoin.

We anticipate billions of participants all of them trying to submit solution at the same time. We like fair competitions so there would be enough backend resources to process all the requests. So we rented 1000 machines.

We can't spent even a bit more than 10000 BTC in total and exactly 10000 BTCs should be given away.

### Solution architecture

TODO: a diagram with FE and many instances of BE.


### Solution complexities

Since we can't spend more BTCs than we have we have to take into account concurency issue.

Let's assume there is 0.01 left in a division. Two participants submit right solution approximately at the same time. Request lands in two different instances of our backend service. if we would be able to resolve this edge case then we are good with all other cases. Let's evaluate options we have.


#### Just a shared variable somewhere

Implementation could be anything. For example, a field in relational database.

1. Instance one receive request
2. Instance two receive request
3. Instance one validate money
4. Instance two validate money
5. Instance one update persistence
6. Instance two update persistence
7. Instance one sends btc.
8. Instance two sends btc.

You see, this will not work. No Success. Let's try something more sophysticated.

#### A persistence with "compare and set" semantics

This could be zookeeper.

1. Instance one receive request
2. Instance two receive request
3. Instance one validate money
4. Instance two validate money
5. Instance one update persistence and send btc
6. Instance two tries to update persistence, but since value already changed by instance one - the change would be rejected. Instance two would read value from persistence to try again, will see new amount of money is equal to 0 and will not do anything.
7. Instance one sends btc.

Success?!

No.

Instance one may crash after step 5, so we would reduce amount of money left without actually sending them, which violates constrain "Distribute exactly 10000 BTC". What if we change order of actions? Problem still the same - we send BTC, but crash before we have a chanse to update amount of money left, so we would spend more than 10000.

In order to satisfy "distribute exactly 10000" updating persistence and transfering BTC must be "atomic".




#### Good old transactions

Any relational database with ACID transactions. And this is complex, because we
need to elaborate SAGAs and Idempotency before we proceed (but such intensive preparations giving you a hint - this time it's defenitelly success).


We can achaive atomicy if our payment system idempotent on processing commands for BTC transfers. We also would have to add a dedicated storage for persisting SAGA state for each request. That's how it would work:

Since scenario is complex let's separately walk through all the steps performed by a single service and than add second into play.

1. Start transaction.
2. Validate money. If more than 0 - proceed, if less - rollback transaction and stop processing.
3. Generate command id for command to payment system.
4. Persist initial SAGA state with the generated command id.
5. Persist new amount of money.
6. Commit transaction. If commit fails (because another instance executed concurrent transaction) - go to step 1.
7. Send money using the generated command id.
8. Persist final state of saga, marking it complete.

If the microservice crashes at any point between step 1 and 6 - the transaction would be rolled back and it would as if we never received the command. Which is okay. This folk is just unlucky one. No bitcoins.

If it crashes between 6 and 7 then when it restores it should scan the DB for started but not finished SAGAs, will find the one and would proceed to step 7 execution.

If it crashes between 7 and 8 - it would recover, find started SAGA and try to send money once again, but the payment system would detect duplicate of the transfer request because the same command id would be used. So we would not send the BTCs second time and will proceed to step 8.

Now, second instance is into play. No two instances would be able to commit transactions which were executed concurrently. One of them would fail on step 6 and would have to restart from step 1 and keep restarting until amount of money would reach 0 or it would become lucky and commit it's transaction. Exactly 10000 spent is ensured.

So. Success?

In general - Yes. But not in our funny/fictional case. What makes this case spacial? It's a high contention problem. Many instances tries to modify single state concurently and with high rate, so many request would stumble at point 6 and would have to retry. This would lead to ennormous system resources wasted on transaction retries. This overhead could be that huge that could DDoS the entire system.

But in most of the real problems are not of "high contention" so this approach would work. Btw, it's called "optimistic locking". TODO: verify

"High contention" is not to be confused with "high load". If, say, we are building a (very popular) toy bank system then we have billions of clients. They are making transactions from one account to another. This could result in thousands of requests executed at the same time, but they would not compete for concurrent modification of the same data. That's high load, not high contention. Transactions works well with high load since there would be almost no retries due to concurrent modifications of the same data.

Next!

#### Any peristence with command processors sharding




## What is it?

This is a checklist of factors to remember while deciding on combining two components in a single Microservice. These are not rules, but heuristics. One has to apply common sense and contextual reasoning to make a decision.

## Glossary

*Heuristic* - a simple strategy or mental processes that humans use to form judgments quickly, make decisions, and find solutions to complex problems. A heuristic is not a rule, but a starting point for reasoning.

### Operational terms

*Microservice* - an artifact that can instantiate a process (ex: Jar, docker image).

*Process* - an instance of a microservice being executed (ex: a JVM instance of running application from Jar).

### Software engineering terms

*Component* - a loosely coupled piece of logic that could be a microservice (but does not have to). Think of Aggregate or Service or Read Model.

*Critical component* - a component which failure yields high losses (whatever "high" for your business is).

## Microservices as a mean to tame complexity

### Complexity of design

Monoliths are good. They have less operational complexity and impose a less mental burden on communication issues than distributed applications. But they turn to become "big balls of mud." So we manage complexity by splitting a monolith into a set of loosely coupled microservices at the cost of increasing complexity of communication and operations.

But, I'm sure we are not managing it. A monolithic application with carefully designed components could be an elegant and simple piece of software. At the same time, a distributed app could be a perfect distributed "ball of mud."

If a team of engineers has built "a ball of mud," they would probably make a distributed "ball of mud" as well. Microservices are not a means to increase the quality of components design.

Also, refactoring is much more comfortable inside one big single "ball of mud."

```text
Heuristic #1: Microservices are not to be used to reduce the complexity of the design.
```

### Complexity of management

We are splitting engineering forces into teams around business tasks or loosely coupled engineering tasks. It makes sense to split application in a loosely coupled microservices if teams develop and deploy changes with different pace or want to use various technologies to resolve their business problems.

```text
Heuristic #2: If different teams own components, it makes sense to decouple these teams and splitting an application in microservices.
```

Answer on a question "How to assign ownership of components of an application by teams and does it make sense?" - out of scope.

### Operational complexity

The more microservices to manage - the more complex task it is. But the complexity does not increase linearly. A proper build infrastructure handling five microservices would handle 50. But, most probably, not 500. But still...

```text
Heuristic #3: If unsure - keep components in a single microservice to reduce operational complexity.
```

### Fault tolerance

Two components are critical for the same business task, and failure of one of them makes another useless.

Example: We are making a search engine for "best" airplane tickets from a to B. A logic for searching these tickets makes use of a read model representing the current state of prices and availability. Building such a read model is quite a task, so it could be tempting to build it as a microservice. But if our engine fails, this read model component is useless. If the read model crashes - the engine has nothing to query.

```text
Heuristic #4: If two components are critical for the same business task - keep them together.
```

```text
Obvious heuristic #5: If components are critical for different business tasks - keep them separated.
```

We do not want our tickets search engine to tear down our users back office.

```text
Even more obvious heuristic #6: Keep not critical components separated from critical.
```

We do not want logic for sending out email notifications in the same deployment unit with the search engine. If it crashes, it's okay to deliver some notifications minutes later, but it's not okay to stop rendering search service.

Still, keep in mind these are heuristics and not rules. For example, one may want to violate #4 if the read model is queried infrequently, but takes a lot of time to warm up. One may want to separate it from the search logic just because you do not want to wait for its recovery for many minutes every time you redeploy search logic.

### Scalability complexity

Let's continue the evaluation of the example. Our search logic is under high load - we spawn 100 processes of microservice with the search logic. Should keep read model in the same microservice, thus creating 100 copies of it? If the query rate is "high," and the size of the model is "small", so you can keep it all in RAM - yes. If it's huge, then "no" (and later either scale together with scaling database instances or have a dedicated hardware instance for the read model with huge about if RAM).

```text
Heuristic #7: If components could be scaled together - keep then in the same deployment unit, separate overwise.
```

## Afterword

Want to add something, disagree? Write a comment below and let's discuss it. This article is a living set of heuristics I update as I get new experience.
