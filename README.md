# bosh-ansible-inventory

Ansible 2 dynamic inventory

# Usage

You can install it by running `setup.py`:
```
$ python setup.py install
```

or using `pip`:

```
$ pip install bosh_inventory
```

Also, you can copy and run it directly by calling the program 
`bosh_inventory.py` instead of `bosh-inventory`.


Once it is installed:

```
$ bosh-inventory  --help
usage: bosh-inventory [-h] [--list]

Program to create an ansible inventory from all the deployments, jobs and
instances managed by a BOSH Director.

optional arguments:
  -h, --help  show this help message and exit
  --list      Enable JSON output for dynamic ansible inventory

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

0.3.0, 2017 Jose Riguera <jose.riguera@springer.com>
```

To use it, just point the env variable `BOSH_CONFIG` to your
bosh configuration. It will read all parameters from there.


By default, it will return an INI format inventory:
```
$ export BOSH_CONFIG=~/.bosh_config
$ bosh-inventory > ansible-inventory
```

Or using directly with ansible:
```
$ export BOSH_CONFIG=~/.bosh_config
$ export BOSH_ANSIBLE_INVENTORY_PARAMS="ansible_user=vcap"
$ export BOSH_ANSIBLE_INVENTORY_VARS="ansible_user=vcap"
$ export BOSH_ANSIBLE_INVENTORY_CALL="vms"
$ export BOSH_ANSIBLE_INVENTORY_INSTANCES="dns"
$ export BOSH_ANSIBLE_INVENTORY_IP="1"
$ ansible "runner_z*" -i $(which bosh-inventory) -a "sudo /sbin/reboot"
```

You can also point to one deployment by using `BOSH_ANSIBLE_DEPLOYMENT`,
and only those instances will appear:
```
$ export BOSH_ANSIBLE_DEPLOYMENT=concourse
$ bosh-inventory
[all:children]
concourse

[concourse:children]
web
worker
db

[web]
web-0 ansible_host=10.10.10.64 ansible_user=vcap

[worker]
worker-0 ansible_host=10.10.10.66 ansible_user=vcap
worker-1 ansible_host=10.10.10.67 ansible_user=vcap

[db]
db-0 ansible_host=10.10.10.65 ansible_user=vcap

```

Be aware that python is not present in the default location, but you can 
define it by using `BOSH_ANSIBLE_INVENTORY_PARAMS="ansible_python_interpreter=/path/to/python"`


# Example: apply a playbook to all CF runners

First of all, make sure your bosh client is targeting the correct Bosh Director!!!!

```
bosh status

https://x.x.x.x:25555
Config
             /home/jriguera/.bosh_config

Director
  Name       devBosh2
  URL        https://x.x.x.x:25555
  Version    1.3232.6.0 (00000000)
  User       admin
  UUID       c4f5c583-1bc3-427f-8ded-b3f5e107f970
  CPI        vsphere
  dns        enabled (domain_name: microbosh)
  compiled_package_cache disabled
  snapshots  disabled

Deployment
  not set
```

Type `bosh vms --details` to confirm!

`bosh-inventory` needs some variables to work:

```
# Point to the bosh config targeting the desired director!
export BOSH_CONFIG=~/.bosh_config
# Define the name of the deployment (to avoid getting other vms)
export BOSH_ANSIBLE_DEPLOYMENT=dev
# Foce the use of IPs (instead of DNS names if bosh has enabled dns)
export BOSH_ANSIBLE_INVENTORY_IP="1"
# Define the ssh user and other ansible parameters
export BOSH_ANSIBLE_INVENTORY_PARAMS="ansible_user=nsaadmin  host_key_checking=false"
```

Check if it is working:

```
ansible runner_z1  -i /usr/local/bin/bosh-inventory   -m ping
```

If so, just run the playbook.

```
ansible-playbook -i /usr/local/bin/bosh-inventory  cf-warden.yml
```


# Author

Springer Nature Platform Engineering, Jose Riguera Lopez (jose.riguera@springer.com)
