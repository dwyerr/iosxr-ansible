#!/usr/bin/python
#------------------------------------------------------------------------------
#
#    Copyright (C) 2016 Cisco Systems, Inc.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#------------------------------------------------------------------------------

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.iosxr import iosxr_argument_spec, run_commands

DOCUMENTATION = """
---
module: xr32_install_package
author: Adisorn Ermongkonchai
short_description: Run install commands on IOS-XR devices.
description:
  - Install IOS-XR package or SMU (Software Maintenance Updates)
    on the IOS-XR node.
options:
  host:
    description:
      - IP address or hostname (resolvable by Ansible control host) of
        the target IOS-XR node.
    required: true
  username:
    description:
      - username used to login to IOS-XR
    required: true
    default: none
  password:
    description:
      - password used to login to IOS-XR
    required: true
    default: none
  pkgpath:
    description:
      - path to where the package file is stored
        e.g. tftp://192.168.1.1
             ftp://192.168.1.1
             /disk0:
    required: Only when state is 'present'
  pkgname:
    description:
      - IOS-XR software package without file extension
        e.g. The package name for 'xrv9k-ospf-1.0.0.0-r61102I.x86_64.rpm'
             is 'xrv9k-ospf-1.0.0.0-r61102I'
    required: true
  state:
    description:
      - represent state of the package being installed
    required: false
    default: 'present'
    choices: ['present', 'absent', 'activated', 'deactivated', 'committed']
"""

EXAMPLES = """
- xr32_install_package:
    provider:
      host: "{{ ansible_host }}"
      username: "{{ ansible_user }}"
      password: "{{ ansible_ssh_pass }}"
    pkgpath: "tftp://192.168.1.1"
    pkgname: "xrv9k-ospf-1.0.0.0-r61102I"
    state: present

- xr32_install_package:
    provider:
      host: "{{ ansible_host }}"
      username: "{{ ansible_user }}"
      password: "{{ ansible_ssh_pass }}"
    pkgname: "xrv9k-ospf-1.0.0.0-r61102I"
    state: activated
"""

RETURN = """
stdout:
  description: raw response
  returned: always
stdout_lines:
  description: list of response lines
  returned: always
"""

# check if another install command in progress
def is_legacy_iosxr(module):
    command = "show version"
    response = run_commands(module, command)
    return "Build Information:" not in response[0]

# check if another install command in progress
def is_install_in_progress(module):
    command = "show install request"
    response = run_commands(module, command)
    return "no install requests" not in response[0]

# check if the package is already added
def is_package_already_added(module, pkg_name):
    command = "show install inactive"
    response = run_commands(module, command)
    return pkg_name in response[0]

# check if the package is already active
def is_package_already_active(module, pkg_name):
    command = "show install active"
    response = run_commands(module, command)
    return pkg_name in response[0]

# wait for install command to complete
def wait_install_response(module, oper_id):
    retries = 100
    while retries > 0:
        if is_install_in_progress(module):
            retries -= 1
            time.sleep(3)
        else:
            command = "show install log " + oper_id.group(1) + " detail"
            response = run_commands(module, command)
            if 'Error: ' in response[0]:
                module.fail_json(msg=response)
            return response

    else:
        module.fail_json(msg="timeout waiting for install to complete")

# get install operation id from log
def get_operation_id(response):
    pattern = re.compile(r"Install operation (\d+)")
    return pattern.search(response[0])

# add package only when it is not already added or activated
def install_add(module, pkg_path, pkg_name):
    result = dict(changed=False)

    if is_package_already_active(module, pkg_name):
        response = [pkg_name + " package is already active\n"]
    elif is_package_already_added(module, pkg_name):
        response = [pkg_name + " package is already added\n"]
    elif pkg_path == None:
        module.fail_json(msg="package path required")
    else:
        command = ("install add source " +
                   pkg_path + " " + pkg_name)
        response = run_commands(module, command)
        oper_id = get_operation_id(response)
        response = wait_install_response(module, oper_id)
        result['changed'] = True

    result['stdout'] = response
    result['stdout_lines'] = str(result['stdout']).split(r'\n')
    return result

# remove package only when it is in inactive state
def install_remove(module, pkg_path, pkg_name):
    result = dict(changed=False)

    if is_package_already_active(module, pkg_name):
        error = pkg_name + " is active, please deactivate first"
        module.fail_json(msg=error)
    elif is_package_already_added(module, pkg_name):
        command = "install remove " + pkg_name + "prompt-level none"
        response = run_commands(module, command)
        oper_id = get_operation_id(response)
        response = wait_install_response(module, oper_id)
        result['changed'] = True
    else:
        response = [pkg_name + " package has already been removed\n"]

    result['stdout'] = response
    result['stdout_lines'] = str(result['stdout']).split(r'\n')
    return result

# activate package only when it has been added
def install_activate(module, pkg_path, pkg_name):
    result = dict(changed=False)

    if is_package_already_active(module, pkg_name):
        response = [pkg_name + " package is already active\n"]
    elif is_package_already_added(module, pkg_name):
        command = "install activate " + pkg_name
        response = run_commands(module, command)
        oper_id = get_operation_id(response)
        response = wait_install_response(module, oper_id)
        result['changed'] = True
    else:
        error = pkg_name + " must be present before activate"
        module.fail_json(msg=error)

    result['stdout'] = response
    result['stdout_lines'] = str(result['stdout']).split(r'\n')
    return result

# deactivate package only when it is in active state
def install_deactivate(module, pkg_path, pkg_name):
    result = dict(changed=False)

    if is_package_already_active(module, pkg_name):
        command = "install deactivate " + pkg_name
        response = run_commands(module, command)
        oper_id = get_operation_id(response)
        response = wait_install_response(module, oper_id)
        result['changed'] = True
    elif is_package_already_added(module, pkg_name):
        response = [pkg_name + " package is already deactivated\n"]
    else:
        response = [pkg_name + " package has already been removed\n"]

    result['stdout'] = response
    result['stdout_lines'] = str(result['stdout']).split(r'\n')
    return result
  
# commit active packages
def install_commit(module, pkg_path, pkg_name):
    command = "install commit"
    response = run_commands(module, command)
    oper_id = get_operation_id(response)
    response = wait_install_response(module, oper_id)

    result = dict(changed=True)
    result['stdout'] = response
    result['stdout_lines'] = str(result['stdout']).split(r'\n')
    return result

def main():
    spec = dict(provider = dict(required=True),
                pkgpath = dict(required=False, default=None),
                pkgname = dict(required=True, default=None),
                state = dict(required=False, default='present',
                             choices = ['present',
                                        'absent',
                                        'activated',
                                        'deactivated',
                                        'committed'])
    spec.update(iosxr_argument_spec)
    module = AnsibleModule(argument_spec=spec)

    args = module.params
    state = args['state']
    legacy = is_legacy_iosxr(module)

    # cannot run on 64-bit XR or run 'updated'
    if not legacy:
        module.fail_json(msg="cannot run on 64-bit IOS-XR")
  
    # make sure no other install in progress
    if is_install_in_progress(module):
        module.fail_json(msg="other install op in progress")
  
    install = {
        'present':     install_add,
        'absent':      install_remove,
        'activated':   install_activate,
        'deactivated': install_deactivate,
        'committed':   install_commit
    }
    # need to be in "admin" mode for classic XR
    command = "admin"
    response = run_commands(module, command)

    result = install[state](module, args['pkgpath'], args['pkgname'])
  
    module.exit_json(**result)

if __name__ == "__main__":
    main()
