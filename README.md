# cert-tools
A python tool (possibly tools) to extract entitlement data from RH Entitlement certificates (which
can be downloaded from the Red Hat Portal, or found on registered RHEL hosts)

## Requirements

This toolset was developed using python3, it has been tested on python 3. Might work, might not.
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

```sh
mkvirtualenv -p python3 -r requirements.txt rhcerts
```

## Usage
Once you have a certificate or manifest zipfile, you need to do the following


### unpack the manifest
I may add this functionality in a future update, but for now...

You should note that the manifests are nested zipfiles and that the `rct` tool will extract the
content into CWD, so create a target directory first and change into it.

```sh
mkdir manifest
cd manifest
rct dump-manifest $MANIFESTFILE
```

### process the certificates
There are lots of files in a manifest archive, but we only really require those in the
`export/entitlement_certs` directory.
They generally have long numerical names

The script has built-in help

```sh
$ ./parse_cert.py --help
usage: parse_cert.py [-h] [-r RELEASEVER] [-t TAG] [-a ARCH] [-l LABEL]
                     [-n NAME] [--any] [-y] [-j] [-o OUTPUT] [-d DESTDIR] [-m]
                     [--table]
                     cert

Proceses a Red Hat entitlement certificate and produces appropriate output for
creating remotes in pulp

positional arguments:
  cert                  path to entitlement certificate

optional arguments:
  -h, --help            show this help message and exit

Filtering Options:
  These are additive (see '--any'), so all items must match

  -t TAG, --tag TAG     show products with the given tag (exact match)
  -a ARCH, --arch ARCH  show products with the given architecture (exact
                        match)
  -l LABEL, --label LABEL
                        show products matching the given label (glob)
  -n NAME, --name NAME  show products matching provided product name (glob)
  --any                 match any of the filters, rather than all. This will
                        probably lead to many more results

Output options:
  -y, --yaml            produce output in YAML
  -j, --json            produce output in JSON
  -o OUTPUT, --output OUTPUT
                        output file, otherwise output is printed to stdout.
                        Can be a directory.
  -d DESTDIR, --destdir DESTDIR
                        target directory for output files, created if missing.
                        Default is CWD
  -m, --multi-file      create an output file for each product. --output is
                        ignored in this case
  --table               print a formatted table of mtatching repos

```

Basic usage:

1. dump all entitlement info to stdout
`parse_cert.py entitlement_certs/CERTFILE`

```json
[
  {
    "label": "rhel-atomic-host-source-rpms",
    "name": "Red Hat Enterprise Linux Atomic Host (Source RPMs)",
    "url": "https://cdn.redhat.com/content/dist/rhel/atomic/7/7Server/$basearch/source/SRPMS",
    "tag": [
      "rhel-atomic-7"
    ]
  },
...

```

1. Show details for just one repo (by label)
`$ parse_cert.py -l 'rhel-8-for-x86_64-baseos-rpms' entitlement_certificates/CERTFILE`

```json
[
  {
    "label": "rhel-8-for-x86_64-baseos-rpms",
    "name": "Red Hat Enterprise Linux 8 for x86_64 - BaseOS (RPMs)",
    "url": "https://cdn.redhat.com/content/dist/rhel8/$releasever/x86_64/baseos/os",
    "tag": [
      "rhel-8-x86_64"
    ]
  }
]
```

2. dump all entitlements with 'rhel-8' in their labels
`parse_cert.py -l 'rhel-8*' entitlement_certificates/CERTFILE`

```json
[
  {
    "label": "rhel-8-appstream-containers",
    "name": "Red Hat Enterprise Linux 8 - AppStream (Containers)",
    "url": "https://cdn.redhat.com/content/dist/containers/rhel8/multiarch/appstream/containers",
    "tag": [
      "rhel-8"
    ]
  },
```

3. Or in YAML, if you prefer

`parse_cert.py -l 'rhel-8*' -y entitlement_certificates/CERTFILE`
```yaml
- label: rhel-8-appstream-containers
  name: Red Hat Enterprise Linux 8 - AppStream (Containers)
  tag:
  - rhel-8
  url: https://cdn.redhat.com/content/dist/containers/rhel8/multiarch/appstream/containers
- label: rhel-8-appstream-beta-containers
  name: Red Hat Enterprise Linux 8 - AppStream Beta (Containers)
  tag:
  - rhel-8-beta
[...]
```

3. dump all matching entilements to individual files
`parse_cert.py -l 'rhel-8*' entitlement_certificates/CERTFILE -m -d OUTPUTDIR`

```sh
$ ls OUTPUTDIR
rhel-8-appstream-beta-containers.json             rhel-8-for-x86_64-highavailability-debug-rpms.json       rhel-8-for-x86_64-sap-netweaver-debug-rpms.json
rhel-8-appstream-containers.json                  rhel-8-for-x86_64-highavailability-eus-debug-rpms.json   rhel-8-for-x86_64-sap-netweaver-eus-debug-rpms.json
rhel-8-for-x86_64-appstream-debug-rpms.json       rhel-8-for-x86_64-highavailability-eus-isos.json         rhel-8-for-x86_64-sap-netweaver-eus-isos.json
rhel-8-for-x86_64-appstream-eus-debug-rpms.json   rhel-8-for-x86_64-highavailability-eus-rpms.json         rhel-8-for-x86_64-sap-netweaver-eus-rpms.json
[...]
```
