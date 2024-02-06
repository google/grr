
# End-to-end test require a user on a client, which e.g. sets the
# home directory for file collection.

useradd -m testuser &&
echo "[7] [01234] [ts/3] [testuser] [pts/3       ] [100.100.10.10       ] [100.100.10.10  ] [Thu Jan 01 00:00:00 1970 UTC]" > wtmp.txt && \
    utmpdump /var/log/wtmp >> wtmp.txt && \
    utmpdump --reverse < wtmp.txt > /var/log/wtmp && \
    utmpdump /var/log/wtmp
