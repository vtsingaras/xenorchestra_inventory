#!/usr/bin/env python3

from xolib import xo
from time import time
from typing import List, Dict, Optional, Union
from ipaddress import ip_network, ip_address, IPv4Network, IPv6Network, AddressValueError
import pcre
import json
import argparse
import configparser
import os
import sys


def static_vars(**kwargs):
    def decorate(func):
        for k in kwargs:
            setattr(func, k, kwargs[k])
        return func
    return decorate


@static_vars(last_refresh=0, obj_cache={})
def getXoObjectsByType(xoa_instance: xo, obj_type: str, refresh: bool = False, cache_seconds: int = 10) -> Dict:
    if refresh is True or (time() - getXoObjectsByType.last_refresh > cache_seconds) or len(getXoObjectsByType.obj_cache) == 0:
        getXoObjectsByType.obj_cache = xoa_instance.xo_getAllObjects()
        getXoObjectsByType.last_refresh = time()

    return {uuid: obj for uuid, obj in getXoObjectsByType.obj_cache.items() if obj['type'] == obj_type}


def inventory_addHostVars(host_name: str, host_vars: Dict):
    global host_inventory
    host_inventory[host_name] = host_vars


def inventory_addHost(group_name: str, host_name: str, host_address: str = None, host_vars: dict = None) -> None:
    global ansible_inventory
    if group_name not in ansible_inventory:
        ansible_inventory[group_name] = dict()
        ansible_inventory[group_name]['hosts'] = list()
    ansible_inventory[group_name]['hosts'].append(host_name)
    #merge host_address with host_vars
    h_vars_dict = host_vars.copy() if host_vars is not None else dict()
    if host_address is not None and 'ansible_host' not in h_vars_dict:
        h_vars_dict['ansible_host'] = host_address
    inventory_addHostVars(host_name, h_vars_dict)


def getHostVarsFromXoaTags(tags: List[str]) -> Dict:
    if len(tags) == 0:
        return dict()
    ansible_tags = [tag for tag in tags if tag.startswith('ansible_')]
    host_vars = dict()
    for ansible_tag in ansible_tags:
        ansible_key, ansible_value = ansible_tag.split('=')
        host_vars[ansible_key] = ansible_value
    return host_vars


def getManagementAddress(addresses: List[str], mgmt_networks: List[Union[IPv4Network, IPv6Network]]) -> Optional[str]:
    for address in addresses:
        try:
            vm_ip_addr = ip_address(address)
            for mgmt_network in mgmt_networks:
                if vm_ip_addr in mgmt_network:
                    return str(vm_ip_addr)
        except AddressValueError:
            pass
    return None


def hostIsExcluded(vm_data: Dict, excluded_tags: List[str], excluded_regexes: List[pcre.Pattern]) -> bool:
    excluded = False
    # Check if the vm_data matches the exclusion specs
    if len(set(excluded_tags) & set(vm_data['tags'])) != 0:
        excluded = True
    for regex in excluded_regexes:
        if regex.match(vm_data['name_label']) is not None:
            excluded = True
    return excluded


ansible_inventory = dict()
host_inventory = dict()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='XenOrchestra Ansible Dynamic Inventory source.')
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--list', action='store_true', help='List all hosts.')
    action.add_argument('--host', help='Get hostvars for host.')

    args = parser.parse_args()

    config = configparser.ConfigParser()
    config.read(os.path.dirname(os.path.realpath(__file__)) + '/xenorchestra.ini')

    xoa_host = config.get('xenorchestra', 'host')
    login_args = dict()
    if config.has_option('xenorchestra', 'token'):
        login_args['token'] = config.get('xenorchestra', 'token')
    else:
        login_args['email'] = config.get('xenorchestra', 'email')
        login_args['password'] = config.get('xenorchestra', 'password')

    allowed_networks_str = ['0.0.0.0/0', ]
    if config.has_option('xenorchestra', 'management_networks'):
        allowed_networks_str = json.loads(config.get('xenorchestra', 'management_nnetworks'))
    allowed_networks = [ip_network(ip_net) for ip_net in allowed_networks_str]

    host_deny_regex = list()
    if config.has_option('xenorchestra', 'deny_regex'):
        host_deny_regex = json.loads(config.get('xenorchestra', 'deny_regex'))
    host_deny_regex_patterns = list(map(pcre.compile, host_deny_regex))

    host_deny_tags = list()
    if config.has_option('xenorchestra', 'deny_tags'):
        host_deny_tags = json.loads(config.get('xenorchestra', 'deny_tags'))

    xoa = xo('ws://' + xoa_host, **login_args)
    allVM_dict = getXoObjectsByType(xoa, 'VM')

    for vm_uuid, vm_data in allVM_dict.items():
        # Get VM management address
        vm_address = None
        if 'addresses' in vm_data and vm_data['addresses'] is not None:
            vm_addresses = [address for idx, address in vm_data['addresses'].items()]
            vm_address = getManagementAddress(vm_addresses, allowed_networks)
        # Check if we should exclude this host
        if hostIsExcluded(vm_data, host_deny_tags, host_deny_regex_patterns):
            continue
        vm_hostvars = getHostVarsFromXoaTags(vm_data['tags'])
        vm_group = vm_hostvars.get('ansible_group', 'unknown')
        inventory_addHost(vm_group, vm_data['name_label'], vm_address, vm_hostvars)
    pass

    ansible_result = None
    if args.list:
        ansible_result = ansible_inventory.copy()
        ansible_result['_meta'] = dict()
        ansible_result['_meta']['hostvars'] = host_inventory
    if args.host:
        ansible_result = host_inventory[args.host]

    if sys.stdout.isatty():
        print(json.dumps(ansible_result, sort_keys=True, indent=2))
        pass
    else:
        print(json.dumps(ansible_result))
