#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Program to create an ansible inventory from all the deployments, jobs and
instances managed by a BOSH Director.
"""
# Python 2 and 3 compatibility
from __future__ import unicode_literals, print_function

__program__ = "bosh-inventory"
__version__ = "0.3.0"
__author__ = "Jose Riguera"
__year__ = "2017"
__email__ = "<jose.riguera@springer.com>"
__license__ = "MIT"
__purpose__ = """
In order to use it, you have to define BOSH_CONFIG environment variable
pointing to the configuration file used by Bosh. It will read the credentials
from the file. You can define additional inventory parameters with
BOSH_ANSIBLE_INVENTORY_PARAMS environment variable, for example:
BOSH_ANSIBLE_INVENTORY_PARAMS="ansible_user=vcap ansible_ssh_pass=blabla"
Be aware that Python is not present in the default location, but you can
use this variable to specify "ansible_python_interpreter=/path/to/python".

The environment variable BOSH_ANSIBLE_INVENTORY_VARS defines a list of
entries which can appear in the inventory as variables for each VM. The
list of values is here:
https://bosh.io/docs/director-api-v1.html#list-instances-detailed,
for example BOSH_ANSIBLE_INVENTORY_VARS="state bootstrap" will add
"state=started bootstrap=false" to each inventory entry.

The environment variable BOSH_ANSIBLE_INVENTORY_INSTANCES, defines the name will
appear in the inventory. If it 'dns' it will build the inventory with the
dns names given by Bosh Director, if 'vm_cid' (default) it will be using the
name of the VM as it is in the IaaS. You can see all parameters supported in
https://bosh.io/docs/director-api-v1.html#list-instances-detailed

In case of 'dns' the IP of each vm will be include if DNS is not defined in
Bosh Director. To force always the inclusion of the IP in the inventory, 
just define the variable BOSH_ANSIBLE_INVENTORY_IP as a positive integer 
indicating the index (starting from 1) of the IP which will be taken 
(for VMs with multiple IPs), 0 will disable the feature.

BOSH_ANSIBLE_INVENTORY_CALL can be 'instances'(default) or 'vms'. 
Instances is faster because it does not query the Bosh Agents, it gets the
desired state. 'vms' will query the Bosh Agents in order to result the current
state, so depending on the situation, it can take a lot of time to get the
result. 'instances' includes references to errand jobs, but 'vms' will only show
vms runnign on the IaaS.

You can also limit the inventory to one deployment by setting the value
of the environment variable BOSH_ANSIBLE_DEPLOYMENT to the name of it.
"""
import sys
import os
import time
import argparse
import json
import yaml
import requests
from collections import OrderedDict
try:
    # Python 3.x
    from io import StringIO
except ImportError:
    # Python 2.x
    #from StringIO import StringIO
    from io import BytesIO as StringIO
try:
    # Python 3.x
    from urllib.parse import urlparse
except ImportError:
    # Python 2.x
    from urlparse import urlparse
# Disable HTTPS warning with self signed certs
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)



def get_instances(session, api, deployment, method, timeout=60):
    result = []
    instances_url = api + '/deployments/{name}/' + str(method)
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


def create_inventory(session, api, target_deployment=None, ip=1,
                     inventory_instances='dns', variables=[], params=[],
                     method="instances"):
    deployments = get_deployments(session, api)
    inventory = OrderedDict()
    inventory["_meta"] = {}
    inventory["_meta"]["hostvars"] = {}
    for deployment in deployments:
        name = deployment['name']
        if target_deployment and target_deployment != name:
            continue
        inventory[name] = {}
        inventory[name]["children"] = []
        instances = get_instances(session, api, deployment, method)
        for instance in json.loads(instances):
            job = str(instance['job_name'])
            if job not in inventory:
                inventory[job] = {}
                inventory[job]["children"] = []
                inventory[name]["children"].append(job)
            if not 'hosts' in inventory[job]:
                inventory[job]["hosts"] = []
            # check if the job has a proper vm
            if instance['vm_cid'] != None:
                # With ip, where ip represents an index in the list
                # If it is zero, it is disabled.
                try:
                    if isinstance(instance[inventory_instances], list):
                        entry = str(instance[inventory_instances][0])
                    else:
                        entry = str(instance[inventory_instances])
                except:
                    entry = job + '-' + str(instance['index'])
                inventory["_meta"]["hostvars"][entry] = {}
                if ip:
                    try:
                        inv_ip = instance['ips'][ip - 1]
                    except:
                        msg = "IP index out of range (%s) for %s" % (ip-1, entry)
                        print("WARNING: " + msg, file=sys.stderr)
                        inv_ip = instance['ips'][0]
                    inventory["_meta"]["hostvars"][entry]['ansible_host'] = inv_ip
                inventory[job]["hosts"].append(entry)
                for variable in variables:
                    try:
                        inventory["_meta"]["hostvars"][entry][str(variable)] = str(instance[variable])
                    except:
                        pass
                for item in params:
                    param = item.split('=')
                    inventory["_meta"]["hostvars"][entry][param[0]] = param[1]
    return json.dumps(inventory, sort_keys=False, indent=2)


def create_ini(session, api, target_deployment=None, ip=1,
               inventory_instances='dns', variables=[], params=[],
               method="instances"):
    deployments = get_deployments(session, api)
    inventory = OrderedDict()
    inventory["[all:children]"] = []
    for deployment in deployments:
        name = deployment['name']
        if target_deployment and target_deployment != name:
            continue
        inventory["[all:children]"].append(name)
        inventory["[%s:children]" % name] = []
        instances = get_instances(session, api, deployment, method)
        for instance in json.loads(instances):
            job = str(instance['job_name'])
            job_key = "[%s]" % job
            if job_key not in inventory:
                inventory[job_key] = []
                inventory["[%s:children]" % name].append(job)
            # check if the job has a proper vm
            if instance['vm_cid'] != None:
                # With ip, where ip represents an index in the list
                # If it is zero, it will be disabled disabled.
                try:
                    if isinstance(instance[inventory_instances], list):
                        entry = instance[inventory_instances][0]
                    else:
                        entry = instance[inventory_instances]
                except:
                    entry = job + '-' + str(instance['index'])
                if ip:
                    try:
                        entry = entry + ' ansible_host=' + instance['ips'][ip - 1]
                    except:
                        msg = "IP index %d not found for %s" % (ip-1, entry)
                        print("WARNING: " + msg, file=sys.stderr)
                        try:
                            entry = entry + ' ansible_host=' + instance['ips'][0]
                        except:
                            print("WARNING: IP not found for %s" % (entry), file=sys.stderr)
                for variable in variables:
                    try:
                        entry = entry + " %s='%s'" % (variable, instance[variable])
                    except:
                        pass
                entry = entry + ' ' + ' '.join(params)
                inventory[job_key].append(entry)
    output = StringIO()
    for key in inventory:
        items = inventory[key]
        print(key.decode('utf-8'), file=output)
        for item in inventory[key]:
            print(item.decode('utf-8'), file=output)
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
    except Exception as e:
        print("ERROR loading environment variable BOSH_CONFIG: %s" % str(e), file=sys.stderr)
        sys.exit(1)
    target = bosh_config['target']
    ca_cert = bosh_config['ca_cert'][target]
    username = bosh_config['auth'][target]['username']
    password = bosh_config['auth'][target]['password']
    # Read other parameters for the inventory
    inventory_params = os.getenv('BOSH_ANSIBLE_INVENTORY_PARAMS', '').split()
    inventory_variables = os.getenv('BOSH_ANSIBLE_INVENTORY_VARS', '').split()
    bosh_method = os.getenv('BOSH_ANSIBLE_INVENTORY_CALL', 'instances')
    if bosh_method not in ['instances', 'vms']:
        msg = "BOSH_ANSIBLE_INVENTORY_CALL must be 'instances' or 'vms'"
        print("ERROR: " + msg, file=sys.stderr)
        bosh_method = 'instances'
    target_deployment = os.getenv('BOSH_ANSIBLE_DEPLOYMENT', None)
    try:
        inventory_ip = abs(int(os.getenv('BOSH_ANSIBLE_INVENTORY_IP', '0')))
    except:
        msg = "BOSH_ANSIBLE_INVENTORY_IP must be positive integer, 0 to disable"
        print("ERROR: " + msg, file=sys.stderr)
        inventory_ip = 0
    try:
        inventory_instances = os.getenv('BOSH_ANSIBLE_INVENTORY_INSTANCES', 'dns')
    except:
        msg = "BOSH_ANSIBLE_INVENTORY_INSTANCES must be 'dns', 'vm_cid' ..."
        print("ERROR: " + msg, file=sys.stderr)
        inventory_instances = 'dns'
    # create a session
    session = requests.Session()
    session.auth = (username, password)
    session.verify = True if ca_cert else False
    session.cert = ca_cert if ca_cert else None
    # Doing the job
    if args.list:
        print(create_inventory(
            session, target, target_deployment, inventory_ip,
            inventory_instances, inventory_variables, inventory_params,
            bosh_method)
        )
    else:
        print(create_ini(
            session, target, target_deployment, inventory_ip, 
            inventory_instances, inventory_variables, inventory_params,
            bosh_method)
        )
    sys.exit(0)


if __name__ == "__main__":
    main()

