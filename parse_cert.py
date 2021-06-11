#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: set ts=4 sts=4 sw=4 et ci nu ft=python:
import os
import sys
import argparse
import json
from fnmatch import fnmatch
  
# requires rhsm python module
from rhsm import certificate
  
# requires PyYAML
import yaml
  
  
def parse_cmdline(argv: list) -> argparse.Namespace:
    """
    process commandline args
    """
    desc = "Proceses a Red Hat entitlement certificate and produces appropriate output for creating remotes in pulp"
    parser = argparse.ArgumentParser(description=desc)
  
    parser.add_argument("cert", help="path to entitlement certificate")
  
    parser.add_argument(
        "-r",
        "--releasever",
        help="Specific version to create output for (e.g. 8.4). if not provided, you'll need to replace $releasever in URLs yourself",
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
        "--any",
        action="store_const",
        dest="match_all",
        const=False,
        help="match any of the filters, rather than all. This will probably lead to many more results",
    ) 
    # output options
    outgrp = parser.add_argument_group("Output options")
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
        "-m",
        "--multi-file",
        action="store_true",
        default=False,
        help="create an output file for each product. --output is ignored in this case",
    )

    opts = parser.parse_args(argv)

    # check if the cert exists
    if not os.path.exists(opts.cert):
        print(f"No such file: {opts.cert}. Please chack and try again")
        sys.exit(1)

    if not opts.format:
        opts.format = "json"

    # build a dictionary of filters
    opts.filters = {
        "label": opts.label,
        "name": opts.name,
        "arches": opts.arch,
        "required_tags": opts.tag,
    }

    return opts


def filtered(item: object, match_all: bool = True, **filters) -> bool:
    """
    returns true if
    1. item.attr is a string and matches value
    2. item.attr is a list and any entry matches value

    Args:
        item(rhsm.certificate2.Content): object representing a content item (repository)
    
    KWargs:
        match_all(bool): match every given filter (AND). Matches any if False
        filters: dictionary of filters mapping attributes/properties of item to fnmatch patterns.

        currently supported filters are
        'label', 'arches', 'name', 'required_tags'

        although anything that is an attriute of the rhsm.certificate2.Content object can be passed
    """
    if not filters:
        return True
    matches = []
    for att, val in filters.items():
        if val is None:
            matches.append(True)
            continue

        # see if we have the given property/attibute.
        # we should, but meh.
        prop = getattr(item, att)

        if prop is not None:
            res = (
                any([fnmatch(x, val) for x in prop])
                if isinstance(prop, list)
                else fnmatch(prop, val)
            )
            # if we are in additive mode (the default), we can fail immediately if no match
            if match_all and not res:
                return res
            else:
                matches.append(res)
        else:
            # move on, nothing to see here
            continue

    if match_all:
        return all(matches)
    return any(matches)


def get_cert_content(certpath: str, match_all: bool = True, filters: dict = {}) -> list:
    """
    read and extract raw data from the certificate file

    Args:
        opts(argparse.Namespace): parsed commandline options, like a named tuple.

    Returns:
        products(list[dict]): list of dictionaries representing RH products (repositories)

    """
    cert = certificate.create_from_file(certpath)

    products = [
        {
            "label": c.label,
            "name": c.name,
            "url": f"https://cdn.redhat.com{c.url}",
            "tag": c.required_tags
        }
        for c in cert.content if filtered(c, match_all, **filters)
    ]

    return products


def dump(item: object, fmt: str = "json") -> str:
    """
    produces a string representation of the object `item` in the chosen format

    Args:
        item(obj): JSON/YAML-serializable object
        fmt(str): 'yaml' or 'json' (default)
    """
    if fmt == "yaml":
        return yaml.safe_dump(item, default_flow_style=False)
    else:
        return json.dumps(item, indent=2)


def main(opts: argparse.Namespace):
    """
    Main script functionality

    Args: opts(argparse.NameSpace) - parsed commndline options
    """

    matching_items = get_cert_content(opts.cert, opts.match_all, opts.filters)

    if opts.destdir and not os.path.isdir(opts.destdir):
        try:
            os.makedirs(opts.destdir)
        except (IOError, OSError) as E:
            print(f"cannot create {opts.destdir}, falling back to CWD")
            opts.destdir = os.path.realpath(os.curdir)

    if opts.multi_file:
        for prod in matching_items:
            with open(
                os.path.join(opts.destdir, f"{prod['label']}.{opts.format}"), "w"
            ) as o:
                o.write(dump(prod, opts.format))
    elif opts.output:
        with open(os.path.join(opts.destdir, opts.output), "w") as o:
            o.write(dump(matching_items, opts.format))

    else:
        print(dump(matching_items, opts.format))


if __name__ == "__main__":
    opts = parse_cmdline(sys.argv[1:])
    main(opts)

