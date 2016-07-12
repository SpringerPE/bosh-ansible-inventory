# bosh-ansible-inventory
Ansible dynamic inventory

# Usage

You can install it by running `setup.py`:
```
$ python setup.py install
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

The program will include the IP of each vm if DNS is not defined. To force 
always the inclusion of the IP in the inventory, just define the variable
BOSH_ANSIBLE_INVENTORY_IP as a positive integer indicating the index (starting
from 1) of the IP which will be taken (for VMs with multiple IPs), 0 will
disable the feature.

You can also limit the inventory to one deployment by setting the value
of the environment variable BOSH_ANSIBLE_DEPLOYMENT to the name of it.

0.2.1, 2016 Jose Riguera <jose.riguera@springer-sbm.com>
```

To use it, just point the env variable `BOSH_CONFIG` to your
bosh configuration. It will read all parameters from there.


By default, it will return an INI format inventory:
```
$ export BOSH_CONFIG=~/.bosh-dev
$ bosh-inventory > ansible-inventory
```

Or using directly with ansible:
```
$ export BOSH_CONFIG=~/.bosh-dev
$ export BOSH_ANSIBLE_INVENTORY_PARAMS="ansible_user=vcap"
$ export BOSH_ANSIBLE_INVENTORY_IP="1"
$ ansible -vvvv firehose-to-syslog-0  -i bosh-inventory.py  -m ping
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


# Author
Jose Riguera Lopez (jose.riguera@springer.com)
