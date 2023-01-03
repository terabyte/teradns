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





