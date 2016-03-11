Katello/Satellite 6 Registration
================================

### Description
The goal of this project is to provide a system administrator the ability
to register a host to a Katello instance from the client side without the
need to knowing the activation-key and the auto-generated puppet environment
name created by Katello for the content-view associated with the content-view.

### Components
- Server Script
  Python script that lives on the Katello/Satellite servers and executed on
  a schedule via crontab. This script gathers a small set of data from 
  Katello via the Hammer CLI then publishes the data to a directory accessible
  to your nodes via HTTP.
- Client Script
  This script should be deployed to hosts that you would like to register 
  to your Katello/Satellite 6 instance. This script can be deployed as a
  standard item on all host deployments to assist in the event a host
  requires re-registered to a different Smart Proxy/Capsule or perhaps to
  switch to a different activation-key/environment.

#### Server Setup
`register_server.py` should be configured on each Katello/Satellite 6 instance
to run as a cron task. This script will collect all available activation-keys,
and relevant puppet environments and publish them to a json file in the standard
apache pub directory. This communication happens over port 80 which is a required
port for a Katello/Satellite implimentation. 

*Note: If you concider you activation keys and environment names a secret affair,
you may want to investigate other options. That said, we are under the assumption that
the your Satellite implimentation is behind firewalls on a private network.*


#### Client Setup
`register.py` can be deployed to any directory on the client host.
You will need to update the following settings to suit your environment:
- tbd
- tbd

#### Host Compatability

Servers OS | Service Version 
-----------|----------------
CentOS 7   | Katello 2.4
RHEL 7.2   | Satellite 6.1.7


Client OS | Python Version
----------|----------------
CentOS 5  | 2.4.3
CentOS 6  | 2.6.6
CentOS 7  | 2.7.5
RHEL 5.11 | 2.4.3
RHEL 6.7  | 2.6.6
RHEL 7.2  | 2.7.5

#### TODO

