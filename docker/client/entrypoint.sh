#!/bin/bash
dpkg -i /installers/*.deb

./usr/bin/fleetspeak-client \
    -alsologtostderr \
    -std_forward \
    -config /configs/client.config