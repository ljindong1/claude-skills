#!/usr/bin/env python3
"""ARXML structural inspector.

Reads an AUTOSAR ARXML file and emits a deterministic structural report:
file identity, package tree, element-type counts, FIBEX reference targets,
communication direction split, ECU-INSTANCE topology, and SWC composition.

It does NOT interpret or judge the file -- it only extracts facts. The
SKILL.md instructions handle conceptual interpretation and Confluence output.

Usage:
    python arxml_inspect.py <file.arxml>            # human-readable report
    python arxml_inspect.py <file.arxml> --json     # machine-readable JSON
"""
import sys
import json
import argparse
from collections import Counter, OrderedDict
import xml.etree.ElementTree as ET


def localname(tag):
    """Strip XML namespace: '{...}SHORT-NAME' -> 'SHORT-NAME'."""
    return tag.split('}')[-1] if '}' in tag else tag


def child(elem, name):
    for c in elem:
        if localname(c.tag) == name:
            return c
    return None


def children(elem, name):
    return [c for c in elem if localname(c.tag) == name]


def short_name(elem):
    sn = child(elem, 'SHORT-NAME')
    return sn.text.strip() if sn is not None and sn.text else None


def text_of(elem, name):
    c = child(elem, name)
    return c.text.strip() if c is not None and c.text else None


# Element tags that are worth counting in a structural overview.
INTERESTING_TAGS = [
    'SYSTEM', 'ECU-INSTANCE', 'COMPOSITION-SW-COMPONENT-TYPE',
    'SW-COMPONENT-PROTOTYPE', 'ASSEMBLY-SW-CONNECTOR',
    'DELEGATION-SW-CONNECTOR', 'SYSTEM-MAPPING', 'SYSTEM-SIGNAL',
    'I-SIGNAL', 'I-SIGNAL-GROUP', 'SYSTEM-SIGNAL-GROUP',
    'CAN-CLUSTER', 'LIN-CLUSTER', 'CAN-FRAME', 'LIN-UNCONDITIONAL-FRAME',
    'I-SIGNAL-I-PDU', 'NM-PDU', 'N-PDU', 'DCM-I-PDU',
    'I-SIGNAL-I-PDU-GROUP', 'PNC-MAPPING',
    'ECUC-MODULE-CONFIGURATION-VALUES', 'ECUC-CONTAINER-VALUE',
    'DIAGNOSTIC-CONTRIBUTION-SET', 'BSW-MODULE-DESCRIPTION',
    'APPLICATION-SW-COMPONENT-TYPE', 'SERVICE-SW-COMPONENT-TYPE',
    'COMPLEX-DEVICE-DRIVER-SW-COMPONENT-TYPE',
    'ECU-ABSTRACTION-SW-COMPONENT-TYPE', 'SENSOR-ACTUATOR-SW-COMPONENT-TYPE',
]


# Tags that appear everywhere in any AUTOSAR file -- excluded from the
# "file-specific tags" view so only characteristic tags remain.
COMMON_TAGS = {
    'AUTOSAR', 'AR-PACKAGES', 'AR-PACKAGE', 'ELEMENTS', 'SHORT-NAME',
    'CATEGORY', 'ADMIN-DATA', 'LANGUAGE', 'SDGS', 'SDG', 'SD', 'ANNOTATIONS',
    'ANNOTATION', 'ANNOTATION-TEXT', 'ANNOTATION-ORIGIN', 'LABEL',
    'DEFINITION-REF', 'UUID', 'L-2', 'DESC', 'LONG-NAME', 'INTRODUCTION',
    'P', 'VALUE', 'SHORT-LABEL',
}


def walk_packages(pkg, depth, acc):
    """Recursively record AR-PACKAGE tree, flagging empty packages."""
    name = short_name(pkg)
    elements = child(pkg, 'ELEMENTS')
    sub = child(pkg, 'AR-PACKAGES')
    n_elements = len([c for c in elements]) if elements is not None else 0
    n_subpkgs = len(children(sub, 'AR-PACKAGE')) if sub is not None else 0
    is_empty = (n_elements == 0 and n_subpkgs == 0)
    acc.append({
        'depth': depth, 'name': name,
        'elements': n_elements, 'subpackages': n_subpkgs,
        'empty': is_empty,
    })
    if sub is not None:
        for sp in children(sub, 'AR-PACKAGE'):
            walk_packages(sp, depth + 1, acc)


def inspect(path):
    tree = ET.parse(path)
    root = tree.getroot()

    report = OrderedDict()

    # --- File identity -------------------------------------------------
    schema = None
    for k, v in root.attrib.items():
        if 'schemaLocation' in k:
            schema = v
            break
    xmlns = root.tag.split('}')[0].strip('{') if '}' in root.tag else None
    report['file'] = {'path': path, 'root_tag': localname(root.tag),
                      'xmlns': xmlns, 'schemaLocation': schema}

    # gather every element once
    all_elems = list(root.iter())

    # provenance (DBC import etc.)
    origins = [e.text.strip() for e in all_elems
               if localname(e.tag) == 'ANNOTATION-ORIGIN' and e.text]
    report['provenance'] = sorted(set(origins))

    # SYSTEM category
    systems = [e for e in all_elems if localname(e.tag) == 'SYSTEM']
    report['systems'] = [{'name': short_name(s),
                          'category': text_of(s, 'CATEGORY')} for s in systems]

    # --- Package tree --------------------------------------------------
    top_pkgs_holder = child(root, 'AR-PACKAGES')
    pkg_tree = []
    if top_pkgs_holder is not None:
        for p in children(top_pkgs_holder, 'AR-PACKAGE'):
            walk_packages(p, 0, pkg_tree)
    report['package_tree'] = pkg_tree
    report['empty_packages'] = [p['name'] for p in pkg_tree if p['empty']]

    # --- Element-type counts ------------------------------------------
    counts = Counter(localname(e.tag) for e in all_elems)
    report['element_counts'] = {t: counts[t] for t in INTERESTING_TAGS
                                if counts.get(t)}

    # --- FIBEX reference targets --------------------------------------
    fibex = Counter()
    for e in all_elems:
        if localname(e.tag) == 'FIBEX-ELEMENT-REF':
            fibex[e.attrib.get('DEST', '?')] += 1
    report['fibex_refs'] = dict(fibex.most_common())

    # --- Communication direction split --------------------------------
    dirs = Counter(e.text.strip() for e in all_elems
                   if localname(e.tag) == 'COMMUNICATION-DIRECTION' and e.text)
    report['comm_direction'] = dict(dirs)

    # --- PNC ----------------------------------------------------------
    pnc_ids = [e.text.strip() for e in all_elems
               if localname(e.tag) == 'PNC-IDENTIFIER' and e.text]
    report['pnc'] = {
        'identifiers': pnc_ids,
        'vector_length': next((e.text.strip() for e in all_elems
                               if localname(e.tag) == 'PNC-VECTOR-LENGTH' and e.text), None),
        'vector_offset': next((e.text.strip() for e in all_elems
                               if localname(e.tag) == 'PNC-VECTOR-OFFSET' and e.text), None),
    }

    # --- ECU-INSTANCE topology ----------------------------------------
    ecus = []
    for e in all_elems:
        if localname(e.tag) != 'ECU-INSTANCE':
            continue
        ctrls = []
        cc = child(e, 'COMM-CONTROLLERS')
        if cc is not None:
            for c in cc:
                ctrls.append({'type': localname(c.tag), 'name': short_name(c)})
        # count comm ports under this ECU
        ports = sum(1 for sub in e.iter()
                    if localname(sub.tag) in ('I-SIGNAL-PORT', 'I-PDU-PORT',
                                              'FRAME-PORT'))
        ecus.append({'name': short_name(e), 'controllers': ctrls,
                     'comm_ports': ports})
    report['ecu_instances'] = ecus

    # --- SWC composition ----------------------------------------------
    comps = []
    for e in all_elems:
        if localname(e.tag) != 'COMPOSITION-SW-COMPONENT-TYPE':
            continue
        protos = []
        comp_holder = child(e, 'COMPONENTS')
        if comp_holder is not None:
            for p in children(comp_holder, 'SW-COMPONENT-PROTOTYPE'):
                tref = child(p, 'TYPE-TREF')
                protos.append({
                    'name': short_name(p),
                    'kind': tref.attrib.get('DEST') if tref is not None else None,
                    'path': tref.text.strip() if tref is not None and tref.text else None,
                })
        conn_assembly = sum(1 for sub in e.iter()
                            if localname(sub.tag) == 'ASSEMBLY-SW-CONNECTOR')
        conn_deleg = sum(1 for sub in e.iter()
                         if localname(sub.tag) == 'DELEGATION-SW-CONNECTOR')
        by_kind = Counter(p['kind'] for p in protos)
        comps.append({
            'name': short_name(e),
            'prototype_count': len(protos),
            'by_kind': dict(by_kind),
            'assembly_connectors': conn_assembly,
            'delegation_connectors': conn_deleg,
            'prototypes': protos,
        })
    report['compositions'] = comps

    # --- File-specific tags (exclude common ones) ---------------------
    tag_counts = Counter(localname(e.tag) for e in all_elems)
    special = [(t, n) for t, n in tag_counts.most_common()
               if t not in COMMON_TAGS]
    report['specific_tags'] = special[:30]

    # --- Meaning-based path tree (containers not counted as depth) -----
    # Shows named AR-PACKAGE / SYSTEM / ECU-INSTANCE / COMPOSITION and the
    # direct child containers of the three pillars, with a kind summary.
    PILLARS = ('SYSTEM', 'ECU-INSTANCE', 'COMPOSITION-SW-COMPONENT-TYPE')
    tree_lines = []

    def kind_summary(container):
        kinds = Counter(localname(c.tag) for c in container)
        return ", ".join(f"{k}x{v}" for k, v in kinds.items())

    def emit_pillar(elem):
        tree_lines.append({'depth': 1, 'tag': localname(elem.tag),
                           'name': short_name(elem), 'summary': None})
        for c in elem:
            t = localname(c.tag)
            if t == 'SHORT-NAME':
                continue
            n_children = len(list(c))
            summary = kind_summary(c) if n_children else None
            tree_lines.append({'depth': 2, 'tag': t,
                               'name': None, 'summary': summary})

    if top_pkgs_holder is not None:
        for p in children(top_pkgs_holder, 'AR-PACKAGE'):
            tree_lines.append({'depth': 0, 'tag': 'AR-PACKAGE',
                               'name': short_name(p),
                               'summary': 'EMPTY' if (child(p, 'ELEMENTS') is None
                                          and child(p, 'AR-PACKAGES') is None)
                                          else None})
            els = child(p, 'ELEMENTS')
            if els is not None:
                for el in els:
                    if localname(el.tag) in PILLARS:
                        emit_pillar(el)
    report['path_tree'] = tree_lines

    # --- ECUC value tree (values files: module -> container -> sub) ----
    # For ECU Configuration / MCAL config files. Counts param/ref/sub per
    # container and recurses sub-containers up to a meaning-based depth.
    def short_def(elem):
        ref = text_of(elem, 'DEFINITION-REF')
        return ref.split('/')[-1] if ref else None

    def emit_container(cont, depth, acc, max_depth=2):
        npar = nref = 0
        subs = []
        for cc in cont:
            t = localname(cc.tag)
            if t == 'PARAMETER-VALUES':
                npar = len(list(cc))
            elif t == 'REFERENCE-VALUES':
                nref = len(list(cc))
            elif t == 'SUB-CONTAINERS':
                subs = [x for x in cc
                        if localname(x.tag) == 'ECUC-CONTAINER-VALUE']
        acc.append({'depth': depth, 'name': short_name(cont),
                    'def': short_def(cont), 'param': npar,
                    'ref': nref, 'sub': len(subs)})
        if depth < max_depth:
            for s in subs:
                emit_container(s, depth + 1, acc, max_depth)

    ecuc_tree = []
    for e in all_elems:
        if localname(e.tag) != 'ECUC-MODULE-CONFIGURATION-VALUES':
            continue
        ecuc_tree.append({'depth': 0, 'name': short_name(e),
                          'def': short_def(e),
                          'variant': text_of(e, 'IMPLEMENTATION-CONFIG-VARIANT'),
                          'module': True})
        cont_holder = child(e, 'CONTAINERS')
        if cont_holder is not None:
            for cont in children(cont_holder, 'ECUC-CONTAINER-VALUE'):
                emit_container(cont, 1, ecuc_tree)
    report['ecuc_tree'] = ecuc_tree

    # --- Outgoing references (basis for block-2 INPUT, NO guessing) ----
    # Group every external reference this file makes, by reference kind and
    # by the root package it points to. This is the factual basis for the
    # "what this file depends on / points to" diagram.
    def root_pkg(p):
        parts = [x for x in p.split('/') if x]
        return parts[0] if parts else p

    ref_kinds = ['DEFINITION-REF', 'MODULE-DESCRIPTION-REF', 'VALUE-REF',
                 'FIBEX-ELEMENT-REF', 'TYPE-TREF']
    outgoing = {}
    for kind in ref_kinds:
        targets = [e.text.strip() for e in all_elems
                   if localname(e.tag) == kind and e.text]
        if not targets:
            continue
        by_root = Counter(root_pkg(t) for t in targets)
        outgoing[kind] = {'total': len(targets),
                          'by_root_package': dict(by_root.most_common()),
                          'examples': targets[:3]}
    report['outgoing_refs'] = outgoing

    # --- ECUC DEFINITION tree (.epd: module-def -> container-def) -------
    # For parameter-definition files. Mirrors ecuc_tree but for *-DEF.
    PARAM_DEFS = {'ECUC-INTEGER-PARAM-DEF', 'ECUC-BOOLEAN-PARAM-DEF',
                  'ECUC-ENUMERATION-PARAM-DEF', 'ECUC-FLOAT-PARAM-DEF',
                  'ECUC-STRING-PARAM-DEF', 'ECUC-FUNCTION-NAME-DEF'}
    REF_DEFS = {'ECUC-REFERENCE-DEF', 'ECUC-SYMBOLIC-NAME-REFERENCE-DEF',
                'ECUC-CHOICE-REFERENCE-DEF', 'ECUC-FOREIGN-REFERENCE-DEF'}

    def def_counts(cont):
        npar = nref = nsub = 0
        for c in cont:
            t = localname(c.tag)
            if t == 'PARAMETERS':
                npar = sum(1 for x in c if localname(x.tag) in PARAM_DEFS)
            elif t == 'REFERENCES':
                nref = len(list(c))
            elif t == 'SUB-CONTAINERS':
                nsub = sum(1 for x in c if 'CONTAINER-DEF' in localname(x.tag))
        return npar, nref, nsub

    def emit_def_container(cont, depth, acc, max_depth=2):
        npar, nref, nsub = def_counts(cont)
        acc.append({'depth': depth, 'name': short_name(cont),
                    'param': npar, 'ref': nref, 'sub': nsub})
        if depth < max_depth:
            for c in cont:
                if localname(c.tag) == 'SUB-CONTAINERS':
                    for s in c:
                        if 'CONTAINER-DEF' in localname(s.tag):
                            emit_def_container(s, depth + 1, acc, max_depth)

    def_tree = []
    module_def = None
    for e in all_elems:
        if localname(e.tag) == 'ECUC-MODULE-DEF':
            module_def = {
                'name': short_name(e),
                'refines': text_of(e, 'REFINED-MODULE-DEF-REF'),
                'post_build': text_of(e, 'POST-BUILD-VARIANT-SUPPORT'),
                'variants': [c.text.strip() for c in e.iter()
                             if localname(c.tag) == 'SUPPORTED-CONFIG-VARIANT'
                             and c.text],
            }
            def_tree.append({'depth': 0, 'name': short_name(e), 'module': True})
            ch = child(e, 'CONTAINERS')
            if ch is not None:
                for cont in ch:
                    if 'CONTAINER-DEF' in localname(cont.tag):
                        emit_def_container(cont, 1, def_tree)
            break
    if module_def:
        report['ecuc_def_module'] = module_def
        report['ecuc_def_tree'] = def_tree
        type_dist = Counter(localname(e.tag) for e in all_elems
                            if localname(e.tag) in PARAM_DEFS | REF_DEFS)
        report['ecuc_def_param_types'] = dict(type_dist.most_common())

    return report


def render(report):
    L = []
    f = report['file']
    L.append("=" * 60)
    L.append("ARXML STRUCTURAL REPORT")
    L.append("=" * 60)
    L.append(f"root        : {f['root_tag']}")
    L.append(f"schema      : {f.get('schemaLocation') or f.get('xmlns')}")
    if report['systems']:
        for s in report['systems']:
            L.append(f"system      : {s['name']}  (CATEGORY={s['category']})")
    if report['provenance']:
        L.append("provenance  :")
        for o in report['provenance']:
            L.append(f"              - {o}")

    L.append("\n-- PACKAGE TREE --------------------------------------------")
    for p in report['package_tree']:
        indent = "  " * p['depth']
        tag = " [EMPTY]" if p['empty'] else f" (elements={p['elements']}, subpkgs={p['subpackages']})"
        L.append(f"{indent}- {p['name']}{tag}")
    if report['empty_packages']:
        L.append(f"   empty packages: {', '.join(report['empty_packages'])}")

    if report['element_counts']:
        L.append("\n-- ELEMENT COUNTS ------------------------------------------")
        for t, c in sorted(report['element_counts'].items(), key=lambda x: -x[1]):
            L.append(f"   {t:<42} {c}")

    if report['fibex_refs']:
        L.append("\n-- FIBEX REFERENCE TARGETS (referenced, not defined here) --")
        for dest, c in report['fibex_refs'].items():
            L.append(f"   {dest:<32} {c}")

    if report['comm_direction']:
        L.append("\n-- COMMUNICATION DIRECTION ---------------------------------")
        for d, c in report['comm_direction'].items():
            L.append(f"   {d:<6} {c}")

    if report['pnc']['identifiers']:
        L.append("\n-- PARTIAL NETWORKING (PNC) --------------------------------")
        L.append(f"   identifiers   : {', '.join(report['pnc']['identifiers'])}")
        L.append(f"   vector length : {report['pnc']['vector_length']}")
        L.append(f"   vector offset : {report['pnc']['vector_offset']}")

    for ecu in report['ecu_instances']:
        L.append(f"\n-- ECU-INSTANCE: {ecu['name']} ----------------------------")
        for ctrl in ecu['controllers']:
            L.append(f"   controller : {ctrl['type']} -> {ctrl['name']}")
        L.append(f"   comm ports : {ecu['comm_ports']}")

    for comp in report['compositions']:
        L.append(f"\n-- COMPOSITION: {comp['name']} ----------------------------")
        L.append(f"   prototypes            : {comp['prototype_count']}")
        L.append(f"   assembly connectors   : {comp['assembly_connectors']}")
        L.append(f"   delegation connectors : {comp['delegation_connectors']}")
        if comp['by_kind']:
            L.append("   by kind:")
            for k, c in sorted(comp['by_kind'].items(), key=lambda x: -x[1]):
                L.append(f"      {str(k):<46} {c}")
    if report.get('path_tree'):
        L.append("\n-- PATH TREE (meaning-based, ~3 depth) ---------------------")
        for t in report['path_tree']:
            indent = "   " * t['depth']
            label = f"[{t['tag']}] {t['name']}" if t['name'] else t['tag']
            extra = ""
            if t['summary'] == 'EMPTY':
                extra = "  (EMPTY)"
            elif t['summary']:
                extra = f"  -> {t['summary']}"
            L.append(f"{indent}{label}{extra}")

    if report.get('specific_tags'):
        L.append("\n-- FILE-SPECIFIC TAGS (common tags excluded) ---------------")
        for t, c in report['specific_tags']:
            L.append(f"   {t:<42} {c}")

    if report.get('ecuc_tree'):
        L.append("\n-- ECUC VALUE TREE (module -> container -> sub) -----------")
        for t in report['ecuc_tree']:
            indent = "   " * t['depth']
            if t.get('module'):
                L.append(f"[ECUC-MODULE: {t['name']}]  variant={t.get('variant')}")
            else:
                meta = []
                if t['param']:
                    meta.append(f"param x{t['param']}")
                if t['ref']:
                    meta.append(f"ref x{t['ref']}")
                if t['sub']:
                    meta.append(f"sub x{t['sub']}")
                ms = ("  " + ", ".join(meta)) if meta else ""
                L.append(f"{indent}[{t['name']}] ({t['def']}){ms}")

    if report.get('outgoing_refs'):
        L.append("\n-- OUTGOING REFERENCES (factual INPUT basis, no guessing) --")
        for kind, info in report['outgoing_refs'].items():
            L.append(f"   {kind}  (total {info['total']})")
            for root, c in info['by_root_package'].items():
                L.append(f"      -> {root}  x{c}")

    if report.get('ecuc_def_module'):
        m = report['ecuc_def_module']
        L.append("\n-- ECUC DEFINITION (.epd: parameter schema) ----------------")
        L.append(f"   module   : {m['name']}")
        L.append(f"   refines  : {m['refines']}")
        L.append(f"   variants : {', '.join(m['variants'])}")
        L.append("   container-def tree (container = struct, param = member):")
        for t in report.get('ecuc_def_tree', []):
            if t.get('module'):
                continue
            indent = "      " + "   " * (t['depth'] - 1)
            meta = []
            if t['param']:
                meta.append(f"member x{t['param']}")
            if t['ref']:
                meta.append(f"ref x{t['ref']}")
            if t['sub']:
                meta.append(f"sub x{t['sub']}")
            ms = ("  " + ", ".join(meta)) if meta else ""
            L.append(f"{indent}[{t['name']}]{ms}")
        if report.get('ecuc_def_param_types'):
            L.append("   member types:")
            for t, c in report['ecuc_def_param_types'].items():
                L.append(f"      {t:<38} {c}")

    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('path')
    ap.add_argument('--json', action='store_true', help='emit JSON')
    args = ap.parse_args()
    try:
        report = inspect(args.path)
    except ET.ParseError as e:
        sys.exit(f"XML parse error: {e}")
    except FileNotFoundError:
        sys.exit(f"File not found: {args.path}")
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(render(report))


if __name__ == '__main__':
    main()
