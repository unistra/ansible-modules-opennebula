*************************
OpenNebula Ansible module
*************************

This repository contains a basic module for managing OpenNebula virtuals machines.

Examples
========

* Ensure a VM exists but is not started (in *hold* state):

.. code::

    onevm:
      endpoint: "https://one.exemple.com:2633/RPC2"
      user: <USER>
      password: <PASSWORD>
      name: <NAME>
      template_id: 1
      cpu: 2
      vcpu: 2
      memory: 8g
      nics: [1, 2]
      graphics: {
        type: vnc,
        keymap: fr
      },
      state: present

* Ensure a VM exists and is started with one additionnal disk of 100G:

.. code::

    onevm:
      endpoint: "https://one.exemple.com:2633/RPC2"
      user: <USER>
      password: <PASSWORD>
      name: <NAME>
      template_id: 1
      cpu: 2
      vcpu: 2
      memory: 8192
      nics: [1, 2]
      graphics: {
        type: vnc,
        keymap: fr
      },
      state: present
      disks:
      - { size: 100g, datastore_id: <DATASTORE_ID> }

* Remove (terminate) a VM:

.. code::

    onevm:
      endpoint: "https://one.exemple.com:2633/RPC2"
      user: <USER>
      password: <PASSWORD>
      name: <NAME>
      state: absent

* Stop a VM:

.. code::

    onevm:
      endpoint: "https://one.exemple.com:2633/RPC2"
      user: <USER>
      password: <PASSWORD>
      name: <NAME>
      state: stopped

* Suspend a VM:

.. code::

    onevm:
      endpoint: "https://one.exemple.com:2633/RPC2"
      user: <USER>
      password: <PASSWORD>
      name: <NAME>
      state: suspended

* Resume a VM:

.. code::

    onevm:
      endpoint: "https://one.exemple.com:2633/RPC2"
      user: <USER>
      password: <PASSWORD>
      name: <NAME>
      state: resumed

* Undeploy a VM:

.. code::

    onevm:
      endpoint: "https://one.exemple.com:2633/RPC2"
      user: <USER>
      password: <PASSWORD>
      name: <NAME>
      state: undeployed
