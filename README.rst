*************************
OpenNebula Ansible module
*************************

This repository contains a basic module for managing OpenNebula virtuals machines.

Examples
========

* Make sure a VM exists (in *hold* state):

.. code::

    onevm:
      endpoint: "https://one.unistra.fr:2633/RPC2"
      user: YOUR_USER
      password: YOUR_PASSWORD
      name: es2-mon1
      template_id: 45 # template centos7-infra
      cpu: 2
      vcpu: 2
      memory: 8192
      nics: [11, 8] # BDD and SAN networks
      graphics: {
        type: vnc,
        keymap: fr
      },
      state: present

* Make sure a VM exists and is started with
  1 additionnal disk, size are in MB and will appear as /dev/vdb device:

.. code::

    onevm:
      endpoint: "https://one.unistra.fr:2633/RPC2"
      user: YOUR_USER
      password: YOUR_PASSWORD
      name: es2-mon1
      template_id: 45 # template centos7-infra
      cpu: 2
      vcpu: 2
      memory: 8192
      nics: [11, 8] # BDD and SAN networks
      graphics: {
        type: vnc,
        keymap: fr
      },
      state: present
      disks: [100000]

* Remove (terminate) a VM:

.. code::

    onevm:
      endpoint: "https://one.unistra.fr:2633/RPC2"
      user: YOUR_USER
      password: YOUR_PASSWORD
      name: es2-mon1
      state: absent

* Stop a VM:

.. code::

    onevm:
      endpoint: "https://one.unistra.fr:2633/RPC2"
      user: YOUR_USER
      password: YOUR_PASSWORD
      name: es2-mon1
      state: stopped

* Suspend a VM:

.. code::

    onevm:
      endpoint: "https://one.unistra.fr:2633/RPC2"
      user: YOUR_USER
      password: YOUR_PASSWORD
      name: es2-mon1
      state: suspended

* Resume a VM:

.. code::

    onevm:
      endpoint: "https://one.unistra.fr:2633/RPC2"
      user: YOUR_USER
      password: YOUR_PASSWORD
      name: es2-mon1
      state: resumed

* Undeploy a VM:

.. code::

    onevm:
      endpoint: "https://one.unistra.fr:2633/RPC2"
      user: YOUR_USER
      password: YOUR_PASSWORD
      name: es2-mon1
      state: undeployed
