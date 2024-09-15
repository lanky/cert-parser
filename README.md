# cert-tools
<!-- vim: set nofen nu :-->
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

alternatively, if you have `python-poetry` installed, you can use that:

```sh
poetry install
poetry shell
```

## Usage
Once you have a certificate or manifest zipfile, you need to do the following


### optionally unpack the manifest

The tool can read info directly from the manifest file now, but if you want to:

You should note that the manifests are nested zipfiles and that the `rct` tool
will extract the content into CWD, so create a target directory first and
change into it.

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
usage: parse_cert.py [-h] [-t TAG] [-a ARCH] [-l LABEL] [-n NAME] [--debug]
                     [--source] [--iso] [--any] [--list-tags]
                     [--list-products] [-y] [-j] [-o OUTPUT] [-d DESTDIR]
                     [-c CERTS_DIR] [-m] [--table]
                     inputfile [inputfile ...]

Processes a Red Hat entitlement manifest and produces appropriate output for
creating remotes in pulp

positional arguments:
  inputfile             path to either an entitlement certificate, or a
                        manifest zipfile. If a manifest, will extract the
                        certificates and put them into your local 'files'
                        directory. Can be spefied multiple times.

options:
  -h, --help            show this help message and exit

Filtering Options:
  These are additive (see '--any'), so all items must match

  -t TAG, --tag TAG     show products with the given tag (exact match)
  -a ARCH, --arch ARCH  show products with the given architecture (exact
                        match)
  -l LABEL, --label LABEL
                        show products matching the given label (glob)
  -n NAME, --name NAME  show products matching provided product name (glob)
  --debug               include debug rpm repos
  --source              Include source repositories
  --iso                 include ISO repositories
  --any                 match any of the filters, rather than all. This will
                        probably lead to many more results

Output options:
  --list-tags           list all tags and exit
  --list-products       Just list product names and exit
  -y, --yaml            produce output in YAML
  -j, --json            produce output in JSON
  -o OUTPUT, --output OUTPUT
                        output file, otherwise output is printed to stdout.
                        Can be a directory.
  -d DESTDIR, --destdir DESTDIR
                        target directory for output files, created if missing.
                        Default is CWD
  -c CERTS_DIR, --certs-dir CERTS_DIR
                        output directory for certificates, if extracting from
                        a manifest
  -m, --multi-file      create an output file for each product. --output is
                        ignored in this case (unless it is a directory)
  --table               print a formatted table of mtatching repos

```

## usage examples

### dump all entitlement info to stdout
`parse_cert.py entitlement_certs/CERTFILE`
or
`parse_cert.py manifest_file.zip` to process all the certificates in it

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

### Show details for just one repo (by label)
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

### dump all entitlements with 'rhel-8' in their labels
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

### Or in YAML, if you prefer

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

### dump all matching entilements to individual files
`parse_cert.py -l 'rhel-8*' entitlement_certificates/CERTFILE -m -d OUTPUTDIR`

```sh
$ ls OUTPUTDIR
rhel-8-appstream-beta-containers.json             rhel-8-for-x86_64-highavailability-debug-rpms.json       rhel-8-for-x86_64-sap-netweaver-debug-rpms.json
rhel-8-appstream-containers.json                  rhel-8-for-x86_64-highavailability-eus-debug-rpms.json   rhel-8-for-x86_64-sap-netweaver-eus-debug-rpms.json
rhel-8-for-x86_64-appstream-debug-rpms.json       rhel-8-for-x86_64-highavailability-eus-isos.json         rhel-8-for-x86_64-sap-netweaver-eus-isos.json
rhel-8-for-x86_64-appstream-eus-debug-rpms.json   rhel-8-for-x86_64-highavailability-eus-rpms.json         rhel-8-for-x86_64-sap-netweaver-eus-rpms.json
[...]
```
