The GRR Nanny
=============

The GRR Nanny is a minimalist program which monitors the GRR client program (as
a child) for safety. If the child misbehaves (e.g. locks up or crashes), the
nanny ensures it is restarted.

The Nanny is supposed to run as a service and communicates with the child via a
platform specific heartbeat mechanism. The child write the current timestamp
into a shared heartbeat resource (e.g. a windows registry key or file), while
the nanny checks that this timestamp is constantly incremented. If the child
fails to record a heartbeat, the nanny kills the child, and then restarts it.

In many use cases (e.g. a service running under windows), there is no command
line available for the service, and therefore the nanny behaviour is not
configured via command line parameters. The behaviour is built into the client
as a static instance of a struct ControllerConfig:

struct ControllerConfig {

  // Number of seconds the child must remain dead after a failure to produce a
  // heartbeat is detected.
  int resurrection_period;

  // The maximum number of seconds since the last child heartbeat. The child
  // will be killed if this is reached.
  int unresponsive_kill_period;

  // Identical messages are suppressed in the event log for this many seconds.
  int event_log_message_suppression;
};

The child controller implements the policy about when the child should be
started and killed. Unresponsive children are killed after the
unresponsive_kill_period and restarted after the resurrection_period. For example
this is an example timeline:


|<=Child started         |<=Child killed            |<=Child started.
-------------------------------------------------------------------->
|<---------------------->|  resurrection_period
unresponsive_kill_period |<------------------------>|

Children are restarted no more frequently than the resurrection_period, but we
do not tolerate a child that does not produce a heart beat more frequently than
the unresponsive_kill_period. The child will be killed but not restarted before
the resurrection_period.

