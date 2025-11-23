# Locations of log files

## Genieacs

The GenieACS logs are located at:

- CWMP access logs: /var/log/genieacs/genieacs-cwmp-access.log
- NBI access logs: /var/log/genieacs/genieacs-nbi-access.log
- Debug logs: /var/log/genieacs/genieacs-debug.yaml

## Router TR-069 proxy

We implemented a proxy in the router container to be able to log TR-069 messages for debugging. The logs can be found at:

- TR-069 logs: /var/log/tr069-proxy.log

