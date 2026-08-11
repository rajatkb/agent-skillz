#!/usr/bin/env python3
"""Inspect an RTSS OverlayEditor .ovl file without RTSS: dump master settings,
sources grouped by provider, layer structure, and table cell bindings.

Usage: python3 inspect_ovl.py path/to/file.ovl [--layers]
"""
import re
import sys

def parse_sections(text):
    """Return list of (section_name, body) in file order."""
    return [(m.group(1), m.group(2))
            for m in re.finditer(r'\[([^\]]+)\]([^\[]*)', text, re.S)]

def get(text, key, default=''):
    m = re.search(r'^%s=(.*)$' % re.escape(key), text, re.M)
    return m.group(1) if m else default

def main():
    path = sys.argv[1]
    show_layers = '--layers' in sys.argv
    text = open(path, encoding='latin-1').read()

    master = re.search(r'\[Master\](.*?)(?=\[|\Z)', text, re.S)
    if master:
        print('MASTER: Font=%s Zoom=%s' % (
            get(master.group(1), 'FontFace'), get(master.group(1), 'ZoomRatio')))
    general = re.search(r'\[General\](.*?)(?=\[|\Z)', text, re.S)
    if general:
        g = general.group(1)
        print('GENERAL: %s sources / %s layers / %s tables' % (
            get(g, 'Sources'), get(g, 'Layers'), get(g, 'Tables')))

    # Sources
    sources = {}
    for name, body in parse_sections(text):
        if re.fullmatch(r'Source\d+', name):
            sources[int(name[6:])] = {
                'name': get(body, 'Name'),
                'provider': get(body, 'Provider'),
                'units': get(body, 'Units'),
            }
    by_provider = {}
    for s in sources.values():
        by_provider.setdefault(s['provider'], []).append(s['name'])
    print('\nSOURCES: %d total' % len(sources))
    for prov, names in sorted(by_provider.items()):
        print('  %-12s (%d):' % (prov, len(names)))
        print('    ' + ', '.join(sorted(set(names))))

    # Layer bindings
    vis = set(re.findall(r'VisibilitySource=([^\r\n]+)', text))
    graphs = set()
    for g in re.findall(r'<G=([^,>]+)', text):
        graphs.add(g.strip())
    tables_used = set(re.findall(r'<TT=([^>]+)>', text))

    # Table cell bindings
    table_cells = {}
    for name, body in parse_sections(text):
        if re.fullmatch(r'Table\d+', name):
            cells = [get(body, k) for k in re.findall(r'^Line\d+Cell\d+Source=([^\r\n]+)', body, re.M)]
            cells = [c for c in cells if c]
            if cells:
                table_cells[name] = cells

    print('\nLAYER BINDINGS:')
    print('  visibility sources:', sorted(vis) or '-')
    print('  graph/bar sources (<G=>):', sorted(graphs) or '-')
    print('  tables referenced (<TT=>):', sorted(tables_used) or '-')
    for tname, cells in table_cells.items():
        print('  %s cells: %s' % (tname, ', '.join(cells)))

    if show_layers:
        print('\nLAYER SECTIONS:')
        for name, body in parse_sections(text):
            if re.fullmatch(r'Layer\d+', name):
                lname = get(body, 'Name')
                txt = get(body, 'Text').replace('\r', '\\r')[:120]
                print('  %s %-40s %s' % (name, lname, txt))

if __name__ == '__main__':
    main()
