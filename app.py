import flask
import flask_httpauth
import json
import multidict
import requests
import werkzeug.security


app = flask.Flask(__name__)


auth = flask_httpauth.HTTPBasicAuth()

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


# auth stuff - https://flask-httpauth.readthedocs.io/en/latest/
@auth.verify_password
def verify_password(username, password):
    if username in app.tera_configs['usermap']:
        if werkzeug.security.check_password_hash(app.tera_configs['usermap'][username], password):
            return username


def dnsimple_api_uri(path):
    return f"https://api.dnsimple.com/v2/{app.tera_configs['dnsimple_id']}/{path}"


# TODO: cache these results or something?
def dnsimple_get_records():
    records = multidict.MultiDict()
    page = 1
    # response is paginated, so we have to loop until we have it all
    while True:
        # first get list of records
        zone_response = app.dnssession.get(dnsimple_api_uri(f"zones/{app.tera_configs['zone_root']}/records"), params={'page': page, 'per_page': 100})
        # we need to get all records, response is paginated
        # Looks like this:
        # zone_response = {
        #     'data': [ { <hash with name, type, zone_id, id, etc }, ... ],
        #     'pagination': {'current_page': 1, 'per_page': 30, 'total_entries': 20, 'total_pages': 1}
        # }
        for record in zone_response.json()['data']:
            records.add(record['name'], record)
        if zone_response.json()['pagination']['current_page'] == zone_response.json()['pagination']['total_pages']:
            # no need to request again
            break
        # otherwise, loop again fetching next page
        page += 1
    app.logger.info(f"Found {len(records)} records across {page} pages")
    return records


def pair_to_name_prefix(location, machine_name):
    return f"{machine_name}.{location}.{app.tera_configs['dns_prefix']}"


def dnsimple_post_machine(location, machine_name, ip):
    records = dnsimple_get_records()
    name_prefix = pair_to_name_prefix(location, machine_name)
    domain = app.tera_configs['zone_root']
    found = False
    if name_prefix in records:
        # might exist, might have to update
        recordset = records.getall(name_prefix)
        for record in recordset:
            if record['type'] != 'A':
                continue
            if record['content'] == ip:
                app.logger.info(f"Found entry {record['name']}.{domain} for ip {record['content']} is up to date")
                found = True
                continue
            app.logger.info(f"Found out of date entry {record['name']}.{domain} for ip {record['content']}, updating to ip {ip}")
            new_record = {"name": name_prefix, "type": "A", "content": ip, "ttl": 60, "priority": 15}
            resp = app.dnssession.patch(dnsimple_api_uri(f"zones/{app.tera_configs['zone_root']}/records/{record['id']}"), params=new_record)
            resp.raise_for_status()
            found = True

    if found:
        # found or updated at least one entry
        return

    # no records found, def. have to create
    app.logger.info(f"Creating new record {name_prefix}.{domain} for ip {ip}")
    new_record = {"name": name_prefix, "type": "A", "content": ip, "ttl": 60, "priority": 15}
    resp = app.dnssession.post(dnsimple_api_uri(f"zones/{app.tera_configs['zone_root']}/records"), params=new_record)
    resp.raise_for_status()


def dnsimple_delete_machine(location, machine_name, prefixes=False):
    records = dnsimple_get_records()
    name_prefix = pair_to_name_prefix(location, machine_name)
    domain = app.tera_configs['zone_root']
    if prefixes:
        app.logger.info(f"Deleting all records under {name_prefix}.{domain}")
        for name in records.keys():
            if name.endswith(name_prefix):
                recordset = records.getall(name)
                for record in recordset:
                    if record['type'] != 'A':
                        continue
                    app.logger.info(f"Deleting record {record['name']} for ip {record['content']} (id={record['id']})")
                    resp = app.dnssession.delete(dnsimple_api_uri(f"zones/{app.tera_configs['zone_root']}/records/{record['id']}"))
                    resp.raise_for_status()
        return

    # not deleting all prefixes, only perfect matches
    if name_prefix not in records:
        # nothing to delete
        return
    recordset = records.getall(name_prefix)
    for record in recordset:
        if record['type'] != 'A':
            continue
        app.logger.info(f"Deleting record {name_prefix}.{domain} for ip {record['content']} (id={record['id']})")
        resp = app.dnssession.delete(dnsimple_api_uri(f"zones/{app.tera_configs['zone_root']}/records/{record['id']}"))
        resp.raise_for_status()


def extract_mappings(fields):
    mappings = dict()
    for key in sorted(fields.keys()):
        if key.startswith('name'):
            num = int(key.split('name')[1])
            val = fields[f"ip{num}"]
            mappings[f"ip{num}"] = val
            mappings[fields[f"name{num}"]] = val
    return mappings


@app.route('/')
def index():
    return flask.render_template('index.html')


@app.route('/api/v1/autoregister/<location>/<machine_name>', methods=('GET', 'POST'))
@auth.login_required
def autoregister(location, machine_name):
    mappings = dict()
    statuses = []
    if flask.request.method == 'POST':
        mappings = extract_mappings(flask.request.values)

    default = 'public'
    if 'default' in flask.request.values:
        default = flask.request.values['default']

    if default not in mappings:
        # I tried to fix using a more standard way, but I couldn't make it
        # work. Not worth the effort, we don't trust this IP or anything it is
        # only for convenience, if a client spoofs it I don't really care.
        #
        # https://stackoverflow.com/a/12771438
        # https://esd.io/blog/flask-apps-heroku-real-ip-spoofing.html
        # https://werkzeug.palletsprojects.com/en/1.0.x/middleware/proxy_fix/
        if flask.request.headers.getlist("X-Forwarded-For"):
            mappings[default] = flask.request.headers.getlist("X-Forwarded-For")[0]
        elif flask.request.remote_addr:
            mappings[default] = flask.request.remote_addr
        else:
            statuses.append("Warning: could not determine public IP, skipping.")

    for i in mappings:
        statuses.append(f"Registered machine '{i}.{machine_name}' at location '{location}' with ip '{mappings[i]}'")
        dnsimple_post_machine(location, f"{i}.{machine_name}", mappings[i])
    if default in mappings:
        statuses.append(f"Registered machine '{machine_name}' at location '{location}' with ip '{mappings[default]}'")
        dnsimple_post_machine(location, machine_name, mappings[default])
    else:
        key = sorted(mappings.keys())[0]
        statuses.append(f"Registered machine '{machine_name}' at location '{location}' with ip '{mappings['key']}' (from {key} iface)")

    return "\n".join(statuses)


@app.route('/api/v1/delete/<location>/<machine_name>', methods=('GET', 'POST'))
@auth.login_required
def delete(location, machine_name):
    dnsimple_delete_machine(location, machine_name, prefixes=True)
    return f"Deleted machine '{machine_name}' at location '{location}' with public ip '{flask.request.remote_addr}'"


if __name__ == "__main__":
    app.run(host='0.0.0.0')
