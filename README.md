Katello/Satellite 6 Registration
================================

## Description
Provides a semi-automated Katello registration and basic puppet configuration. 
The `register.py` script can be run stand-alone or with the included server-side 
script which will remove the need to remember/type a long activation-key or cryptic
(Katello auto-generated) puppet environment names. 

## Components
#### `generate_registration_data.py`  
Should be configured as a cronjob on each Katello/Satellite6 instance 
The script will collect all available activation-keys, and relevant
puppet environments for an organization and publishes them as a json
along side the ca-consumer package in the apache `http://<server-url>/pub`
directory.

You will need to update the following settings to suit your environment:
- org_name - Organization 'Name' of which to export activation-keys & puppet environments

#### `register.py` 
Client side script that can be deployed to any directory on client hosts.  
This script will perform the following:
 - Append a host record to /etc/hosts for the chosen Katello instance
 - Perform connectivity tests for required network ports
 - Install the ca-consumer package for the chosen Katello instance
 - Perform subscription-manager registration
 - Install client packages (katello-agent, puppet)
 - Configure Puppet using a puppet.conf template
 - Execute Puppet run to generate client/server certificate exchange
 - Enable/Start Puppet service

Customize the following settings to suit your environment:
- katello_servers - specify Katello/Satellite servers
- puppet_configuration_template - customize to your needs (default: noop true)

## Compatability

Servers OS | Service Version 
-----------|----------------
RHEL 7.2   | Satellite 6.1.9


Client OS | Python Version
----------|----------------
RHEL 5.11 | 2.4.3
RHEL 6.7  | 2.6.6
RHEL 7.2  | 2.7.5

## TODO
-
-
-

