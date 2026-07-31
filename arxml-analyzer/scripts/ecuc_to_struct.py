#!/usr/bin/env python3
"""Render ECUC parameter-definition containers (.epd) as C struct code.

A container definition is a struct; each parameter is a member with its C type
and, as a comment, its constraints (range / default / enum literals). Sub
containers are NOT inlined: each is its own standalone typedef, and the parent
references the child by type. Output order is parent-before-child (an analysis
view for reading structure, not for compilation -- so no forward declarations).
References become pointer members.

This is the core of detail-analysis branch B ("see the definition as a struct").

Usage:
    python ecuc_to_struct.py <definition.epd>
    python ecuc_to_struct.py <definition.epd> --container CanController
"""
import sys
import argparse
import xml.etree.ElementTree as ET


def localname(tag):
    return tag.split('}')[-1] if '}' in tag else tag


def short_name(elem):
    for c in elem:
        if localname(c.tag) == 'SHORT-NAME' and c.text:
            return c.text.strip()
    return None


def text_of(elem, name):
    for c in elem:
        if localname(c.tag) == name and c.text:
            return c.text.strip()
    return None


# ECUC parameter-def tag -> C base type
CTYPE = {
    'ECUC-INTEGER-PARAM-DEF': 'uint32',
    'ECUC-BOOLEAN-PARAM-DEF': 'boolean',
    'ECUC-FLOAT-PARAM-DEF': 'float64',
    'ECUC-STRING-PARAM-DEF': 'char*',
    'ECUC-FUNCTION-NAME-DEF': 'void*',
    'ECUC-ENUMERATION-PARAM-DEF': 'enum',
}
PARAM_DEFS = set(CTYPE)
REF_DEFS = {'ECUC-REFERENCE-DEF', 'ECUC-SYMBOLIC-NAME-REFERENCE-DEF',
            'ECUC-CHOICE-REFERENCE-DEF', 'ECUC-FOREIGN-REFERENCE-DEF'}


def constraint_comment(p, t):
    parts = []
    if t in ('ECUC-INTEGER-PARAM-DEF', 'ECUC-FLOAT-PARAM-DEF'):
        mn, mx = text_of(p, 'MIN'), text_of(p, 'MAX')
        if mn is not None or mx is not None:
            parts.append(f"{mn}..{mx}")
    dv = text_of(p, 'DEFAULT-VALUE')
    if dv is not None:
        parts.append(f"default={dv}")
    if t == 'ECUC-ENUMERATION-PARAM-DEF':
        lits = [short_name(x) for x in p.iter()
                if localname(x.tag) == 'ECUC-ENUMERATION-LITERAL-DEF']
        if lits:
            parts.append("{" + ", ".join(lits) + "}")
    return ("  // " + ", ".join(parts)) if parts else ""


def children_in(cont, holder):
    for c in cont:
        if localname(c.tag) == holder:
            return list(c)
    return []


def render_one(cont, out):
    """Emit ONE container as a standalone typedef. Sub-containers are referenced
    by type only (`AdcChannel_t AdcChannel;`), not inlined -- the child's own
    typedef appears separately below (analysis layout, parent-before-child)."""
    name = short_name(cont)
    out.append("typedef struct {")
    # parameters
    for p in children_in(cont, 'PARAMETERS'):
        t = localname(p.tag)
        if t in PARAM_DEFS:
            ctype = f"{short_name(p)}_e" if t == 'ECUC-ENUMERATION-PARAM-DEF' \
                else CTYPE[t]
            out.append(f"    {ctype:<16} {short_name(p)};"
                       f"{constraint_comment(p, t)}")
    # references (pointer members)
    for r in children_in(cont, 'REFERENCES'):
        dest = (text_of(r, 'DESTINATION-REF') or '').split('/')[-1]
        out.append(f"    void*            {short_name(r)};"
                   f"  // ref -> {dest}")
    # sub-containers: referenced by type only (flat -- defined separately below)
    for s in children_in(cont, 'SUB-CONTAINERS'):
        if 'CONTAINER-DEF' in localname(s.tag):
            sn = short_name(s)
            out.append(f"    {sn + '_t':<16} {sn};  // -> {sn}_t (아래 정의)")
    out.append(f"}} {name}_t;")
    out.append("")


def collect(cont, registry, order):
    """Depth-first walk; record each container once in parent-before-child order."""
    name = short_name(cont)
    if name in registry:
        return
    registry[name] = cont
    order.append(name)
    for s in children_in(cont, 'SUB-CONTAINERS'):
        if 'CONTAINER-DEF' in localname(s.tag):
            collect(s, registry, order)


def top_containers(root):
    for e in root.iter():
        if localname(e.tag) == 'ECUC-MODULE-DEF':
            for c in e:
                if localname(c.tag) == 'CONTAINERS':
                    return [x for x in c if 'CONTAINER-DEF' in localname(x.tag)]
    return []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('definition')
    ap.add_argument('--container', help='only render this container by name')
    args = ap.parse_args()
    try:
        root = ET.parse(args.definition).getroot()
    except (ET.ParseError, FileNotFoundError) as e:
        sys.exit(f"error: {e}")

    conts = top_containers(root)
    if not conts:
        sys.exit("no ECUC-MODULE-DEF / container definitions found "
                 "(is this a .epd parameter-definition file?)")

    # collect every container once, parent-before-child
    registry, order = {}, []
    for cont in conts:
        if args.container and short_name(cont) != args.container:
            continue
        collect(cont, registry, order)
    if not order:
        sys.exit(f"container '{args.container}' not found")

    # emit parent first, each child's own typedef flat below it
    # (analysis view -- not for compilation, so no forward declarations)
    out = []
    for name in order:
        render_one(registry[name], out)
    print("\n".join(out))


if __name__ == '__main__':
    main()
