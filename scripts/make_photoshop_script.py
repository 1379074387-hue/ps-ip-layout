#!/usr/bin/env python3
"""Generate a bounded Photoshop ExtendScript from an explicit JSON manifest (stdlib only)."""
import argparse
import json
from pathlib import Path

RUNTIME = r'''
#target photoshop
(function () {
  var config = CONFIG;
  var oldDialogs = app.displayDialogs;
  var oldUnits = app.preferences.rulerUnits;
  var log = new File(config.log); log.encoding = 'UTF8';
  if (!log.open('w')) throw new Error('Cannot write log: ' + config.log);
  app.displayDialogs = DialogModes.NO;
  app.preferences.rulerUnits = Units.PIXELS;
  function px(v) { return UnitValue(v, 'px'); }
  function bounds(l) {
    var b = l.bounds;
    return [b[0].as('px'), b[1].as('px'), b[2].as('px'), b[3].as('px')];
  }
  function parentDir(path) {
    var folder = new File(path).parent;
    function make(f) { if (!f.exists) { make(f.parent); if (!f.create()) throw new Error('Cannot create ' + f.fsName); } }
    make(folder);
  }
  function allLayers(c, out, path) {
    for (var i = 0; i < c.layers.length; i++) {
      var l = c.layers[i], p = path ? path + '/' + l.name : l.name;
      if (l.typename === 'LayerSet') allLayers(l, out, p);
      else out.push({layer:l, path:p});
    }
  }
  function one(doc, name) {
    var a = []; allLayers(doc, a, ''); var found = [];
    for (var i=0; i<a.length; i++) if (a[i].layer.name === name) found.push(a[i].layer);
    if (found.length !== 1) throw new Error('Expected one layer named ' + name + ', found ' + found.length);
    return found[0];
  }
  function revealSelection(doc) {
    var d = new ActionDescriptor();
    d.putClass(charIDToTypeID('Nw  '), charIDToTypeID('Chnl'));
    var r = new ActionReference();
    r.putEnumerated(charIDToTypeID('Chnl'), charIDToTypeID('Chnl'), charIDToTypeID('Msk '));
    d.putReference(charIDToTypeID('At  '), r);
    d.putEnumerated(charIDToTypeID('Usng'), charIDToTypeID('UsrM'), charIDToTypeID('RvlS'));
    executeAction(charIDToTypeID('Mk  '), d, DialogModes.NO);
    doc.selection.deselect();
  }
  function subject(doc) {
    if (doc.activeLayer.isBackgroundLayer) doc.activeLayer.isBackgroundLayer = false;
    var d = new ActionDescriptor(); d.putBoolean(stringIDToTypeID('sampleAllLayers'), false);
    executeAction(stringIDToTypeID('autoCutout'), d, DialogModes.NO);
    var b = doc.selection.bounds;
    if (b[2].as('px') <= b[0].as('px') || b[3].as('px') <= b[1].as('px')) throw new Error('Empty subject selection');
    revealSelection(doc);
    doc.activeLayer.name += ' [Photoshop subject mask]';
  }
  function embed(doc, jobs) {
    for (var i=0; i<jobs.length; i++) {
      var j=jobs[i], l=one(doc,j.name), ob=bounds(l);
      doc.activeLayer=l;
      var d=new ActionDescriptor(); d.putPath(charIDToTypeID('null'),new File(j.file));
      executeAction(stringIDToTypeID('placeEvent'),d,DialogModes.NO);
      var n=doc.activeLayer,b=bounds(n),w=b[2]-b[0],h=b[3]-b[1];
      if (j.subject) {
        var scale=Math.min((ob[2]-ob[0])/w,(ob[3]-ob[1])/h);
        n.resize(scale*100,scale*100,AnchorPosition.TOPLEFT);
        b=bounds(n); n.translate(px((ob[0]+ob[2]-b[2]-b[0])/2),px((ob[1]+ob[3]-b[3]-b[1])/2));
      } else {
        var f=j.frame || [ob[0],ob[1],ob[2]-ob[0],ob[3]-ob[1]];
        var scale=j.fit==='contain'?Math.min(f[2]/w,f[3]/h):Math.max(f[2]/w,f[3]/h);
        n.resize(scale*100,scale*100,AnchorPosition.TOPLEFT); b=bounds(n);
        w=b[2]-b[0];h=b[3]-b[1];
        n.translate(px(f[0]+(f[2]-w)/2-b[0]),px(f[1]+(f[3]-h)/2-b[1]));
        doc.selection.select([[f[0],f[1]],[f[0]+f[2],f[1]],[f[0]+f[2],f[1]+f[3]],[f[0],f[1]+f[3]]],SelectionType.REPLACE,0,true);
        if (j.radius) doc.selection.smooth(j.radius);
        revealSelection(doc);
      }
      n.name=j.name; l.remove();
    }
  }
  function a3(doc, job) {
    var dpi=job.dpi||300, landscape=job.orientation==='landscape';
    var tw=Math.round((landscape?420:297)/25.4*dpi),th=Math.round((landscape?297:420)/25.4*dpi);
    var w=doc.width.as('px'),h=doc.height.as('px');
    if(w/h>tw/th) doc.resizeImage(px(tw),null,dpi,ResampleMethod.BICUBICSMOOTHER);
    else doc.resizeImage(null,px(th),dpi,ResampleMethod.BICUBICSMOOTHER);
    doc.resizeCanvas(px(tw),px(th),AnchorPosition.MIDDLECENTER);
    if(job.paper_layer){
      var paper=one(doc,job.paper_layer),b=bounds(paper);
      paper.resize(tw/(b[2]-b[0])*100,th/(b[3]-b[1])*100,AnchorPosition.MIDDLECENTER);
      b=bounds(paper);paper.translate(px(-b[0]),px(-b[1]));
    } else if(job.background){
      var layer=doc.artLayers.add();layer.name='A3 extension background';
      var color=new SolidColor();color.rgb.hexValue=job.background.replace('#','');
      doc.selection.selectAll();doc.selection.fill(color);doc.selection.deselect();
      var bottom=doc.layers[doc.layers.length-1];
      if(bottom!==layer){if(bottom.typename==='ArtLayer'&&bottom.isBackgroundLayer)bottom.isBackgroundLayer=false;layer.move(bottom,ElementPlacement.PLACEAFTER);}
    }
  }
  function enlarge(doc, changes) {
    var list=[];allLayers(doc,list,'');var matched=[];
    for(var k=0;k<changes.length;k++)matched[k]=0;
    for(var i=0;i<list.length;i++){
      var l=list[i].layer;if(l.kind!==LayerKind.TEXT)continue;
      var hit=-1;
      for(var k=0;k<changes.length;k++){
        var c=changes[k];
        if(c.name===l.name&&(!c.path||c.path===list[i].path)&&
          (c.text===undefined||c.text===l.textItem.contents)){
          if(hit!==-1)throw new Error('Overlapping change rules for '+list[i].path);
          hit=k;
        }
      }
      if(hit<0)continue;var c=changes[hit];matched[hit]++;
      var anchor=AnchorPosition.TOPLEFT;
      if(l.textItem.justification===Justification.CENTER)anchor=AnchorPosition.TOPCENTER;
      else if(l.textItem.justification===Justification.RIGHT)anchor=AnchorPosition.TOPRIGHT;
      l.resize(c.factor*100,c.factor*100,anchor);
      if(c.move)l.translate(px(c.move[0]),px(c.move[1]));
    }
    for(var k=0;k<changes.length;k++){
      if(!matched[k])throw new Error('Unmatched change: '+changes[k].name);
      if(matched[k]>1&&!changes[k].all_matches)throw new Error('Ambiguous change: '+changes[k].name+'; specify text/path or all_matches');
    }
  }
  try {
    for(var i=0;i<config.jobs.length;i++){
      var job=config.jobs[i];
      try {
        if(new File(job.output).exists)throw new Error('Output already exists; choose a fresh filename: '+job.output);
        if(job.preview&&new File(job.preview).exists)throw new Error('Preview already exists: '+job.preview);
        var source=app.open(new File(job.input));
        var doc=source.duplicate(new File(job.output).name.replace(/\.psd$/i,''),false);
        if(job.crop)doc.crop([px(job.crop[0]),px(job.crop[1]),px(job.crop[2]),px(job.crop[3])]);
        if(job.mode==='cutout')subject(doc);
        else if(job.mode==='embed_images')embed(doc,job.replacements);
        else if(job.mode==='a3')a3(doc,job);
        else if(job.mode==='enlarge_text')enlarge(doc,job.changes);
        parentDir(job.output);var opts=new PhotoshopSaveOptions();opts.layers=true;opts.embedColorProfile=true;
        doc.saveAs(new File(job.output),opts,false,Extension.LOWERCASE);
        if(job.preview){parentDir(job.preview);var png=new PNGSaveOptions();png.compression=4;doc.saveAs(new File(job.preview),png,true,Extension.LOWERCASE);}
        log.writeln('SUCCESS '+job.output+' | '+doc.width.as('px')+'x'+doc.height.as('px')+' | '+doc.resolution+' dpi | Photoshop '+app.version);
      }catch(e){log.writeln('ERROR job '+i+' '+e+' line '+e.line);break;}
    }
  } finally {
    app.preferences.rulerUnits=oldUnits;app.displayDialogs=oldDialogs;log.close();
  }
  // Leave the final document open; never close the user's existing documents.
})();
'''


def validate(config):
    if not isinstance(config.get('jobs'), list) or not config['jobs']:
        raise ValueError('jobs must be a nonempty array')
    used = set()
    for job in config['jobs']:
        if job.get('mode') not in {'cutout', 'embed_images', 'a3', 'enlarge_text', 'save'}:
            raise ValueError('Unsupported mode')
        for key in ('input', 'output'):
            path = Path(job[key]).expanduser()
            if not path.is_absolute():
                raise ValueError(f'{key} must be absolute: {path}')
            job[key] = str(path)
        if not Path(job['input']).is_file():
            raise ValueError(f"Input missing: {job['input']}")
        if Path(job['output']).suffix.lower() != '.psd':
            raise ValueError('Output must end in .psd')
        if Path(job['input']).resolve() == Path(job['output']).resolve():
            raise ValueError('Use a separate output; originals are preserved')
        for path in [job['output']] + ([job['preview']] if job.get('preview') else []):
            if not Path(path).is_absolute() or Path(path).exists() or str(Path(path).resolve()) in used:
                raise ValueError(f'Choose a fresh absolute output: {path}')
            used.add(str(Path(path).resolve()))
        if job.get('preview') and Path(job['preview']).suffix.lower() != '.png':
            raise ValueError('Preview must end in .png')
        if job['mode'] == 'a3':
            if job.get('orientation', 'portrait') not in {'portrait', 'landscape'}:
                raise ValueError('Invalid A3 orientation')
            if not 72 <= job.get('dpi', 300) <= 1200:
                raise ValueError('dpi must be 72..1200')
            if job.get('background'):
                color = job['background'].lstrip('#')
                if len(color) != 6 or any(c not in '0123456789abcdefABCDEF' for c in color):
                    raise ValueError('background must be #RRGGBB')
        for item in job.get('changes', []):
            if not item.get('name') or not 0 < item.get('factor', 0) <= 4:
                raise ValueError('Text changes require name and factor in (0, 4]')
        if job['mode'] == 'enlarge_text' and not job.get('changes'):
            raise ValueError('enlarge_text requires explicit changes')
        if job['mode'] == 'embed_images' and not job.get('replacements'):
            raise ValueError('embed_images requires replacements')
        for item in job.get('replacements', []):
            if not item.get('name') or not Path(item['file']).is_absolute() or not Path(item['file']).is_file():
                raise ValueError('Each replacement needs name and existing absolute file')
            if item.get('fit', 'cover') not in {'cover', 'contain'}:
                raise ValueError('fit must be cover or contain')
            if item.get('frame') and (len(item['frame']) != 4 or min(item['frame'][2:]) <= 0):
                raise ValueError('frame is [left, top, positive width, positive height]')
        if job.get('crop'):
            b = job['crop']
            if len(b) != 4 or b[2] <= b[0] or b[3] <= b[1]:
                raise ValueError('crop is [left, top, right, bottom]')
    if not Path(config['log']).is_absolute() or Path(config['log']).exists():
        raise ValueError('log must be a fresh absolute path')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    config = json.loads(args.manifest.read_text(encoding='utf-8'))
    config.setdefault('log', str(args.out.resolve().with_suffix('.log')))
    validate(config)
    # ExtendScript string literals cannot contain raw Unicode line separators.
    serialized = json.dumps(config, ensure_ascii=False).replace('\u2028', r'\u2028').replace('\u2029', r'\u2029')
    args.out.parent.mkdir(parents=True, exist_ok=True)
    Path(config['log']).parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(RUNTIME.replace('CONFIG', serialized, 1), encoding='utf-8')
    print(f'Generated {args.out.resolve()} ({len(config["jobs"])} jobs). Execute inside Photoshop and read {config["log"]}')


if __name__ == '__main__':
    main()
