#!/usr/bin/python
# coding: utf-8
# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}

DOCUMENTATION = """
---
module: onevm
short_description: Manage OpenNebula virtuals machines.
description:
  - Manage OpenNebula virtuals machines.
author:
  - François Ménabé (@fmenabe)
requirements:
  - python-lxml
options:
  state:
    description:
      - Final state of the virtual machine.
    note:
      - 'present' state will put the virtual machine in the 'hold' state.
      - 'started' state will create the virtual machine if not exists and make sure the
        virtual machine is started.
      - 'stopped', 'suspended', 'resumed' and 'undeployed' states will failed if the
        virtual machine does not exists.
      - 'retrieve' state is a hack state for retrieving information on a virtual machine
        (but it does no action) and changed paramter is always False.
      - none of the actions are forced so you need to check for the state of the virtual
        machine.
    choices: [present, absent, started, stopped, suspended, resumed, undeployed, retrieve]
    default: started
  endpoint:
    required: true
    description:
      - URL of OpenNebula XML-RPC API.
  user:
    required: true
    description:
      - Username for connecting to OpenNebula XML-RPC API.
  password:
    required: true
    description:
      - Password for connecting to OpenNebula XML-RPC API.
  name:
    required: true
  template_id:
    description:
    note:
      - This parameter is required with 'present' and 'started' states.
  cpu:
    description:
      - Number of CPU.
  vcpu:
    description:
      - Number of vCPU.
  memory:
    description:
      - Memory in Mb.
  nics:
    description:
      - List of networks ids.
  graphics:
    description:
      - Allow to active either VNC or Spice for accessing virtual machine console.
  disks:
    description:
      - Additionnal disks. The format is: .
"""

import os
import traceback

try:
    from xmlrpc.client import ServerProxy
except ImportError:
    from xmlrpclib import ServerProxy

try:
    import lxml.etree as etree
    HAS_LXML = True
except ImportError:
    HAS_LXML = False


from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_native

STATES = [
    'present',
    'absent',
    'started',
    'stopped',
    'suspended',
    'resumed',
    'undeployed',
    'retrieve']
ONE_STATES_MAP = {
    '0': 'init',
    '1': 'pending',
    '2': 'hold',
    '3': 'active',
    '4': 'stopped',
    '5': 'suspended',
    '6': 'done',
    '8': 'poweroff',
    '9': 'undeployed',
    '10': 'cloning',
    '11': 'cloning_failure'
}

#FIND_VM = "/VM_POOL/VM[NAME='{name:s}']/NAME | /VM_POOL/VM[NAME='{name:s}']/ID"
NOT_EXISTS_ERR = 'virtual machine does not exists!'

class OneError(Exception):
    pass

def xmlrpc(client, method, *args):
    status, stdout, errcode = getattr(client.one, method)(*args)
    if not status:
        raise OneError('{:d}: {:s}'.format(errcode, stdout))
    #print(stdout)
    open('/tmp/output.xml', 'w').write(stdout)
    return stdout

def get_vm_info(client, session, name):
    xml = etree.fromstring(xmlrpc(client, 'vmpool.info', session, -2, -1, -1, -1))
    vms = xml.xpath("/VM_POOL/VM[NAME='{:s}']".format(name))
    if len(vms) > 2:
        raise OneError("Multiples VMs have the same name!")

    vm_id, vm_state = (
        (vms[0].find('ID').text, ONE_STATES_MAP[vms[0].find('STATE').text])
        if vms
        else (-1, None))
    return {'name': name, 'id': int(vm_id), 'state': vm_state}

def gen_template(params):
    template_params = []
    template_params.append('CPU = "{:d}"'.format(params.get('cpu', 2)))
    template_params.append('VCPU = "{:d}"'.format(params.get('vcpu', 2)))
    template_params.append('MEMORY = "{:d}"'.format(params.get('memory', 2048)))
    template_params.extend('NIC = [ NETWORK_ID = "{:d}" ]'.format(nic_id)
                           for nic_id in params.get('nics', []))
    if 'graphics' in params:
        graphics_params = ['GRAPHICS = [']
        graphics_params.extend('  {:s} = "{:s}",'.format(param.upper(), value)
                              for param, value in params['graphics'].items())
        # Remove the comma on last element (as the template is invalid with it).
        graphics_params[-1] = graphics_params[-1][:-1]
        graphics_params.append(']')
        template_params.extend(graphics_params)
    return '\n'.join(template_params)

def retrieve_vm(client, session, vm, _):
    if vm['state'] is None:
        return { 'failed': True, 'msg': NOT_EXISTS_ERR }
    xml = etree.fromstring(xmlrpc(client, 'vm.info', session, vm['id']))
    conf = {}
    for elt in ('uid', 'gid', 'uname', 'gname', 'state'):
        conf[elt] = xml.find(elt.upper()).text
    conf['state'] = ONE_STATES_MAP[conf['state']]

    for elt in ('cpu', 'vcpu', 'memory'):
        conf[elt] = xml.xpath('/VM/TEMPLATE/{:s}'.format(elt.upper()))[0].text

    ips = xml.xpath('/VM/TEMPLATE/NIC/IP')
    conf['ips'] = [ip.text for ip in ips]
    return { 'changed': False, 'vm_id': vm['id'], 'conf': conf }

def create_vm(client, session, vm, params):
    """If virtual machine does not exists, it is created in 'hold' state while
    nothing is done if the virtual machine already exists."""
    if vm['state'] is not None:
        return { 'changed': False, 'vm_id': vm['id'], 'actions': [] }

    template_id = params.pop('template_id', None)
    stdout = xmlrpc(
        client,
        'template.instantiate',
        session,
        template_id,
        vm['name'],
        True,
        gen_template(params),
        False
    )
    return { 'changed': True, 'vm_id': int(stdout), 'actions': ['created']}

def delete_vm(client, session, vm, params):
    """Delete (ie: terminate) a virtual machine."""
    if vm['state'] is None:
        return { 'changed': False }
    xmlrpc(client, 'vm.action', session, 'terminate', vm['id'])
    return { 'changed': True, 'vm_id': -1, 'actions': ['terminated'] }

def start_vm(client, session, vm, params):
    """Start a virtual machine. The virtual machine is created if it does not exists."""
    if vm['state'] == 'active':
        return { 'changed': False, 'vm_id': vm['id'], 'actions': [] }

    actions = []
    if vm['state'] is None:
        vm['id'] = create_vm(client, session, vm, params)['vm_id']
        vm['state'] = 'hold'
        actions.append('created')

    if vm['state'] == 'hold':
        xmlrpc(client, 'vm.action', session, 'release', vm['id'])
        actions.append('released')
    else:
        xmlrpc(client, 'vm.action', session, 'resume', vm['id'])
        actions.append('started')
    return { 'changed': True, 'vm_id': vm['id'], 'actions': actions }

def stop_vm(client, session, vm, params):
    """Stop an existing virtual machine. It will fail if the virtual machine does
    not exist."""
    if vm['state'] is None:
        return { 'failed': True, 'msg': NOT_EXISTS_ERR }
    if vm['state'] in ('hold', 'stopped'):
        return { 'changed': False, 'vm_id': vm['id'], 'actions': [] }

    xmlrpc(client, 'vm.action', session, 'poweroff', vm['id'])
    return { 'changed': True, 'vm_id': vm['id'], 'actions': ['stopped'] }

def suspend_vm(client, session, vm, params):
    """Suspend an existing virtual machine. It will fail if the virtual machine does
    not exists."""
    if vm['state'] is None:
        return { 'failed': True, 'msg': NOT_EXISTS_ERR }
    if vm['state'] == 'suspended':
        return { 'changed': False, 'vm_id': vm['id'], 'actions': [] }
    if vm['state'] != 'active':
        return { 'failed': True, 'msg': 'only an active virtual machine can be suspended!' }

    xmlrpc(client, 'vm.action', session, 'suspend', vm['id'])
    return { 'changed': True, 'vm_id': vm['id'], 'actions': ['suspended'] }

def resume_vm(client, session, vm, params):
    """Resume an existing virtual machine. It will fail if the virtual machine does
    not exists."""
    if vm['state'] is None:
        return { 'failed': True, 'msg': NOT_EXISTS_ERR }
    if vm['state'] == 'active':
        return { 'changed': False, 'vm_id': vm['id'], 'actions': [] }
    if vm['state'] != 'suspended':
        return { 'failed': True, 'msg': 'only a suspended virtual machine can be resumed!' }

    xmlrpc(client, 'vm.action', session, 'resume', vm['id'])
    return { 'changed': True, 'vm_id': vm['id'], 'actions': ['resumed'] }

def undeploy_vm(client, session, vm, params):
    """Undeploy an existing virtual machine."""
    if vm['state'] is None:
        return { 'failed': True, 'msg': NOT_EXISTS_ERR }
    if vm['state'] == 'undeploy':
        return { 'changed': False, 'vm_id': vm['id'], 'actions': [] }

    xmlrpc(client, 'vm.action', session, 'undeploy', vm['id'])
    return { 'changed': True, 'vm_id': vm['id'], 'actions': ['undeployed'] }

def core(module):
    # Required parameters.
    endpoint = module.params.pop('endpoint')
    session = '{:s}:{:s}'.format(module.params.pop('user'), module.params.pop('password'))
    state = module.params.pop('state')
    name = module.params.pop('name')

    if state in ('present', 'started') and module.params['template_id'] is None:
        return { 'failed': True, 'msg': 'missing required argument: template_id' }

    try:
        client = ServerProxy(endpoint)
        vm = get_vm_info(client, session, name)

        return {
            'present': create_vm,
            'absent': delete_vm,
            'started': start_vm,
            'stopped': stop_vm,
            'suspended': suspend_vm,
            'resumed': resume_vm,
            'undeployed': undeploy_vm,
            'retrieve': retrieve_vm
        }.get(state)(client, session, vm, module.params)
    except OneError as err:
        return { 'failed': True, 'msg': to_native(err) }
    return { 'changed': False }

def main():
    module = AnsibleModule(
        argument_spec={
            'state': dict(type='str', choices=STATES, default='started'),
            'endpoint': dict(type='str', required=True),
            'user': dict(type='str', required=True),
            'password': dict(type='str', required=True, no_log=True),
            'name': dict(type='str', required=True),
            'template_id': dict(type='int', required=False),
            'cpu': dict(type='int', required=False, default=2),
            'vcpu': dict(type='int', required=False, default=2),
            'memory': dict(type='int', required=False, default=2048),
            'graphics': dict(type='dict', required=False, default={'type': 'vnc'}),
            'nics': dict(type='list', required=False),
            'disks': dict(type='list', required=False)
        },
        supports_check_mode=True,
    )

    if not HAS_LXML:
        module.fail_json(msg="Missing required 'lxml' module (pip install lxml)")

    try:
        result = core(module)
    except Exception as err:
        module.fail_json(msg=to_native(err), exception=traceback.format_exc())

    if 'failed' in result:  # something went wrong
        module.fail_json(**result)
    else:
        module.exit_json(**result)

if __name__ == '__main__':
    main()
