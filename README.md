# TeraDynDNS

TeraDynDNS is a simple web app which lets machines you manage update their dns
entries all by themselves. It works with dnsimple.com and could be made to work
with any dns service which supports a rest API pretty easily.

# How it works

Say you own a domain name already, such as example.com. You might wish to have
your machines available under dyn.example.com. Now, no matter what IP address
your laptop has, you can always ping laptop.dyn.example.com. You can also get
an internal or external IP address by looking up public.laptop.dyn.example.com
or eth0.laptop.dyn.example.com. TeraDynDNS client can report any or all of
these and the webapp will safely store credentials to make the appropriate
calls to dnsimple.com to update your DNS records.

# Configuration

Everything you need to tweak is in properties.json.  You can find a starting example in example-properties.json.
```
{
    "dnsimple_oauth_token":"xxx",
    "zone_root":"example.com",
    "dns_prefix":"dyn",
    "usermap":{"user1":"pbkdf2:sha256:260000$J9rrEwtsGsnwoSAc$e2c06f6f84133b95c340a9423e95599905fea3d3e3d1c909b4f0ae4f24bfc763"}
}
```
The above password for "user1" is "password".  Please don't use that as your password =)

## `dnsimple_oauth_token`: To get this, you need to generate an access token following the directions here: https://developer.dnsimple.com/v2/oauth/
Essentially, I created an authorized application then used CURL to make calls to get the token.  For me, it looked like this:

* go to https://dnsimple.com/a/$YOUR_ACCT_ID/account/automation and create an oauth application, note the CLIENT_ID and CLIENT_SECRET
* go to https://dnsimple.com/oauth/authorize?response_type=code&client_id=$OAUTH_ID&state=SOME_INTERESTING_STRING_HERE
* This, if successful, will redirect you to a URL with a "code" parameter, which you should note as OAUTH_CODE
* Now, you can post to https://api.dnsimple.com/v2/oauth/access_token giving the parameters grant_type "authorization_code", client_id (same as above), client_secret (same as above), code (from the previous step), redirect_uri (same as above), state (same string as above).  The reply should look like this:
```
{
  "access_token": "zKQ7OLqF5N1gylcJweA9WodA000BUNJD",
  "token_type": "Bearer",
  "scope": null,
  "account_id": 1
}
```
The "access_token" above is the thing you put in properties.json as "dnsimple_oauth_token". It doesn't seem to require rotating or expire or anything, so please protect it =)

You can test it as follows:
```
$ curl -H "Content-Type: application/json" -H 'Accept: application/json' -H "Authorization: Bearer $(cat ~/.dnsimple-token)" https://api.dnsimple.com/v2/whoami | jq .
{
  "data": {
    "user": null,
    "account": {
      "id": <REDACTED>,
      "email": "<REDACTED>",
      "plan_identifier": "personal-v2-monthly",
      "created_at": "2022-10-03T22:19:53Z",
      "updated_at": "2022-10-03T22:21:41Z"
    }
  }
}
```

## `zone_root`: the domain name you are using

For example, the above config would register machine "foo" in location "bar" as foo.bar.dyn.example.com.

## `dns_prefix`: the prefix to use with your domain name

For example, the above config would register machine "foo" in location "bar" as foo.bar.dyn.example.com.
TODO: in the future, I could support leaving it blank to allow foo.bar.example.com, but for now it is required.

## `usermap`: the map of usernames/passwords to make requests

The application keeps your oauth token safe, so you don't have to curl directly
to the dnsimple.com API using a full credential that can do anything (like
delete all your shit).  That said, you still don't want someone finding your
endpoint and registering a bunch of DNS entries (or deleting yours), so you
should have a shared secret to authenticate your clients.  For simplicity, we
do this using basic auth and all authenticated users can any anything the app
lets you do (create records, delete records, etc). Of course, in the absence of
bugs (which you should not assume!) you can only modify records under the
domain name prefix, so it is still relatively safe.

# example client call

For now, a client is as easy as:
```
$ curl -u 'user1:password' -X POST -d 'name1=eno1&ip1=192.168.1.101&name2=wlan0&ip2=192.168.1.105&name3=public&ip3=1.2.3.4' http://dyn.example.com/api/v1/autoregister/home/workdesktop
```
This would result in the following DNS entries:
```
eno1.workdesktop.home.dyn.example.com 192.168.1.101
wlan0.workdesktop.home.dyn.example.com 192.168.1.105
public.workdesktop.home.dyn.example.com 1.2.3.4
workdesktop.home.dyn.example.com 1.2.3.4
```
If you do not specify a `public` named interface, the remote_addr as seen by the service will be used (for both `public` and the top-level entry for that machine).

# smart client

You can also run the smart client:
```
$ virtualenv .ve
$ source .ve/bin/activate
$ pip install -r requirements.txt
$ bin/teradyndns-client.py --service http://dyn.example.com --user user1 --password password --location home --machine laptop
Response: Registered machine 'ip1.laptop' at location 'home' with ip '192.168.1.196'
Registered machine 'wlp0s20f3.laptop' at location 'home' with ip '192.168.1.196'
Registered machine 'ip2.laptop' at location 'home' with ip '192.168.1.204'
Registered machine 'eno1.laptop' at location 'home' with ip '192.168.1.204'
Registered machine 'public.laptop' at location 'home' with ip '1.2.3.4'
Registered machine 'laptop' at location 'home' with ip '1.2.3.4'
```

# TODO

Nice to have features:

* IPv6 support
* better caching/efficiency
* support emtpy dns prefix
* support empty location
* Query all existing machines
