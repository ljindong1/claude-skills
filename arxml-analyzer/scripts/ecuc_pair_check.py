#!/usr/bin/env python3
"""Pair-match checker for an ECUC value file against a parameter-definition file.

A value file (ECUC-MODULE-CONFIGURATION-VALUES) and a definition file
(.epd, ECUC-MODULE-DEF) are a matching pair iff EVERY DEFINITION-REF in the
value file resolves to a path that actually exists in the definition file
(value subset of definition). One missing reference => not a pair.

Usage:
    python ecuc_pair_check.py <value.arxml> <definition.epd>
    python ecuc_pair_check.py <value.arxml> <definition.epd> --json
"""
import sys
import json
import argparse
import xml.etree.ElementTree as ET


def localname(tag):
    return tag.split('}')[-1] if '}' in tag else tag


def short_name(elem):
    for c in elem:
        if localname(c.tag) == 'SHORT-NAME' and c.text:
            return c.text.strip()
    return None


def collect_value_refs(root):
    """All DEFINITION-REF targets in the value file (unique)."""
    refs = set()
    for e in root.iter():
        if localname(e.tag) == 'DEFINITION-REF' and e.text:
            refs.add(e.text.strip())
    return refs


def collect_defined_paths(root):
    """All definable full paths in the definition file, built from the
    SHORT-NAME hierarchy of packages / module-def / *-DEF elements."""
    defined = set()

    def walk(elem, path):
        nm = short_name(elem)
        here = path
        t = localname(elem.tag)
        if nm and (t.endswith('-DEF') or t == 'ECUC-MODULE-DEF'
                   or t == 'AR-PACKAGE'):
            here = path + '/' + nm
            defined.add(here)
        for c in elem:
            walk(c, here)

    walk(root, '')
    return defined


def module_paths(refs):
    """Top-package + module portion of each ref (first 2 path segments)."""
    return set('/'.join(r.split('/')[:3]) for r in refs if r.startswith('/'))


def check(value_path, def_path):
    vroot = ET.parse(value_path).getroot()
    droot = ET.parse(def_path).getroot()

    val_refs = collect_value_refs(vroot)
    defined = collect_defined_paths(droot)

    missing = sorted(r for r in val_refs if r not in defined)
    is_pair = (len(missing) == 0 and len(val_refs) > 0)

    return {
        'value_file': value_path,
        'definition_file': def_path,
        'value_ref_count': len(val_refs),
        'defined_path_count': len(defined),
        'missing_count': len(missing),
        'missing_examples': missing[:10],
        'value_module_paths': sorted(module_paths(val_refs)),
        'is_pair': is_pair,
    }


def render(r):
    L = ["=" * 56, "ECUC PAIR CHECK", "=" * 56,
         f"value      : {r['value_file']}",
         f"definition : {r['definition_file']}",
         f"value refs : {r['value_ref_count']}",
         f"defined    : {r['defined_path_count']}",
         f"missing    : {r['missing_count']}"]
    if r['is_pair']:
        L.append("\nRESULT: MATCH  (value subset of definition)")
    else:
        L.append("\nRESULT: NOT A PAIR")
        if r['value_ref_count'] == 0:
            L.append("  reason: value file has no DEFINITION-REF")
        else:
            L.append("  reason: these value references are not found in the"
                     " definition file:")
            for m in r['missing_examples']:
                L.append(f"    - {m}")
        L.append("  value file actually requires the definition at:")
        for m in r['value_module_paths']:
            L.append(f"    -> {m}")
        L.append("  Provide the definition (.epd) for that path.")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('value')
    ap.add_argument('definition')
    ap.add_argument('--json', action='store_true')
    args = ap.parse_args()
    try:
        r = check(args.value, args.definition)
    except (ET.ParseError, FileNotFoundError) as e:
        sys.exit(f"error: {e}")
    print(json.dumps(r, indent=2, ensure_ascii=False) if args.json else render(r))


if __name__ == '__main__':
    main()
