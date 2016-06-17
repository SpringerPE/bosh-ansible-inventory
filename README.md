# bosh-ansible-inventory
Ansible dynamic inventory

# Usage

```
./bosh-inventory.py  --help
usage: bosh-inventory.py [-h] [--list]

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

v0.1.0, 2016 Jose Riguera <jose.riguera@springer-sbm.com>
```


In order to get an INI format inventory:
```
export BOSH_CONFIG=~/.bosh-dev
./bosh-inventory.py > inventory
```

Or using directly with ansible:
```
export BOSH_CONFIG=~/.bosh-dev
export BOSH_ANSIBLE_INVENTORY_PARAMS="ansible_user=vcap"                                                                                                  
ansible -vvvv firehose-to-syslog-0  -i ./bosh-inventory.py  -m ping
```

# Author
Jose Riguera Lopez
