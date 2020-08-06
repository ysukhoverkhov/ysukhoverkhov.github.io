Title: TODO: Horizontal scaling of microservices. Data consistency concerns or "A definitive guide of how to not split one's brain."
Category: Distributed and rock-solid
Date: 2020-6-16
Tags: microservices, distributed applications, CQRS, event-sourcing, commands, fault tolerance, scalability
Status: draft
Summary: TODO: If several instances of a microservice are running in parallel, there is no reliable way to predict which instance receives commands/requests. This makes the task of ensuring data consistency not as trivial as it may look like, especially in "high contention" applications.


TODO: add link to related article about guaranties in command and event processing.
TODO: Copy-paste summary after syntax checks

## (Fictional) case study

We are Elon Musk, and, as usual, we want to give away 10000 bitcoins. We split the prize among folks who resolve a "2+2*2" problem and submit a solution via a simple Web interface. Here are the rules:

1. Everybody is split into "divisions by age." There are 100 divisions (for example, the first division is 0-1 years old, second 1-2, etc.).
2. Each division would splint 100 bitcoins among participants.
3. The first 10000 winners in each division get 0.01 bitcoin.
4. We must give away precisely 100 BTC per division - even a 0.01 error in any direction would hit our имидж.

We anticipate billions of participants, all of them trying to submit a solution at the same time. We like fair competitions, so there would be enough backend resources to process all the requests. So we rented 1000 machines.

### Solution architecture

TODO: a diagram with FE and many instances of BE.


### Solution complexities

The main complexity is to give away exactly the 100 BTC per division due to concurrent result evaluation. This problem boils down to "0.01 BTC left, and there are two competitors submitting results".

## Possible solutions evaluation

### Just a shared variable somewhere

Implementation could be anything — for example, a field in a relational database.

1. Instance one receive request
2. Instance two receive request
3. Instance one validate money
4. Instance two validate money
5. Instance one update persistence
6. Instance two update persistence
7. Instance one sends btc.
8. Instance two sends btc.

You see, this will not work. No Success. Let's try something more sophisticated.

### A persistence with "compare and set" semantics

The persistence implementation could be a zookeeper.

1. Instance one receive request
2. Instance two receive request
3. Instance one validate money
4. Instance two validate money
5. Instance one update persistence and send btc
6. Instance two tries to update persistence, but since value already changed by instance one - the change would be rejected. Instance two would read value from persistence to try again, will see new amount of money is equal to 0 and will not do anything.
7. Instance one sends btc.

Success?!

No.

Instance one may crash after step 5, so we would reduce the amount of money left without actually sending them, which violates constrain "Distribute exactly 10000 BTC". What if we change the order of actions and send BTC before updating persistence? The problem still the same - we send BTC, but crash before we have a chance to update the amount of money left, so we would spend more than 10000.

To satisfy "distribute exactly 10000," updating persistence and transferring BTC must be an "atomic" operation.

How do we do it?

### Optimistic locking

Let's use any database with ACID transactions. And this is complex because we need to elaborate SAGAs and Idempotency before we proceed (but such intensive preparations giving you a hint - this time it's a success).

TODO: give a link to SAGA article.
TODO: give a link to the idempotency article.

We can achieve atomicity if our payment system idempotent on processing commands for BTC transfers. We also would have to add dedicated storage for persisting SAGA state for each request.

Since the scenario is complex, let's separately walk through all the steps performed by a single service and then add second into play.

1. Start transaction.
2. Validate BTC left. If more than 0 - proceed, if less - rollback transaction and stop processing.
3. Generate command id for a command to the payment system.
4. Persist initial SAGA state with the generated command id.
5. Persist the new amount of money.
6. Commit transaction. If the commit fails (because another instance executed a concurrent transaction with a modified amount of money) goes to step 1.
7. Send money using the generated command id.
8. Persist the final state of SAGA, marking it complete.

If our service crashes, it reads the state of all unfinished SAGAs and continues their execution.

If it crashes at any point between steps 1 and 6 - the transaction would be rolled back, and it would as if we never received the command. No modifications in persistence - no SAGA found. Nothing happened, which is okay. This folk is just an unlucky one. No bitcoins.

If it crashes between 6 and 7, then it would restore the SAGA and proceed to step 7 execution.

If it crashes between 7 and 8 - it would find started SAGA and try to send money once again (step 7), but the payment system would detect duplicate of the transfer request because we would use the same command ID. So we would not send the BTCs second time and will proceed to step 8.

Now, the second instance is into play. No two instances would be able to commit concurrent transactions because both transactions modified the same field - the amount of BTC left in the bucket. One of them would fail on step 6 and would have to restart from step 1, and it will keep restarting until the amount of money would reach 0 or transaction commit would be successful. We ensured "exactly 100 per division spent."

So. Success?

In general, - yes, but not in our fictional case. What makes this case special? It's a high contention problem. Many instances try to modify a single state concurrently, and with a high rate, so many requests would stumble at point 6 and would have to retry. These transaction retries would lead to enormous system resources waste and could even DDoS the entire system.

But most of the real-life problems are not of "high contention," so this approach would work.

"High contention" is not to be confused with "high load." For example, we are building a prevalent payment system for some virtual currency with billions of clients. They are making transactions from one account to another, which results in thousands of requests executed simultaneously, but they would not compete for concurrent modification of the same data. That's the "high load," not "high contention." Optimistic locking works well with a high load since there would be almost no retries due to concurrent modifications of the same data.

The "transactions" approach almost worked for us but didn't. What did we learn from it? It does not make sense to execute requests to withdraw BTC from a single bucket in parallel. Since our problem is of high contention, we gain nothing from this parallelization and, in fact, even lose performance. But how do we ensure sequential execution of commands with many instances and random instances receiving commands? With pessimistic locking or with sharding.

### Pesimistick locking

Optimistic locking - "oh, I'm sure I'll not collide with anyone, so let's proceed with the modification and rollback in the end in case of collision."
Pessimistic locking - "well, I'm sure I'll collide with concurrent modification, so let's first lock the resource, modify and then release the lock."

Again, we can use Zookeeper, but now not for holding the amount of BTC left in a bucket, but for holding pessimistic locks on the bucket.

Here is a flow of a single instance first:

1. Lock bucket.
1. Start transaction.
2. Validate BTC left. If more than 0 - proceed, if less - roll back the transaction, release the lock, and stop processing.
3. Generate command id for a command to the payment system.
4. Persist initial SAGA state with the generated command id.
5. Persist the new amount of money.
6. Commit transaction. If the commit fails - release the lock and start over.
7. Send money using the generated command id.
8. Persist the final state of SAGA, marking it complete.
9. Release lock.

You may ask a question: why do we need the transaction? Strictly speaking, we do not need it - we need steps 4 and 5 to be atomic, transactions are just one of the ways to ensure it.

The behavior of the second instance is dead simple. If at step 1, it can't lock the bucket - it just waits until it can and then proceed.

The problem of high contention solved, here is the cost:

1. There is an overhead on constant locking/unlocking of buckets.
2. Costly instances would either wait for the lock to acquire and do nothing. Since command distribution is random, we may be unlucky and have most instances receiving requests for the same bucket, reducing the system's throughput.
3. Instead of waiting for the lock, we may stash commands for a locked bucket and proceed with the next command processing. We shift "retry" logic from a database to command processing, which is, in general, more optimal, but still not good enough.
4. If an instance crashes while holding a lock, a particular logic must be applied to let another instance forcefully reacquire the lock and continue the created SAGA execution. We have to make sure the "crashed" instance is crashed and not just lost network connectivity to Zookeeper. I do not know an easy automated way of doing it.

Success?

Not really. May worth using in some cases, but I'd say these should be business cases. For example, if you are making a plane tickets shop. The start of the booking process of a single ticket would create a pessimistic lock on the ticket, so nobody would be able to reserve it while filling your passport details and specify the amount of baggage. I'd not use pessimistic locking for dealing with "high-contention" engineering problems.

### Sharding

So, let's analyze another way of ensuring linear command processing per bucket but without pessimistic locking.

We can do it with any persistence combined with command sharding.

We have 100 buckets. Let's launch, say, 50 instances of our service. Instance 1 would be responsible for processing requests in buckets 1 and 51, instance 2 for buckets 2 and 52, and so on.

Each instance knows this distribution. So, if an instance receives a request for a bucket it's not "assigned" to - it forwards the received request to an assigned instance. We just reduced the problem to "sequential processing inside one instance," which is trivial.

1. Instance one receive request
2. Instance two receive request
3. Instance one forwards request to instance 3 assigned to the bucket.
3. Instance two forwards request to instance 3 assigned to the bucket.
3. Instance three validate money executing first request.
4. Instance three update persistence and send btc executing the first request.
4. Instance three validate money executing second request and stops its execution since no money left.

Success?

Yes!

Have we found a silver bullet?

No.

This approach is the most complex if we think beyond this trivial and fictional case study (Elon would never give away his BTCs, obviously).
In real-life instances are dynamic - they go up and down all the time at least because we redeploy them. A responsibility to process commands for bucket X should migrate between instances. Here are problems we would have to resolve:

1. An instance is going down because it's crashed. There should be a supervisor to detect it and spawn a new instance.
2. All the instances would have to update their tables of "where do we forward requests to bucket X?"
3. An instance may not crash but just would lose connectivity with the supervisor, but from the supervisor's point of view, it crashed so that it would spawn a new instance responsible for the same bucket. Your router/load balancer still may be aware of the old instance and forward request to it, thus we would have a rogue instance executing requests for bucket X and another instance acknowledged by the supervisor. This situation violates all the logic of processing, and it's called "split-brain."

There are frameworks mitigating this problem (check Akka's "Split Brain Resolver," for example), but it's the most sophisticated solution. I'd go for it only in extremely "high-contention" problems.

### Optimistic locking combined with sharding without guaranties

That's what it is. We use any database with ACID transactions on persistence level as we did in the "optimistic locking" option. To mitigate the "too many transaction retries" problem, we roughly split traffic by instances ensuring the vast majority of commands for a bucket landing the same instance. We do not need strict guarantees since there are transactions to protect us from "split-brain".

We can distribute commands by instances with a smart load balancer capable of analyzing commands or using any message bus with queue partitioning, like Kafka.

In a stable state, the same instance would receive all the commands for a shard. In case of redeployment/crash during a short period of time, there is a chance of having several instances executing commands for the same bucket, but this would not cause problems with data consistency due to optimistic locks but would lead to temporary degradation in command handling because of a spike of transaction restarts.


## Afterwords

What should you choose? Evaluate all the options and analyze the consequences.

My heuristic: "go with optimistic locking by default and cheat with "sharding without guarantees + optimistic locking" if there is a "high-contention." Use true sharding only if degradation in processing during redeployments is not acceptable. Avoid pessimistic locking."
