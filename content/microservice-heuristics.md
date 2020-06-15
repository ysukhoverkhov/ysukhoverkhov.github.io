Title: "When to create a new microservice" heuristics
Category: Distributed and rock-solid
Date: 2020-6-2
Tags: microservices, heuristics, distributed applications
Summary: There are debates about "should we create a new microservice for this functionality"? Here are my heuristics on the subject.

There are debates about "should we create a new microservice for this functionality"? Here are my heuristics on the subject.

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
