#!/usr/bin/env python3

import argparse
import netifaces
import os
import requests
import socket

parser = argparse.ArgumentParser(
    prog='teradyndns-client',
    description='Client to easily call TeraDynDNS service',
    epilog='Take control of your ever-changing ip addresses',
)

parser.add_argument('--service', help='TeraDnyDNS endpoint url', required=True)
parser.add_argument('--user', help='username for authenticating to TeraDynDNS', default=os.getlogin())
parser.add_argument('--password', help='password for authenticating to TeraDynDNS', required=True)
parser.add_argument('--location', help='location of this machine', default='home')
parser.add_argument('--machine', help='name of this machine', default=socket.gethostname())
parser.add_argument('--operation', help='operation to perform (autoregister, delete)', default='autoregister')
args = parser.parse_args()

params = dict()
count = 0

for iface in netifaces.interfaces():
    if iface == 'lo' or iface.startswith('vbox') or iface.startswith('docker') or iface.startswith('gpd') or iface.startswith('tun'):
        continue
    iface_details = netifaces.ifaddresses(iface)
    if netifaces.AF_INET in iface_details:
        count += 1
        params[f"name{count}"] = iface
        # TODO: is there ever more than just one entry here? I've only ever seen one...
        params[f"ip{count}"] = iface_details[netifaces.AF_INET][0]['addr']
    # TODO: IPv6
    # if netifaces.AF_INET6 in iface_details:
    #     count +=1
    #     mappings[iface] = iface_details[netifaces.AF_INET6]['addr']
    #     params[f"name{count}"] = iface
    #     params[f"ip{count}"] = iface_details[netifaces.AF_INET6]['addr']


session = requests.Session()
session.auth = (args.user, args.password)

resp = session.post(f"{args.service}/api/v1/{args.operation}/{args.location}/{args.machine}", params=params)
print(f"Response: {resp.content.decode()}")
