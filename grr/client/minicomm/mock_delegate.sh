#!/bin/bash

# Performs scripted actions according to $1. Mostly these actions simulate
# various delegate misbehaviors.

case "$1" in
  # Simple error on startup.
  startup-error)
    >&2 echo "Subprocess Error"
    exit 1
    ;;
  # Write garbage to stdout
  garbage-out)
    while :
    do
      echo "I'm sending garbage, lots and lots of garbage."
      sleep 1
    done
    ;;
  # Sleep for a long time (beyond any reasonable unit test timeout).
  sleepy)
    for i in `seq 1 10000`;
    do 
      sleep 1
    done
    ;;
  loop-back)
    cat
    ;;
  *)
    echo "Unrecognized command."
    ;;
esac
