#!/usr/bin/env python
import subprocess
import shlex
import json
import sys
import os
import re
"""
Katello registration data collector
===================================
Collect activation-keys and environment information to be used to register new
clients. See provided README.md for more informantion and instructions.
"""
__author__ = 'Blayne Campbell'
__date__ = '3/11/16'

# Settings Start ##############################################################
org_name = "Acme Corporation"  # Change to your Organization Name
output_directory = '/var/www/html/pub'  # full path to output data file
# Settings End ################################################################

# Change Directory to file path
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)


def hammer(query, org=None):
    """ Execute Hammer CLI for a given query.
    :param query: query
    :param org: organization 'Name'
    :return: json data
    """
    cmd = 'hammer --output=json %s' % query
    if org:
        cmd += ' --organization "%s"' % org
    output = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE)
    try:
        return json.loads(output.communicate()[0])
    except ValueError, error:
        sys.exit(error)

def publish(data, directory):
    output_file = os.path.join(directory, 'registration.json')
    with open(output_file, 'w') as f:
        json.dump(data, f)
    os.chmod(output_file, 0644)


def main():
    registration_data = []
    activation_keys = hammer('activation-key list', org_name)
    content_views = hammer('content-view list', org_name)
    environments = hammer('environment list', org_name)
    organization = hammer('organization info --name "%s"' % org_name)
    for activation_key in activation_keys:
        for content_view in content_views:
            if content_view['Name'] == activation_key['Content View']:
                activation_key['Content View Label'] = content_view['Label']
        for environment in environments:
            if re.search(r'(?=.*%s_\d*$)(?=.*%s.*)(?=.*%s.*)' % (
                    activation_key['Content View Label'],
                    activation_key['Lifecycle Environment'],
                    organization['Label']), environment['Name']):
                activation_key['Org'] = organization['Label']
                activation_key['Environment'] = environment['Name']
        # Cleanup Elements you do not need:
        del activation_key['ID']
        del activation_key['Host Limit']
        del activation_key['Content View']
        del activation_key['Content View Label']
        del activation_key['Lifecycle Environment']
        registration_data.append(activation_key)
    # print(json.dumps(registration_data, indent=4, sort_keys=True))
    publish(registration_data, output_directory)


if __name__ == '__main__':
    main()
