#!/usr/bin/env python3
"""Render ECUC configuration-values (Ecud_*.arxml) as C designated initializers.

The paired companion of ecuc_to_struct.py:
  - ecuc_to_struct.py : a parameter DEFINITION (.epd)  -> an EMPTY struct
  - ecuc_to_init.py   : the parameter VALUES (Ecud_*)  -> the struct FILLED IN

Each ECUC-CONTAINER-VALUE becomes `const <Def>_t <ShortName> = { .member = value, ... };`.
Values are the real values from the ARXML; the C-initializer syntax is only a
representation framed on branch-B's struct. This is NOT the vendor-generated
*_PBcfg.c (generated code uses register-oriented field names / bit-encoded
constants); it is a learning view that mirrors the definition struct.

This is detail-analysis branch C, item C-4 ("see the values as a filled struct").

Pairing:
  - With --def (the .epd): full output -- booleans render TRUE/FALSE, integers get
    a 'u' suffix, and a `/* 정의 기본 X */` comment is added where the set value
    differs from the definition default. (recommended; needs the paired .epd)
  - Without --def: reduced output -- raw values, no type coercion, no default
    comments (the value file alone does not carry types/defaults).

Repeated sibling containers of the same definition (e.g. 21x AdcChannel) are
each emitted as their own standalone const (flat); the parent references them
as an array of pointers (`.AdcChannel = { &AdcChannel_0, &AdcChannel_1 }`).
Output order is parent-before-child (analysis view, not for compilation).

Usage:
    python ecuc_to_init.py <values.arxml>
    python ecuc_to_init.py <values.arxml> --def <definition.epd>
    python ecuc_to_init.py <values.arxml> --def <def.epd> --container AdcHwUnit
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


def last_seg(ref):
    return ref.split('/')[-1] if ref else ref


# ---- definition index (built only when --def is given) --------------------
PARAM_DEF_TAGS = {
    'ECUC-INTEGER-PARAM-DEF': 'int',
    'ECUC-BOOLEAN-PARAM-DEF': 'bool',
    'ECUC-FLOAT-PARAM-DEF': 'float',
    'ECUC-STRING-PARAM-DEF': 'str',
    'ECUC-FUNCTION-NAME-DEF': 'fn',
    'ECUC-ENUMERATION-PARAM-DEF': 'enum',
}


def build_def_index(def_root):
    """short-name -> {'kind': ..., 'default': ...} for every parameter def."""
    idx = {}
    for e in def_root.iter():
        t = localname(e.tag)
        if t in PARAM_DEF_TAGS:
            nm = short_name(e)
            if nm and nm not in idx:
                idx[nm] = {'kind': PARAM_DEF_TAGS[t],
                           'default': text_of(e, 'DEFAULT-VALUE')}
    return idx


# ---- value extraction ------------------------------------------------------
NUM_VAL = 'ECUC-NUMERICAL-PARAM-VALUE'
TXT_VAL = 'ECUC-TEXTUAL-PARAM-VALUE'
REF_VAL = 'ECUC-REFERENCE-VALUE'
CONT_VAL = 'ECUC-CONTAINER-VALUE'


def coerce(raw, info):
    """Render one parameter value as C, using def info when available."""
    if info is None:                      # no --def: print raw
        return raw, ''
    kind, default = info['kind'], info['default']
    truthy = ('1', 'true', 'True', 'TRUE')
    if kind == 'bool':
        # normalise both sides before comparing (raw '0' == default 'false')
        v = 'TRUE' if raw in truthy else 'FALSE'
        dv = ('TRUE' if default in truthy else 'FALSE') if default is not None else None
        comment = f"  /* 정의 기본 {dv} */" if (dv is not None and v != dv) else ''
        return v, comment
    differs = (default is not None and raw is not None
               and raw.strip() != default.strip())
    comment = f"  /* 정의 기본 {default} */" if differs else ''
    if kind == 'int':
        v = f"{raw}u" if raw is not None and raw.lstrip('-').isdigit() else raw
    else:                                 # enum / str / float / fn
        v = raw
    return v, comment


def params_of(cont):
    out = []
    for holder in cont:
        if localname(holder.tag) != 'PARAMETER-VALUES':
            continue
        for p in holder:
            t = localname(p.tag)
            if t in (NUM_VAL, TXT_VAL):
                nm = last_seg(text_of(p, 'DEFINITION-REF'))
                out.append((nm, text_of(p, 'VALUE')))
    return out


def refs_of(cont):
    out = []
    for holder in cont:
        if localname(holder.tag) != 'REFERENCE-VALUES':
            continue
        for r in holder:
            if localname(r.tag) == REF_VAL:
                nm = last_seg(text_of(r, 'DEFINITION-REF'))
                tgt = last_seg(text_of(r, 'VALUE-REF'))
                out.append((nm, tgt))
    return out


def sub_containers(cont):
    for holder in cont:
        if localname(holder.tag) == 'SUB-CONTAINERS':
            return [c for c in holder if localname(c.tag) == CONT_VAL]
    return []


def def_of(cont):
    return last_seg(text_of(cont, 'DEFINITION-REF'))


def module_containers(root):
    for e in root.iter():
        if localname(e.tag) == 'ECUC-MODULE-CONFIGURATION-VALUES':
            for c in e:
                if localname(c.tag) == 'CONTAINERS':
                    return short_name(e), [x for x in c
                                           if localname(x.tag) == CONT_VAL]
    return None, []


# ---- emit ------------------------------------------------------------------
def emit(cont, idx, out, emitted_groups):
    """Emit each container as a STANDALONE const (flat), parent BEFORE children.

    The parent is written first, referencing each child by variable name (an
    array of pointers when a child def repeats); the children's own consts are
    appended afterwards. Analysis view (parent-before-child), not for compiling.
    Returns this container's variable name.
    """
    name = short_name(cont) or def_of(cont)
    dname = def_of(cont)

    # group children by definition name; resolve each child's var name first
    groups = {}
    for k in sub_containers(cont):
        groups.setdefault(def_of(k), []).append(k)

    child_lines = []
    deferred = []          # (child_cont) to emit AFTER this parent
    for gdef, members in groups.items():
        varnames = [short_name(m) or def_of(m) for m in members]
        deferred.extend(members)
        if len(varnames) == 1:
            child_lines.append(f"    .{gdef:<26} = &{varnames[0]},")
        else:
            joined = ", ".join("&" + v for v in varnames)
            child_lines.append(f"    .{gdef:<26} = {{ {joined} }},  /* {len(varnames)} */")

    # parent body first
    out.append(f"const {dname}_t {name} = {{")
    for pname, raw in params_of(cont):
        v, cmt = coerce(raw, idx.get(pname) if idx else None)
        out.append(f"    .{pname:<26} = {v},{cmt}")
    for rname, tgt in refs_of(cont):
        rhs = f"&{tgt}" if tgt else "NULL_PTR"
        out.append(f"    .{rname:<26} = {rhs},   /* VALUE-REF */")
    out.extend(child_lines)
    out.append("};")
    out.append("")

    # then children, flat, below the parent
    for child in deferred:
        emit(child, idx, out, emitted_groups)
    return name


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('values')
    ap.add_argument('--def', dest='definition',
                    help='paired .epd (enables typed values + default comments)')
    ap.add_argument('--container', help='only this top-level container by name')
    args = ap.parse_args()

    try:
        vroot = ET.parse(args.values).getroot()
    except (ET.ParseError, FileNotFoundError) as e:
        sys.exit(f"error: {e}")

    idx = None
    if args.definition:
        try:
            idx = build_def_index(ET.parse(args.definition).getroot())
        except (ET.ParseError, FileNotFoundError) as e:
            sys.exit(f"error reading --def: {e}")

    module, conts = module_containers(vroot)
    if not conts:
        sys.exit("no ECUC-MODULE-CONFIGURATION-VALUES found "
                 "(is this a values file?)")

    banner = (f"/* module: {module} | "
              f"{'paired with .epd: typed + default comments' if idx else 'values only: raw, no defaults'} */")
    out = [banner, ""]
    for cont in conts:
        if args.container and short_name(cont) != args.container:
            continue
        emit(cont, idx, out, set())
    print("\n".join(out))


if __name__ == '__main__':
    main()
