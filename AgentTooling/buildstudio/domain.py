"""Compatibility over authored fixtures, not a hardware safety certification."""
import hashlib,json,math
from pathlib import Path
CATALOG=json.loads((Path(__file__).parent/'catalog.json').read_text())
CANON=lambda x:json.dumps(x,sort_keys=True,separators=(',',':'))
HASH=lambda x:hashlib.sha256(CANON(x).encode()).hexdigest()
class Invalid(ValueError):pass

def search(query):
    if not isinstance(query,str) or len(query)>200:raise Invalid('invalid search query')
    terms=query.lower().split()
    return dict(catalog_version=CATALOG['version'],scope=CATALOG['scope'],board=CATALOG['board'],modules=[m for m in CATALOG['modules'] if not terms or any(t in (m['id']+' '+m['capability']).lower() for t in terms)])

def recipe(modules):
    """Fixture helper; derives wiring from catalog, never a real model prediction."""
    by_id={m['id']:m for m in CATALOG['modules']}
    return dict(board='demo-mcu',modules=modules,enclosure=dict(width_mm=100,depth_mm=70,height_mm=30),
      wires=[dict(source='demo-mcu.'+pin,target=identifier+'.'+port) for identifier in modules for port,pin in by_id[identifier]['wiring'].items()])

def validate(plan):
    if not isinstance(plan,dict) or set(plan)!={'board','modules','enclosure','wires'}:raise Invalid('invalid build fields')
    if plan['board']!=CATALOG['board']['id']:raise Invalid('unsupported board')
    ids=plan['modules'];by_id={m['id']:m for m in CATALOG['modules']}
    if not isinstance(ids,list) or not 1<=len(ids)<=4 or any(not isinstance(i,str) or i not in by_id for i in ids):raise Invalid('unsupported modules')
    if len(set(ids))!=len(ids):raise Invalid('duplicate module')
    modules=[by_id[i] for i in ids];board=CATALOG['board']
    if any(m['voltage_mv']!=board['voltage_mv'] for m in modules):raise Invalid('fixture voltage mismatch')
    if sum(m['current_ma'] for m in modules)>board['budget_ma']:raise Invalid('fixture current budget exceeded')
    addresses=[m['address'] for m in modules if m['bus']=='i2c']
    if len(set(addresses))!=len(addresses):raise Invalid('fixture I2C address conflict')
    shape=plan['enclosure']
    if not isinstance(shape,dict) or set(shape)!={'width_mm','depth_mm','height_mm'}:raise Invalid('invalid enclosure dimensions')
    for k,v in shape.items():
        if type(v) not in (int,float) or not math.isfinite(v) or not 10<=v<=250:raise Invalid('dimension must be finite millimeters in range 10-250')
    # A fixed, non-overlapping left-to-right arrangement with 3mm edge clearance.
    parts=[board,*modules];width=sum(m['dimensions_mm'][0] for m in parts)+3*(len(parts)+1)
    depth=max(m['dimensions_mm'][1] for m in parts)+6;height=max(m['dimensions_mm'][2] for m in parts)+6
    if any(shape[k]<v for k,v in zip(('width_mm','depth_mm','height_mm'),(width,depth,height))):raise Invalid('enclosure too small for fixture layout')
    actual=plan['wires']
    if not isinstance(actual,list) or any(not isinstance(w,dict) or set(w)!={'source','target'} or not all(isinstance(v,str) for v in w.values()) for w in actual):raise Invalid('invalid wire fields')
    expected=recipe(ids)['wires']
    if sorted(map(CANON,actual))!=sorted(map(CANON,expected)):raise Invalid('wiring must exactly match catalog fixture rules')
    result=dict(plan=plan,catalog_version=CATALOG['version'],catalog_hash=HASH(CATALOG),scope=CATALOG['scope'],
       layout_bounds_mm=[width,depth,height],assembly=[f"Connect {w['source']} to {w['target']}." for w in expected],
       geometry=dict(kind='enclosure-source-only',dimensions_mm=shape,clearance_mm=3))
    result['validation_hash']=HASH(result)
    return result

def scad(validated):
    d=validated['plan']['enclosure'];w,h,z=(d[k] for k in ('width_mm','depth_mm','height_mm'))
    return f'// Fixture enclosure source only: no CAD renderer or physical test executed.\n// validation {validated["validation_hash"]}\ndifference() {{\n  cube([{w}, {h}, {z}]);\n  translate([2, 2, 2]) cube([{w-4}, {h-4}, {z}]);\n}}\n'
