import flask
import json
import requests

import pprint


app = flask.Flask(__name__)
with open("properties.json", "r") as f:
    app.tera_configs = json.load(f)

app.dnssession = requests.Session()
app.dnssession.headers.update({
    "Authorization": f"Bearer {app.tera_configs['dnsimple_oauth_token']}",
    "Content-Type": "application/json",
})


def dnsimple_get_id():
    resp = app.dnssession.get('https://api.dnsimple.com/v2/whoami')
    return resp.json()['data']['account']['id']


app.tera_configs['dnsimple_id'] = dnsimple_get_id()


def dnsimple_api_uri(path):
    return f"https://api.dnsimple.com/v2/{app.tera_configs['dnsimple_id']}/{path}"

def dnsimple_post_machine(location, machine_name, ip):
    # first get list of records
    zone_records = app.dnssession.get(dnsimple_api_uri(f"zones/{app.tera_configs['zone_root']}/records"))
    pprint.pprint(zone_records.json())


@app.route('/')
def index():
    return flask.render_template('index.html')


@app.route('/api/v1/update_machine/<location>/<machine_name>', methods=('GET', 'POST'))
def update_machine(location, machine_name):
    dnsimple_post_machine(location, machine_name, flask.request.remote_addr)
    return f"Updating machine '{machine_name}' at location '{location}' with public ip '{flask.request.remote_addr}'"


if __name__ == "__main__":
    app.run(host='0.0.0.0')
