---
layout: default
menuitem: Home
order: 1
---

# GRR Rapid Response Framework.

GRR is an Incident Response Framework focused on Remote Live Forensics.

## State of the Project

GRR is currently in an Beta release, ready for testing by end users. More
information can be found in the (GRR Rapid Response documentation)[docs.html].

### Update: August 8 2014

Blackhat talk "GRR: Find all the badness, collect all the things"
[slides](docs/References/Presentations/GRR_Blackhat_2014_Greg_Castle.html) and
[artifact
whitepaper](docs/References/Papers/GRR_Artifacts_Whitepaper_Blackhat2014_Greg_Castle.html)
are up.

### Update: August 4 2014

This weekend I gave a GRR workshop at the [DFRWS](http://dfrws.org/) in
Denver. This is probably mostly interesting for people who attended but the
slides are available at [DFRWS US workshop
slides](docs/References/Presentations/DFRWS_US_2014.html).

I also released a minor update to the GRR server, the install script now points
at version 3.0-2. New in this version:

  * There are some bugfixes to various flows (auto update, file finder, ...).

  * The clients also got upgraded to a new version (3.0.0.2). The most notable
    bug we fixed is that the last Windows clients were missing a MSVC runtime
    dll and would not install on machines that don't have the runtime installed
    already.

  * Some people had problems with the rendering of Rekall output in the last
    version. We put a lot of effort into this so rendering should now work
    better and also give some more information, check out the pslist plugin for
    an example. There has been a Rekall release in the meantime so now you need
    to run v1.0.3 on the server.

### Update: June 27 2014

Hey everyone,

I have just updated our download site, we are releasing a new
server package today!

The new server has version 0.3.0 (not 0.2.10 like the release
candidate / test server) but before you get too excited, we
decided to change the versioning scheme to make client upgrades
easier, not because it's so radically different from the last
server. Think of it more like a version 0.2.10.

Still, we have some cool new features since 0.2.9. We now use
Rekall as the memory forensics platform which gives much better
results than Volatility did and there are new flows that should
make the basic everyday workflows more intuitive (File- or
RegistryFinder for example). Since this was a pretty popular
request, the new server now also comes with a client for rpm
based Linux distros that should just work out of the box. There
are also stability improvements if you run big hunts, some new
gui elements, better data export functionality, and many more
features I probably forgot.

I'd also like to use this opportunity to announce that this
server is probably the last one that will use Mongo as the
default backend. We currently have Flavio doing an internship
here with the GRR team and he has done some proper research on
the data store backends. Preliminary results confirm what we
thought for quite some time that Mongo is really slow for our use
case. As an alternative we offer the MySQL data store which is a
bit better than Mongo but has its own weaknesses. We are
currently experimenting with a TDB and a SQLite based data store
and they are both *much* faster than MySQL (and of course Mongo)
so using one of those should provide a much more scalable
environment and we will therefore probably switch to one of those
in the near future. Those backends are included in the server so
you can play with them but they are probably not production ready
yet, use at your own risk.

If you want to test the new server right away, please redownload
and run the installation script as described in
https://code.google.com/p/grr/wiki/GettingStarted

Have fun using the new server :)

Cheers,
- Andy


Oh there is one known issue, we included a 32 bit client for deb
based Linux platforms. That client does not repack in the default
setting because we don't install the 32 bit libraries as a server
dependency. Please ignore the error messages.

This is still not fixed since we consider it quite low priority:

  * This release comes with a prebuilt mac client which does not support custom
    client names, it will always run as "grr" regardless of your Client.name
    settings.

To get an idea of where GRR is heading see the
[https://code.google.com/p/grr/wiki/Roadmap roadmap].

## Information

GRR consists of an agent that can deployed to a target system, and a server
infrastructure that can manage and talk to the agent. More information can be
found in the [https://github.com/google/grr-doc/blob/master/implementation.adoc
GRR Developer documentation] and [http://code.google.com/p/grr/wiki/Contributing
Contributing to GRR development].<br>

Client Features:

  * Cross-platform support for Linux, Mac OS X and Windows clients (agents)
  * Open source memory drivers for Linux, Mac OS X and Windows
  * Supports searching, downloading
  * Volatility integration for memory analysis
  * Secure communication infrastructure designed for Internet deployment
  * Client automatic update support

Server Features:

  * Fully fledged response capabilities handling most incident response and forensics tasks
  * OS-level and raw access file system access, using the !SleuthKit (TSK)
  * Ajax Web UI
  * Fully scriptable IPython console access
  * Enterprise hunting support
  * Basic system timelining features
  * Basic reporting infrastructure
  * Support for asynchronous flows
  * Fully scaleable back-end to handle very large deployments
  * Detailed monitoring of client CPU, memory, IO usage
  * Automated scheduling for reoccurring tasks

See [http://code.google.com/p/grr/wiki/GettingStarted GettingStarted] to start using it.

## Screenshots
||
<a href="http://raw.githubusercontent.com/google/grr/gh-pages/screenshots/Screenshot from 2013-11-18 18-36-13.png"><img src="http://raw.githubusercontent.com/google/grr/gh-pages/screenshots/Screenshot from 2013-11-18 18-36-13.png" width="140" height="80" /></a>
||
<a href="http://raw.githubusercontent.com/google/grr/gh-pages/screenshots/Screenshot from 2013-11-18 18-36-46.png"><img src="http://raw.githubusercontent.com/google/grr/gh-pages/screenshots/Screenshot from 2013-11-18 18-36-46.png" width="140" height="80" /></a>
||
<a href="http://raw.githubusercontent.com/google/grr/gh-pages/screenshots/Screenshot from 2013-11-18 18-37-37.png"><img src="http://raw.githubusercontent.com/google/grr/gh-pages/screenshots/Screenshot from 2013-11-18 18-37-37.png" width="140" height="80" /></a>
||
<a href="http://raw.githubusercontent.com/google/grr/gh-pages/screenshots/Screenshot from 2013-11-18 18-40-49.png"><img src="http://raw.githubusercontent.com/google/grr/gh-pages/screenshots/Screenshot from 2013-11-18 18-40-49.png" width="140" height="80" /></a>
||
<a href="http://raw.githubusercontent.com/google/grr/gh-pages/screenshots/Screenshot from 2013-11-18 18-41-45.png"><img src="http://raw.githubusercontent.com/google/grr/gh-pages/screenshots/Screenshot from 2013-11-18 18-41-45.png" width="140" height="80" /></a>
