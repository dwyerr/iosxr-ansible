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

from ansible.module_utils.basic import *
from ydk.providers import NetconfServiceProvider
from ydk.services import CRUDService
from ydk.models.cisco_ios_xr.Cisco_IOS_XR_spirit_install_instmgr_oper import SoftwareInstall
import sys
import logging

def init_logging (logfile):
    # Initialize the logging infra and add a handler
    logger = logging.getLogger ("ydk") 
    logger.setLevel (logging.DEBUG)
  
    # create file handler             
    fh = logging.FileHandler (logfile)
    fh.setLevel (logging.DEBUG)
  
    # create a console logger too
    ch = logging.StreamHandler ()
    ch.setLevel (logging.ERROR)
  
    # add the handlers to the logger
    logger.addHandler (fh)
    logger.addHandler (ch)

def main ():
    module = AnsibleModule (argument_spec = 
                                dict (provider = dict (required = True)))

    args = module.params

    init_logging ("/tmp/iosxr_show_install_version.log")

    # establish ssh connection
    provider = NetconfServiceProvider (address = args["host"],
                                       port=830,
                                       username = args["username"],
                                       password = args["password"],
                                       protocol="ssh")
    # establish CRUD service
    crud = CRUDService ()

    # retrieve software install version
    install = SoftwareInstall ()
    info = crud.read (provider, install)

    result = dict (changed = False)
    result["stdout"] = info.version.log
    return module.exit_json (**result)

if __name__ == "__main__":
    main ()
