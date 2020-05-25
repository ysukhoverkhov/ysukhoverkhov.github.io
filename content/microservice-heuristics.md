Title: "When to create new microservice" checklist/heuristics
Category: Distributed and rock-solid
Date: 2020-5-10
Tags: microservices, heuristics
Status: draft


Glossary

Application - an artifact which can instantiate a process (ex: Jar, also it's called "microservice" in the title)

Process - instance of the application that is being executed (ex: a JVM instance running application from Jar)

Aggregate - A cluster of associated objects that are treated as a unit for the purpose of data changes. External references are restricted to one member of the AGGREGATE, designated as the root.

Service - An operation offered as an interface that stands alone in the model, with no encapsulated state. Typically used to perform complex business transaction which are not in scope of a single Aggregate.

Read model - model specialized for reads. It takes events produced by the domain and uses them to build and maintain a model that is suitable for answering the client's queries. It can draw on events from different aggregates and even different types of aggregate.

Component - either Aggregate or Service or Read Model.

Mission critical component - in case of failure imposes significant financial loses (homework - find out with your PO is your particular component mission critical).
Scope of the document

    A checklist of factors to be taken into account while making a decision about combining two components in a single Application.
    Will not give universal answer - one will have to apply heuristics to make a decision.

Assumptions

    Each component in our model can be categorized either as Aggregate or as a Service or as a Read model.
    These components are well designed - "good" design is out of scope of the document.

How to read/use

Initially correctly designed components work well with component per service. But this approach increase complexity and cost of both operations and development and decrease performance. So we would like to combine them in applications whenever it's possible.

Bellow there are checklists of things we are taking into account while making the decision about combining two particular component types. If an app has already three components in it and you thinking about adding fourth - verify your candidate against each of three components which are already in the app. Apply buddy and common sense if got conflicting results (smile).

A - Aggregate

S - Service

R - Read model

? - Component of any type

(plus) - consider combining in one app

(minus) - consider separate apps

Checklists

? + ?

(plus) - both components are critical and failure of one of them makes another useless.

(minus) - one of components is critical and failure of another does not render critical component useless, but may render it malfunction due to same process sharing.

(minus) - there are strong reasons to ship functionality provided by components independently, thus we need independent deployments.

Examples:

RNG Blackjack Game Aggregate, RNG Roulette game Aggregate

Both mission critical, but are independent to each other. We have no reason to put in same app.

Failure of BJ does not makes RT failed, but may render it useless. For example due to error in BJ code there will be a huge memory leak. So we want them in separate applications.

RNG Game DWH Events Producer, RNG Game game Aggregate

Both of them are critical. DWH events generator is useless without game and game can tolerate only short DWH even generator outage. It could make sense to put them in a single application.

There is additional demand from Ops to have DWH Events Generator as a dedicated service since they want it to deploy individually or disaster recovery. So perhaps point 3 in the checklist wins.

RNG Game DWH Events Producer, DWH Events Consumer

Both are critical, so we perhaps want all the DWH Event generators be in the same app as DWH events consumer, but we do not. If DWH Event generator is failing then DWH Events consumer still useful since it receives events from other games.

A + S

(plus) - Most of other components orchestrated are already in the same app

Example:

RNG Game Aggregate, Player Wallet Aggregate, RNG Game Service

One of concerns of RNG game service - orchestration of business transactions between game aggregate and wallet aggregate. Obviously we do not want to put RNG Game Service in the same app with Wallet Aggregate (see ?+?). But it make sense to put it in the same app as RNG Game Aggregate since they are both critical in scope of RNG and only useful if both are functioning.

A/S + R

(plus) - Read model is used by the Aggregate/Service (it reads from the model). This means the same read model can be used in several apps (in form of library).

(minus) - This read model is optional for the Aggregate/Service to function and Aggregate/Service is critical.

(minus) - Built read model consumes a lot of resources and used by many Aggregates/Services.

(plus) - Read model has strict SLA on consistency which can't be fulfilled without placing it in the same application as Aggregate which events are used to build the model

Example:

RNG Game Service, User Session Read model

We, potentially can build read model for user sessions in each service which strictly need it, unless there is a requirement like "if Auth service is not working then users should not be authenticated", so we can't use outdated model. In this case Auth Service and Auth Read model should reside in one application and others query session or subscribe on read model changes.

RNG Game Service, Table Assignment Read model

Each RNG game uses this read model, there are no strict SLAs, not much resources of consumed, so we want to have this read model in each of RNG applications which need it
