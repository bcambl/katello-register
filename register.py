#!/usr/bin/env python
from distutils.spawn import find_executable
from rpm import TransactionSet
from datetime import datetime
import subprocess
import socket
import urllib
import shlex
import sys
import os
import re
"""
Katello Client Registration Script
==================================
Register a host to a Katello/Satellite 6 Server.

Notes:
 - Script should use old-style file open/close to support RHEL5 (python 2.4.3)
 - Strings should use old-style '%s' formatting to support RHEL5 (python 2.4.3)

"""
__author__ = 'Blayne Campbell'
__date__ = '2016-06-06'


# Settings Start ##############################################################
katello_servers = [
    {'hostname': 'katello',
     'fqdn': 'katello.example.com',
     'ip': '11.22.33.44'
     },
    {'hostname': 'satellite',
     'fqdn': 'satellite.example.com',
     'ip': '55.66.77.88'
     }
]

required_ports = [
    {'port': 80, 'description': 'HTTP'},
    {'port': 443, 'description': 'HTTPS'},
    {'port': 5647, 'description': 'katello/Qpid'},
    {'port': 8140, 'description': 'Puppet'}
]

puppet_configuration_template = """
[main]
vardir = /var/lib/puppet
logdir = /var/log/puppet
rundir = /var/run/puppet
ssldir = $vardir/ssl

[agent]
pluginsync      = true
report          = true
ignoreschedules = true
daemon          = false
noop            = %s
ca_server       = %s
certname        = %s
server          = %s
environment     = %s

"""
# Settings End ################################################################

try:
    import json
except ImportError:
    import simplejson as json
try:
    input = raw_input
except NameError:
    pass


def run_command(command):
    """ Command wrapper function
    :param command: command to execute as string
    """
    try:
        subprocess.call(shlex.split(command.encode('ascii')))
    except Exception, e:
        sys.exit(e)


def determine_fqdn():
    """ Subscription Manager and Puppet determine the FQDN of a host
    differently. This function is to provide an consistent FQDN to be
    use for both subscription-manager and puppet.
    """
    hostname, domain, fqdn = None, None, None
    # first we will attempt to find the domain via /etc/resolv.conf
    with open('/etc/resolv.conf', 'r') as resolv_conf:
        for line in resolv_conf.readlines():
            if re.search(r'^domain', line):
                domain = line.split()[1]
                break
    # second we will retrieve the primary hostname (non-alias)
    hostname = str(socket.gethostname()).split('.')[0]
    if hostname and domain:
        fqdn = '%s.%s' % (hostname, domain)
    if not fqdn:
        # if we were unable to determine both a hostname and domain
        # above, we will resort to using the fqdn provided by the
        # socket library. The problem with using this is that getfqdn()
        # will return the first FQDN found even if it is based on an alias.
        fqdn = socket.getfqdn()
    return fqdn


def select_katello_server(katello_servers=None):
    server_choices = dict((k, v) for k, v in enumerate(katello_servers))
    while True:
        print("\nSelect Satellite Server:")
        for k, v in enumerate(katello_servers):
            print('%s - %s' % (k + 1, v['fqdn']))
        try:
            choice = int(input('Selection #: '))
            choice -= 1
        except ValueError:
            print('Invalid entry.. Please provide a # from above choices.')
            continue
        if choice in server_choices:
            satellite = server_choices[choice]
            print('Registering to Katello Server: %s' % satellite['fqdn'])
            break
        else:
            print('Option %s does not exist, '
                  'select # from above choices.' % str(choice + 1))
    return satellite


def test_katello_connection(server=None, ports=None, timeout=5):
    """ Check network port connectivity to proposed Satellite server.
    :param server: dict of Satellite server information
    :param ports: Required posts specified via settings
    :param timeout: time to wait before declaring a timeout
    """
    errors_found = int()
    for port in ports:
        try:
            s = socket.socket()
            s.settimeout(timeout)
            s.connect((server['fqdn'], port['port']))
            print('Connection to %s on port %s: SUCCESS!'
                  % (server['fqdn'], str(port['port'])))
        except Exception, e:
            errors_found += 1
            print('Connection to %s on port %s: ERROR (Required for %s)'
                  % (server['fqdn'], str(port['port']), port['description']))
    if errors_found:
        print('\nFound %s connection issues.. (See above)' % str(errors_found))
        ignore_errors = input('Continue anyways? [y/N]: ')
        if ignore_errors in ['Y', 'y']:
            print('Continuing with connection errors..')
        else:
            sys.exit('Exiting due to %s connection issues' % errors_found)


def get_available_activation_key(server=None):
    try:
        location = 'http://%s/pub/registration.json' % server['fqdn']
        response = urllib.urlopen(location)
        activation_keys = json.loads(response.read())
        return activation_keys
    except:
        print('\nError retrieving activiation keys from %s' % server['fqdn'])
        activation_key_org = input('\nPlease provide an organization label: ')
        activation_key_name = input('\nPlease provide an activation key: ')
        puppet_environment = input('\nPlease provide a puppet environment: ')
        activation_key = {
            "Org": activation_key_org,
            "Name": activation_key_name,
            "Environment": puppet_environment
        }
        return activation_key


def choose_activation_key(available_keys=None):
    if isinstance(available_keys, dict):
        return available_keys
    activation_key_choices = dict((k, v) for k, v in enumerate(available_keys))
    while True:
        print("\nSelect an Activation Key:")
        for k, v in enumerate(available_keys):
            print('%s - %s' % (k + 1, v['Name']))
        try:
            choice = int(input('Selection #: '))
            choice -= 1
        except ValueError:
            print('Invalid entry.. Please provide a # from above choices.')
            continue
        if choice in activation_key_choices:
            activation_key = activation_key_choices[choice]
            print('You chose: %s' % activation_key['Name'])
            break
        else:
            print('Option %s does not exist, '
                  'select # from above choices.' % str(choice + 1))
    return activation_key


def update_hosts_file(server=None):
    """ Check for existing /etc/hosts record and add if not found
    """
    try:
        all_host_records = open('/etc/hosts', 'r').read()
        if re.search(r'%s' % server['fqdn'], all_host_records, re.IGNORECASE):
            print("Host file entry for %s already exists.." % server['fqdn'])
        else:
            print("Adding host file entry for %s.." % server['fqdn'])
            record = "\n%s\t%s %s\n" \
                     % (server['ip'], server['fqdn'], server['hostname'])
            append_katello_host = open('/etc/hosts', 'a')
            append_katello_host.write(record)
            append_katello_host.close()
    except IOError, e:
        sys.exit(e)


def backup_configuration(file_path=None):
    """ Re-usable backup function to backup configurations/files with current
    timestamp appended.
    :param file_path: full path of the file to backup
    """
    date = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    try:
        if os.path.exists(file_path):
            print("Found existing configuration file: %s" % file_path)
            try:
                os.rename(file_path, '%s.backup-%s' % (file_path, date))
                print('Backup created: %s.backup-%s' % (file_path, date))
            except OSError, e:
                sys.exit("Unable to backup %s: %s" % (file_path, e))
    except OSError as e:
        print("Unable to backup %s: File does not Exist!")


def install_consumer_package(server=None):
    """ Remove existing consumer package and install latest from the server
    """
    remove_package = None
    ts = TransactionSet()
    print("\nChecking for existing Katello ca-consumer package..")
    for i in ts.dbMatch():
        if re.search(r'katello-ca-consumer', i['name']):
            remove_package = i['name']
    if remove_package:
        print("Found existing Katello ca-consumer package installed.")
        print("Removing package: %s" % remove_package)
        run_command('%s -e %s' % (find_executable('rpm'), remove_package))
    print('Installing Katello ca-consumer package from %s' % server['fqdn'])
    consumer_package = 'katello-ca-consumer-latest.noarch.rpm'
    run_command('%s -Uvh http://%s/pub/%s' % (find_executable('rpm'),
                                              server['fqdn'],
                                              consumer_package))


def deploy_rhsm_hostname_fact_override():
    """ Deploy /etc/rhsm/facts/katello.facts with hostname override(s)
    Typically subscription-manager will attempt to register a new host
    using the subscription-manager fact: network.hostname. This would sometimes
    cause duplicate hosts in Satellite due to a 'Host' and 'Content Host'
    hostname mis-match. This was addressed by implementing the new fact
    network.hostname-override. Unfortunately this solution is only partially
    implemented and subscription-manager is still using network.hostname.
    We will override both facts to avoid any complications.
    """
    katello_fact_file = '/etc/rhsm/facts/katello.facts'
    fact_data = {}
    # Read/preserve existing fact overrides if the file exists
    if os.path.exists(katello_fact_file):
        fact_file = open(katello_fact_file, 'r')
        fact_data = json.loads(fact_file.read())
        fact_file.close()
    host_fqdn = determine_fqdn()
    # override subscription-manager facts
    fact_data['network.fqdn'] = host_fqdn
    fact_data['network.hostname'] = host_fqdn
    fact_data['network.hostname-override'] = host_fqdn
    # print the latest fact overrides to stdout
    print('\nConfiguring subscription-manager fact overrides:')
    for k, v in fact_data.items():
        print("%s: %s" % (k, v))
    # write the file with new fact data
    fact_file = open(katello_fact_file, 'w')
    fact_file.write(json.dumps(fact_data))
    fact_file.close()


def katello_register(activation_key=None):
    print('\nUn-Registering from current Satellite server:')
    run_command('%s unregister' % find_executable('subscription-manager'))
    print('cleaning up local subscription data:')
    run_command('%s clean' % find_executable('subscription-manager'))
    registration = '%s register --org="%s" --activationkey="%s"' \
        % (find_executable('subscription-manager'),
           activation_key['Org'],
           activation_key['Name'])
    print("\nRegistering server with command:\n %s\n" % registration)
    run_command(registration)


def install_packages():
    packages = ['katello-agent', 'puppet']
    run_command('%s -y install %s'
                % (find_executable('yum'), ' '.join(packages)))


def configure_puppet(server=None, activation_key=None, noop='true'):
    template = puppet_configuration_template % (noop,
                                                server['fqdn'],
                                                determine_fqdn(),
                                                server['fqdn'],
                                                activation_key['Environment'])
    try:
        f = open('/etc/puppet/puppet.conf', 'w')
        f.write(template)
        f.close()
        print("Wrote puppet configuration to /etc/puppet/puppet.conf")
    except IOError, e:
        sys.exit(e)


def puppet_cleanup_prompt():
    puppet_ssl_path = '/var/lib/puppet/ssl'
    if not os.path.exists(puppet_ssl_path):
        return
    print("\nExisting Puppet client certificate detected..\n"
          "Would you like to cleanup/remove the local Puppet certificates?\n"
          "This is typically only required to register with a new Satellite.\n"
          "Note: You will prompted to clean the cert from Satellite manually.")
    choice = input("Choose [N/y]: ")
    if choice in ['Y', 'y', 'yes']:
        return True


def puppet_noop_prompt():
    """ Prompt user as to whether puppet should be configured in 'noop' mode.
    Default: noop = true
    """
    noop = 'true'
    print("\nBy default Puppet will be configured to NOT apply changes to\n"
          "the host in attempt to protect against accidental puppet changes.\n"
          "This can be modified at anytime via /etc/puppet/puppet.conf\n"
          "Default: noop = true\n"
          "\nAllow Puppet to apply changes to host? (ie: set noop = false)")
    choice = input("Choose [N/y]: ")
    if choice in ['Y', 'y', 'yes']:
        noop = 'false'
    return noop


def delete_old_puppet_certificate():
    puppet_ssl_path = '/var/lib/puppet/ssl'
    if os.path.exists(puppet_ssl_path):
        print("found %s, removing.." % puppet_ssl_path)
        run_command('%s -rf %s' % (find_executable('rm'), puppet_ssl_path))
        print("Successfully removed Puppet client cert: %s" % puppet_ssl_path)
    else:
        print("%s not found.. Skipping puppet cert cleanup." % puppet_ssl_path)


def puppet_run():
    run_command('%s agent -t' % find_executable('puppet'))


def enable_services():
    if find_executable('systemctl'):
        try:
            run_command('%s enable puppet' % find_executable('systemctl'))
            run_command('%s start puppet' % find_executable('systemctl'))
            print('\nPuppet enabled/started via chkconfig/service\n')
        except Exception, e:
            print("Error Enabling Puppet Service: %s" % e)
    else:
        try:
            run_command('%s puppet on' % find_executable('chkconfig'))
            run_command('%s puppet start' % find_executable('service'))
            print('\nPuppet enabled/started via systemctl\n')
        except:
            print("Error Enabling Puppet Service: %s" % e)


def main():
    try:
        katello_server = select_katello_server(katello_servers)
        update_hosts_file(server=katello_server)
        test_katello_connection(server=katello_server, ports=required_ports)
        available_keys = get_available_activation_key(katello_server)
        activation_key = choose_activation_key(available_keys)
        cleanup_puppet_ssl = puppet_cleanup_prompt()
        puppet_noop_state = puppet_noop_prompt()
        install_consumer_package(server=katello_server)
        deploy_rhsm_hostname_fact_override()
        katello_register(activation_key=activation_key)
        install_packages()
        backup_configuration(file_path='/etc/puppet/puppet.conf')
        configure_puppet(noop=puppet_noop_state,
                         server=katello_server,
                         activation_key=activation_key)
        if cleanup_puppet_ssl:
            delete_old_puppet_certificate()
        puppet_run()
        enable_services()
    except KeyboardInterrupt:
        try:
            subprocess.call(shlex.split(find_executable('reset')))
        except Exception, e:
            sys.exit("Unable to reset terminal..")
        print("CTRL+C Detected.. Exiting Script.")


if __name__ == "__main__":
    main()
