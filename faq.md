---
layout: default
menuitem: FAQ
title: Frequently Asked Questions (FAQ).
---

### Q. Who wrote GRR and Why?

GRR started at Google as a 20% project and gained in popularity until it became
fully-supported and open sourced.  The primary motivation was that we felt the
state of the art for incident response was going in the wrong direction, and
wasn't going to meet our cross platform, scalability, obfuscation or flexibility
goals for an incident response agent.  A number of those things still hold true
in 2013.

Additionally, we believe that for things to progress in security, everyone has
to up their game and improve their capabilities. We hope that by open sourcing
GRR, we can foster development of new ways of doing things and thinking about
the problem, get it into the hands of real organizations at reasonable cost, and
generally push the state of the art forward.

As of late 2013, the project has gained some momentum and we are beginning to
get code contributions from outside of the core dev team.

### Q. Why is the project called GRR?

When using other tools, we found ourselves making the sound "grrr" a lot, and it
just kind of stuck. GRR is a recursive acronym, in the tradition of
[http://en.wikipedia.org/wiki/GNU GNU] and it stands for GRR Rapid Response. Not
GRR Response Rig or Google Rapid Response which it is sometimes mistaken for.

### Q. Is GRR production ready?

As of October 2013 there are a few medium-large (40K+ agents) cross-platform
installations running successfully off the GRR codebase for more than a
year. These are running off of an internal version of the codebase, maintained
by the GRR development team (see below).  There are also a number of smaller
(<2k) open source installations.

### Q. Should I expect to be able to install and just start running GRR?

Yes, for basic use cases (as of late 2013).

But if you want to do a large-scale enterprise deployment, it is probably best
to think about GRR as a 80% written software project that you could invest in.
The question then becomes: instead of investing X million in product Y to buy
something, should I instead invest 25% of that in GRR and hire a dev to
contribute, build and deploy it?  On the one hand that gives you control and
in-house support, on the other, it is a real investment of resources.

If you are selling GRR internally (or to yourself) as a free <insert commercial
IR product here>, your expectations will be wrong, and you may get
disillusioned.

### Q. Can the GRR team provide me with assistance in getting it setup?

The core GRR team cares about the open source project, but in the end, our main
goals are to build something that works for us. We don't, and won't offer a
helpdesk, professionally curated documentation, nor someone you can pay money to
help you out if something goes wrong. We aren't providing feeds or consulting
services, and have nothing direct to gain from offering the platform. If you
need something pre-packaged and polished, GRR probably isn't right for you (at
least in the short-medium term). For a large deployment you should expect to fix
minor bugs, improve or write documentation, and actively engage with the team to
make it successful.

If someone is willing to code, and has invested some time learning we will do
what we can to support them. We're happy to spend time on VC or in person
helping people get up to speed or running hackathons. However, the time that the
developers invest in packaging, building, testing and debugging for open source
is mostly our own personal time. So please be reasonable in what and how you ask
for assistance. We're more likely to help if you've contributed documentation or
code, or even filed good bug reports.

### Q. So, I'm interested in GRR but I, or my team need some more convincing. Can you help?

The core GRR team has invested a lot in the project, we think its pretty
awesome, so the team happy to talk, do phone calls, or chat with other teams
that are considering GRR. We've even been known to send house-trained GRR
engineers to companies to talk with interested teams. Just contact us
directly. You also can corner one of us, or at least someone from the team, or
someone who works on GRR at most leading forensics/IR type conferences around
the world.

### Q. I've heard that there are secret internal versions of GRR that aren't open
   sourced that may have additional capabilities. Is that true?

GRR was always designed to be open sourced, but with any sufficiently complex
"enterprise" product you expect to integrate it with other systems and
potentially even with proprietary technology. So its true that a number of the
core developers work on those types of features that won't be released
publicly. The goal is to ensure that everything is released, but there are some
things that don't make sense. Below are listed some of the key differences that
may matter to you:

  * *Datastore/Storage* The core development team’s datastore isn't Mongo; we
     use a proprietary datastore that has different characteristics to Mongo. So
     we've tested things at real scale, but on a different datastore backend. We
     have abstracted things such that it "should" work, but be aware open source
     has had a lot less performance testing.

  * *Security and privacy*. The open source version has minimal controls
     immediately available for user authentication, multi-party authorization,
     privacy controls, logging, auditing etc. This is because these things are
     important enough for them to be custom and integrated with internal
     infrastructure in a large deployment. We open source the bits that make
     sense, and provide sensible hooks for others to use, but full
     implementations of these would likely require some integration work.

  * *Data analysis* The current functionality of GRR is mostly focused around
     data collection. But collecting data isn't all that useful, you need to be
     able to analyze it. There are a number of public systems for doing this
     analysis such as those offering Map Reduce functionality but this analysis
     at the moment belongs outside of GRR. In Q4 2013 we have added output
     plugins that allow for easy export to other systems to allow for data
     mining, and these will get better over time.

  * *Machine handling and monitoring*. Much of the infrastructure for running
     and monitoring a scalable service is often built into the platform
     itself. As such GRR hasn't invested a lot in built-in service or
     performance monitoring at the moment. We expose a lot of statistics, but
     collecting them and displaying them isn't part of things yet.

Differences will be whittled away over time as the core GRR team runs open
source GRR deployments themselves.  That means you can expect most of these
things to become much less of an issue over time.

### Q. When will feature X be ready?

Generally our roadmap on the main project page matches what we are working on,
but we reserve the right to miss those goals, work on something entirely
different, or sit around a fire singing kumbaya. Of course, given this is open
source, you can add the feature yourself if it matters.

### Q. Who is working on GRR?

As of Q4 2013, GRR now has full time software engineers working on it as their
day job, plus additional part time code contributors. The project has long term
commitment.

### Q. Why aren't you developing directly on open source? what's up with the big code dumps?

Given we have had very limited contribution from outside, it is hard to justify
the extra effort of jumping out of our internal code review and submission
processes. We'd like that to change, and we will most likely move to Github at
some point. Encouragement in the form of code welcome.

### Q. Why is GRR so complicated?

GRR _is_ complicated. We are talking about a distributed, asynchronous, cross
platform, large scale system with a lot of moving parts. Building that is a
_hard_ and complicated engineering problem. This is not your grandmother’s pet
python project.

We built the core GRR engine, and the engineers that work on it know it well,
but as of Q4 2013, we haven't built the abstractions to make it easy for
non-core engineers to add functionality. It is possible, people have done it,
but its hard. We're working on improving this in Q4 2013 through better
abstractions for normal tasks.

### Q. What are the commercial competitors to GRR?

Some people have compared GRR functionality to Mandiant's MIR, Encase
Enterprise, or F-Response. There is some crossover in functionality with those
products, but we don't consider GRR to be a direct competitor. GRR is unlikely
to ever be the product for everyone, as most organizations need consultants,
support and the whole package that goes with that.

In many ways we have a long way to go to match the capabilities and ease of use
of some of the commercial products, but we hope we can learn something off each
other, we can all get better, and together we can all genuinely improve the
security of the ecosystem we all exist in. We're happy to see others use GRR in
their commercial consulting practices.