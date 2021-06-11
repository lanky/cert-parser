# cert-tools
A python tool (possibly tools) to extract entitlement data from RH Entitlement certificates (which
can be downloaded from the Red Hat Portal, or found on registered RHEL hosts)

## Requirements

This toolset was developed using python3, it is not tested on python < 3. Might work, might not.
YMMV.

You'll need an entitlement certificate, or manifest zipfile. The manifests can be downloaded from
the RH portal at https://access.redhat.com

### system packages
  * python3
  * python3-devel (for the virtualenv)

### Python modules from PyPi

  * rhsm
  * python-dateutil

It's probably best to use a python virutalenv for this. Personally I like using `virtualenvwrapper`
athough you can do these things manually, or use `pip3 install --user` if you really want.

```
# mkvirtualenv -p python3 -r requirements.txt rhcerts
```



