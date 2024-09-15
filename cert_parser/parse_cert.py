#!/usr/bin/env python3
# vim: set ts=4 sts=4 sw=4 et ci nu ft=python:
"""Parse a RH manifest entitlement certificate."""

import argparse
import io
import json
import os
import re
import sys
import zipfile
from fnmatch import fnmatch
from operator import itemgetter
from pathlib import Path
from typing import List

# requires PyYAML
import yaml

# requires rhsm python module
from rhsm import certificate

MEDIA = re.compile(r" *\((Debug|Source)? *(RPMS?s|ISOs)\) *")


def parse_cmdline(argv: list) -> argparse.Namespace:
    """Process commandline args."""
    desc = """Processes a Red Hat entitlement manifest and produces appropriate
    output for creating remotes in pulp"""
    parser = argparse.ArgumentParser(description=desc)

    parser.add_argument(
        "inputfile",
        nargs="+",
        help="""path to either an entitlement certificate,
    or a manifest zipfile. If a manifest, will extract the certificates and put them
    into your local 'files' directory.
    Can be spefied multiple times.
    """,
    )

    # separate group for filtering options
    filtergrp = parser.add_argument_group(
        "Filtering Options", "These are additive (see '--any'), so all items must match"
    )
    filtergrp.add_argument(
        "-t", "--tag", help="show products with the given tag (exact match)"
    )
    filtergrp.add_argument(
        "-a", "--arch", help="show products with the given architecture (exact match)"
    )
    filtergrp.add_argument(
        "-l", "--label", help="show products matching the given label (glob)"
    )
    filtergrp.add_argument(
        "-n", "--name", help="show products matching provided product name (glob)"
    )
    filtergrp.add_argument(
        "--debug", action="store_true", default=False, help="include debug rpm repos"
    )
    filtergrp.add_argument(
        "--source",
        action="store_true",
        default=False,
        help="Include source repositories",
    )
    filtergrp.add_argument(
        "--iso", action="store_true", default=False, help="include ISO repositories"
    )
    filtergrp.add_argument(
        "--any",
        action="store_const",
        dest="match_all",
        const=False,
        help="""match any of the filters, rather than all.
        This will probably lead to many more results""",
    )
    # output options
    outgrp = parser.add_argument_group("Output options")
    outgrp.add_argument(
        "--list-tags",
        action="store_true",
        default=False,
        help="list all tags and exit",
    )
    outgrp.add_argument(
        "--list-products",
        action="store_true",
        default=False,
        help="Just list product names and exit",
    )
    outgrp.add_argument(
        "-y",
        "--yaml",
        action="store_const",
        dest="format",
        const="yaml",
        help="produce output in YAML",
    )
    outgrp.add_argument(
        "-j",
        "--json",
        action="store_const",
        dest="format",
        const="json",
        help="produce output in JSON",
    )
    outgrp.add_argument(
        "-o",
        "--output",
        help="output file, otherwise output is printed to stdout. Can be a directory.",
    )
    outgrp.add_argument(
        "-d",
        "--destdir",
        default=os.path.realpath(os.curdir),
        help="target directory for output files, created if missing. Default is CWD",
    )
    outgrp.add_argument(
        "-c",
        "--certs-dir",
        default="files",
        help="output directory for certificates, if extracting from a manifest",
    )
    outgrp.add_argument(
        "-m",
        "--multi-file",
        action="store_true",
        default=False,
        help="""create an output file for each product. --output is ignored
        in this case (unless it is a directory)""",
    )
    outgrp.add_argument(
        "--table",
        action="store_true",
        default=False,
        help="print a formatted table of mtatching repos",
    )

    opts = parser.parse_args(argv)

    # check if the cert exists
    opts.inputfile = [Path(p) for p in opts.inputfile]

    opts.certs_dir = Path(opts.certs_dir)

    if not opts.format:
        opts.format = "json"

    if opts.match_all is None:
        opts.match_all = True

    # build a dictionary of filters
    opts.filters = {
        "label": opts.label,
        "name": opts.name,
        "arches": opts.arch,
        "required_tags": opts.tag,
        "isos": opts.iso,
        "debug": opts.debug,
        "source": opts.source,
    }

    return opts


def filtered(item, match_all=True, filters={}):
    """Decide whether an item matches our defined filters.

    1. item.attr is a string and matches value
    2. item.attr is a list and any entry matches value
    """
    if not filters:
        return True
    matches = []
    # include_iso = filters.pop("isos", False)
    # include_debug = filters.pop("debug", False)
    # include_source = filters.pop("source", False)

    #     matches.append(include_iso and "-iso" in item.label)
    #     matches.append(include_debug and "-debug" in item.label)
    #     matches.append(include_source and "-source" in item.label)

    for att, val in filters.items():
        if val is None:
            matches.append(True)
            continue

        # TODO
        # handle 'iso' 'source' and 'debug' in labels

        # see if we have the given property/attibute.
        # we should, but meh.
        prop = getattr(item, att)

        if prop is not None:
            res = (
                any([fnmatch(x, val) for x in prop])
                if isinstance(prop, list)
                else fnmatch(prop, val)
            )
            # if we are in additive mode (the default),
            # we can fail immediately if no match
            if match_all and not res:
                return res
            else:
                matches.append(res)
        else:
            # move on, nothing to see here
            continue

    if match_all:
        res = all(matches)
        return res
    return any(matches)


def get_cert_content(certpath, match_all=True, filters={}) -> list:
    """Read and extract raw data from the certificate file."""
    cert = certificate.create_from_pem(certpath.read_text())

    products = [
        {
            "label": c.label,
            "name": c.name,
            "url": f"https://cdn.redhat.com{c.url}",
            "tags": c.required_tags,
            "certificate": certpath.name,
        }
        for c in cert.content
        if filtered(c, match_all, filters)
    ]

    return products


def dump(item, fmt):
    """Output an item in either YAML or JSON."""
    if fmt == "yaml":
        return yaml.safe_dump(item, default_flow_style=False)
    else:
        return json.dumps(item, indent=2)


def get_padding(dictlist):
    """Set padding."""
    res = {}

    for d in dictlist:
        for k, v in d.items():
            try:
                res[k] = max([res.get(k, 0), len("".join(v))])
            except TypeError:
                res[k] = max([res.get(k, 0), len("".join(str(v)))])
    return res


def extract_certs(manifest: Path, destdir: Path) -> List[Path]:
    """Extract entitlements certificates from RH manifest.

    save them locally
    return list of pathlib.path objects
    """
    pathlist = []
    try:
        # need to extract each of the certificates from it
        with zipfile.ZipFile(manifest, mode="r") as mf:
            content = zipfile.ZipFile(io.BytesIO(mf.read("consumer_export.zip")))
        for crt in zipfile.Path(
            content, at="export/entitlement_certificates/"
        ).iterdir():
            destdir.joinpath(crt.name).write_text(crt.read_text())
            pathlist.append(destdir.joinpath(crt.name))
    except Exception:
        raise
    return pathlist


def main(opts: argparse.Namespace):
    """Run all the things.

    Main script functionality

    Args: opts(argparse.NameSpace) - parsed commndline options
    """
    certlist = []
    matches = []
    for fname in opts.inputfile:
        if fname.suffix == ".zip":
            certlist.extend(extract_certs(fname, destdir=opts.certs_dir))
        else:
            certlist.append(fname)

    for cert in certlist:
        matches.extend(get_cert_content(cert, opts.match_all, opts.filters))

    if opts.list_tags:
        # each match has a 'tag' key containing a list of tags
        tags = set([t for m in matches for t in m.get("tags")])
        print("tags:")
        print("\n".join(sorted(list(tags))))
        sys.exit(0)

    if opts.list_products:
        products = set([MEDIA.sub("", m["name"]) for m in matches])
        print("Products:")
        print("\n".join(sorted(list(products))))
        sys.exit(0)

    if opts.destdir and not os.path.isdir(opts.destdir):
        try:
            os.makedirs(opts.destdir)
        except OSError as E:
            print(f"cannot create {E.filename} - {E.strerror}, falling back to CWD")
            opts.destdir = os.path.realpath(os.curdir)

    if opts.multi_file:
        for prod in matches:
            with open(
                os.path.join(opts.destdir, f"{prod['label']}.{opts.format}"), "w"
            ) as o:
                o.write(dump(prod, opts.format))
    elif opts.output:
        with open(os.path.join(opts.destdir, opts.output), "w") as o:
            o.write(dump(matches, opts.format))

    elif opts.table:
        padding = get_padding(matches)
        fmt = "{{label:{label}}} | {{name:{name}}} | {{url:{url}}}".format(**padding)
        print(fmt.format(label="label", name="Name", url="URL"))
        print("{l:.{label}} | {l:.{name}} | {l:.{url}}".format(l=".", **padding))
        for repo in sorted(matches, key=itemgetter("label")):
            print(fmt.format(**repo))
    else:
        # just dump the raw data
        print(dump(matches, opts.format))


if __name__ == "__main__":
    opts = parse_cmdline(sys.argv[1:])
    main(opts)
