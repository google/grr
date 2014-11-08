<img src="https://raw.githubusercontent.com/google/grr/gh-pages/img/grr_logo_real_sm.png" />

GRR Rapid Response is an incident response framework focused on remote live forensics.

Links
-----

 * [Quickstart: Fast automated installation](https://github.com/google/grr-doc/blob/master/quickstart.adoc)
 * [Downloads](https://googledrive.com/host/0B1wsLqFoT7i2N3hveC1lSEpHUnM/)
 * [User Manual](https://github.com/google/grr-doc/blob/master/user_manual.adoc)
 * [Blog](http://grr-response.blogspot.com/)
 * [Administration Documentation (Setup and Configuration)](https://github.com/google/grr-doc/blob/master/admin.adoc)
 * [Publications: Papers, Presentations, Workshops etc.](https://github.com/google/grr-doc/blob/master/publications.adoc)
 * [Project FAQ](https://github.com/google/grr-doc/blob/master/faq.adoc)
 * [Developer and Implementation Documentation](https://github.com/google/grr-doc/blob/master/implementation.adoc)
 * [The GRR Configuration system](https://github.com/google/grr-doc/blob/master/configuration.adoc)
 * [Release Notes: check these when upgrading](https://github.com/google/grr-doc/blob/master/releasenotes.adoc)
 * [Project Roadmap](https://github.com/google/grr-doc/blob/master/roadmap.adoc)
 * [Search Documentation (using github search)](https://github.com/google/grr-doc)
 * [License Information](https://github.com/google/grr-doc/blob/master/licenses.adoc)
 * [Troubleshooting](https://github.com/google/grr-doc/blob/master/troubleshooting.adoc)

Mailing Lists
-------------

 * GRR Users: [grr-users](https://groups.google.com/forum/#!forum/grr-users)
 * GRR Developers: [grr-dev](https://groups.google.com/forum/#!forum/grr-dev)

Announcements
-------------

**Nov 5 2014**: We've got a great new logo, which you will see turning up in the admin UI soon.  It replaces [our long-standing unofficial logo](https://raw.githubusercontent.com/google/grr/gh-pages/img/grr_logo.png) :)

**Oct 28 2014**: We've started a blog as a supplement to the documentation.  Check out the first post on [how to set up the distributed datastore](http://grr-response.blogspot.com/2014/10/using-distributed-data-store-in-grr.html).

**Oct 15 2014**: We're now fully migrated to github. The code.google.com page
will just be a redirect here. Open issues, documentation and code have been
moved over, and we will only update this repository in the future.

Overview
--------

GRR consists of an agent (client) that can be deployed to a target system, and
server infrastructure that can manage and talk to the agent.<br>

Client Features:

 * Cross-platform support for Linux, Mac OS X and Windows clients.
 * Live remote memory analysis using open source memory drivers for Linux, Mac
   OS X and Windows, and the [Rekall](http://www.rekall-forensic.com/) memory
   analysis framework.
 * Powerful search and download capabilities for files and the Windows registry.
 * Secure communication infrastructure designed for Internet deployment.
 * Client automatic update support.
 * Detailed monitoring of client CPU, memory, IO usage and self-imposed
   limits.

Server Features:

 * Fully fledged response capabilities handling most incident response and
   forensics tasks.
 * OS-level and raw file system access, using the SleuthKit (TSK).
 * Enterprise hunting (searching across a fleet of machines) support.
 * Fully scaleable back-end to handle very large deployments.
 * Automated scheduling for recurring tasks.
 * Fast and simple collection of hundreds of digital forensic artifacts.
 * Asynchronous design allows future task scheduling for clients, designed to
   work with a large fleet of laptops.
 * Ajax Web UI.
 * Fully scriptable IPython console access.
 * Basic system timelining features.
 * Basic reporting infrastructure.

See [quickstart](https://github.com/google/grr-doc/blob/master/quickstart.adoc Quickstart) to start using it.

Screenshots
-----------
[<img src="http://wiki.grr.googlecode.com/git/Screenshot from 2013-11-18 18:36:13.png" width="140" height="80" />](http://wiki.grr.googlecode.com/git/Screenshot from 2013-11-18 18:36:13.png)
[<img src="http://wiki.grr.googlecode.com/git/Screenshot from 2013-11-18 18:36:46.png" width="140" height="80" />](http://wiki.grr.googlecode.com/git/Screenshot from 2013-11-18 18:36:46.png)
[<img src="http://wiki.grr.googlecode.com/git/Screenshot from 2013-11-18 18:37:37.png" width="140" height="80" />](http://wiki.grr.googlecode.com/git/Screenshot from 2013-11-18 18:37:37.png)
[<img src="http://wiki.grr.googlecode.com/git/Screenshot from 2013-11-18 18:40:49.png" width="140" height="80" />](http://wiki.grr.googlecode.com/git/Screenshot from 2013-11-18 18:40:49.png)
[<img src="http://wiki.grr.googlecode.com/git/Screenshot from 2013-11-18 18:41:45.png" width="140" height="80" />](http://wiki.grr.googlecode.com/git/Screenshot from 2013-11-18 18:41:45.png)
