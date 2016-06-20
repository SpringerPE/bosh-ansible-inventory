#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Program to create an ansible inventory from all the deployments, jobs and
instances managed by a BOSH Director.
"""
# Python 2 and 3 compatibility
from __future__ import unicode_literals, print_function

__program__ = "bosh-inventory"
__version__ = "v0.1.0"
__author__ = "Jose Riguera"
__year__ = "2016"
__email__ = "<jose.riguera@springer-sbm.com>"
__license__ = "MIT"
__purpose__ = """
In order to use it, you have to define BOSH_CONFIG environment variable
pointing to the configuration file used by Bosh. It will read the credentials
from the file. You can define additional inventory parameters with
BOSH_ANSIBLE_INVENTORY_PARAMS environment variable, for example:
BOSH_ANSIBLE_INVENTORY_PARAMS="ansible_user=vcap ansible_ssh_pass=blabla"
"""
import sys
import os
import time
import argparse
import urllib3
urllib3.disable_warnings()

from urlparse import urlparse
from collections import OrderedDict
import json
import yaml
import requests
import StringIO



def get_instances(session, api, deployment, timeout=60):
    result = []
    instances_url = api + '/deployments/{name}/vms'
    instances_url = instances_url.format(**deployment)
    instances_req = session.get(instances_url,
        params={'format': 'full'},
        allow_redirects=False)
    if instances_req.status_code != 302:
        return result
    task_url = api + urlparse(instances_req.headers['Location']).path
    status = '-'
    while status != 'done':
        instances_status_req = session.get(task_url)
        if instances_status_req.status_code != 200:
            break
        status = instances_status_req.json()['state']
        if timeout > 0:
            timeout -= 1
            time.sleep(1)
        else:
            break
    else:
        output_url =  task_url + '/output'
        instances_out_req = session.get( output_url,
            headers={'Accept': 'text/plain'},
            params={'type': 'result'})
        if instances_out_req.status_code == 200:
            for line in instances_out_req.text.splitlines():
                result.append(json.loads(line))
    return json.dumps(result)


def get_deployments(session, api):
    result = []
    deployments_url = api + '/deployments'
    deployments_req = session.get(deployments_url)
    if deployments_req.status_code == 200:
        result = deployments_req.json()
    return result


def create_inventory(session, api, params=[]):
    deployments = get_deployments(session, api)
    inventory = OrderedDict()
    inventory["_meta"] = {}
    inventory["_meta"]["hostvars"] = {}
    for deployment in deployments:
        name = deployment['name']
        inventory[name] = {}
        inventory[name]["children"] = []
        instances = get_instances(session, api, deployment)
        for instance in json.loads(instances):
            job = instance['job_name']
            if job not in inventory:
                inventory[job] = {}
                inventory[job]["children"] = []
                inventory[name]["children"].append(job)
            if not 'hosts' in inventory[job]:
                inventory[job]["hosts"] = []
            try:
                entry = instance['dns'][0]
                inventory["_meta"]["hostvars"][entry] = {}
            except:
                entry = job + '-' + str(instance['index'])
                inventory["_meta"]["hostvars"][entry] = {}
                inventory["_meta"]["hostvars"][entry]['ansible_host'] = instance['ips'][0]
            inventory[job]["hosts"].append(entry)
            for item in params:
                param = item.split('=') 
                inventory["_meta"]["hostvars"][entry][param[0]] = param[1]
    return json.dumps(inventory, sort_keys=False, indent=2)


def create_ini(session, api, params=[]):
    deployments = get_deployments(session, api)
    inventory = OrderedDict()
    inventory["[all:children]"] = []
    for deployment in deployments:
        name = deployment['name']
        inventory["[all:children]"].append(name)
        inventory["[%s:children]" % name] = []
        instances = get_instances(session, api, deployment)
        for instance in json.loads(instances):
            job = instance['job_name']
            job_key = "[%s]" % job
            if job_key not in inventory:
                inventory[job_key] = []
                inventory["[%s:children]" % name].append(job)
            try:
                entry = instance['dns'][0]
            except:
                dns = job + '-' + str(instance['index'])
                entry = dns + ' ansible_host=' + instance['ips'][0]
            entry = entry + ' ' + ' '.join(params)
            inventory[job_key].append(entry)
    output = StringIO.StringIO()
    for key in inventory:
        items = inventory[key]
        print(key, file=output)
        for item in inventory[key]:
            print(item, file=output)
        print('', file=output)
    content = output.getvalue()
    output.close()
    return content


def main():
    # Argument parsing
    epilog = __purpose__ + '\n'
    epilog += __version__ + ', ' + __year__ + ' '
    epilog += __author__ + ' ' + __email__
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter,
        description=__doc__, epilog=epilog)
    parser.add_argument(
        '--list', action='store_true', default=False,
         help='Enable JSON output for dynamic ansible inventory')
    args = parser.parse_args()
    try:
        bosh_config_file = os.environ['BOSH_CONFIG']
        with open(bosh_config_file, 'r') as stream:
            bosh_config = yaml.load(stream)
    except:
        print('ERROR: BOSH_CONFIG not defined!', file=sys.stderr)
        parser.print_help()
        sys.exit(1)
    target = bosh_config['target']
    ca_cert = bosh_config['ca_cert'][target]
    username = bosh_config['auth'][target]['username']
    password = bosh_config['auth'][target]['password']
    # Read other parameters for the inventory
    inventory_params = os.getenv('BOSH_ANSIBLE_INVENTORY_PARAMS', '').split()
    # create a session
    session = requests.Session()
    session.auth = (username, password)
    session.verify = True if ca_cert else False
    session.cert = ca_cert if ca_cert else None
    # Doing the job
    if args.list:
        print(create_inventory(session, target, inventory_params))
    else:
        print(create_ini(session, target, inventory_params))
    sys.exit(0)


if __name__ == "__main__":
    main()

