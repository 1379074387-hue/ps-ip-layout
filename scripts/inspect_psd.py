#!/usr/bin/env python3
"""Read PSD structure, typography and optional comparison; no source files are modified."""
import argparse
import io
import json
from pathlib import Path

try:
    from psd_tools import PSDImage
except ImportError:
    raise SystemExit('psd-tools is required. Use an existing Python environment with psd-tools; do not silently install it.')


def overlap(a, b):
    return max(0, min(a[2], b[2])-max(a[0], b[0])) * max(0, min(a[3], b[3])-max(a[1], b[1]))


def inspect(path, embedded=False, compare=None):
    psd = PSDImage.open(path)
    layers = list(psd.descendants())
    res = psd.image_resources.get_data(1005)
    result = dict(file=str(path), size=list(psd.size), dpi=None,
                  content_layers=sum(not x.is_group() for x in layers),
                  text_layers=sum(x.kind == 'type' for x in layers),
                  smart_objects=sum(x.kind == 'smartobject' for x in layers),
                  root_groups=[x.name for x in psd if x.is_group()], layers=[])
    if res:
        result['dpi'] = [res.horizontal/65536, res.vertical/65536]
    for i, layer in enumerate(layers):
        row = dict(index=i, name=layer.name, kind=layer.kind, bbox=list(layer.bbox),
                   visible=layer.is_visible(), mask=layer.has_mask())
        if layer.kind == 'type':
            row['text'] = layer.text
        if embedded and layer.kind == 'smartobject':
            try:
                inner = PSDImage.open(io.BytesIO(layer.smart_object.data))
                row['embedded_psd_masks'] = sum(x.has_mask() for x in inner.descendants())
            except Exception as exc:
                row['embedded_inspection'] = 'Not readable as an embedded PSD: ' + str(exc)[:120]
        result['layers'].append(row)
    if compare:
        old = list(PSDImage.open(compare).descendants())
        same_structure = [(x.name, x.kind) for x in old] == [(x.name, x.kind) for x in layers]
        report = dict(source=str(compare), same_structure=same_structure)
        if same_structure:
            text_pairs = [(a,b) for a,b in zip(old,layers) if a.kind=='type']
            report['same_text_contents'] = all(a.text==b.text for a,b in text_pairs)
            report['changed_text_layers'] = sum(a.bbox!=b.bbox or a.transform!=b.transform for a,b in text_pairs)
            report['nontext_bounds_changed'] = [b.name for a,b in zip(old,layers)
                                                if not a.is_group() and a.kind!='type' and a.bbox!=b.bbox]
            report['new_text_overlaps'] = []
            for i,(a0,a1) in enumerate(text_pairs):
                for b0,b1 in text_pairs[i+1:]:
                    if a1.is_visible() and b1.is_visible() and not overlap(a0.bbox,b0.bbox) and overlap(a1.bbox,b1.bbox)>4:
                        report['new_text_overlaps'].append(dict(a=a1.name,a_text=a1.text,b=b1.name,b_text=b1.text))
        result['comparison'] = report
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('psd', type=Path)
    parser.add_argument('--compare', type=Path)
    parser.add_argument('--embedded-masks', action='store_true')
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    output = json.dumps(inspect(args.psd, args.embedded_masks, args.compare), ensure_ascii=False, indent=2)
    if args.out:
        args.out.write_text(output, encoding='utf-8')
        print(args.out.resolve())
    else:
        print(output)


if __name__ == '__main__':
    main()
