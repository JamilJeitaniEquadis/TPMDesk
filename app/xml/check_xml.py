import xml.etree.ElementTree as ET, glob, datetime, os, sys, collections
U={'Gramme (g)':0.001,'Kilogramme (kg)':1,'Milligramme (mg)':1e-6}
d=lambda s: datetime.datetime.strptime(s,'%d/%m/%Y')
D=sys.argv[1]; tot=collections.Counter()
for f in sorted(glob.glob(D+'/*.xml')):
    ps=ET.parse(f).getroot().findall('product'); e=collections.Counter(); bad=collections.defaultdict(list)
    for p in ps:
        v=lambda i:([x.findtext('value') for x in p.iter('field') if x.get('id')==i] or [None])[0]
        g=v('2'); errs=[]
        if v('1225') and not v('2107'): errs.append('RG_626')
        if v('2234') and v('2231') and d(v('2234'))>d(v('2231')): errs.append('RG_421')
        if p.find(".//field[@id='604']") is None: errs.append('REQ_603')
        if not v('1025'): errs.append('REQ_1025')
        if 'CXC' in str(v('185_1')) and not v('185_3'): errs.append('RG_909')
        if len({x.get('gln') for x in ps})>1: errs.append('GLN multiples')
        for i,lg in enumerate(p.iter('log')):
            if lg.find('.//pack') is None: errs.append('log sans pack')
        for i,pk in enumerate(p.iter('pack')):
            w=lambda k:([x.findtext('value') for x in pk.findall('field') if x.get('id')==k] or [None])[0]
            if i==0 and v('2234') and w('PK71') and d(v('2234'))>d(w('PK71')): errs.append('RG_180')
            if i==0 and v('2231') and w('PK72') and d(v('2231'))>d(w('PK72')): errs.append('RG_183')
            if not w('PK71'): errs.append('REQ_PK71')
            if not w('PK32'): errs.append('REQ_PK32')
            for k in ('PK50','PK53'):
                if w(k) and float(w(k))==0: errs.append('DAZ_'+k)
            n=w('PK17') or w('PK10'); G,N=w('PK28'),w('PK30'); un=float(v('158'))*U.get(v('159'),0) if v('158') else None
            if G and N and float(G)<float(N): errs.append('RG_627')
            if n and N and un and float(N)+1e-9<float(n)*un: errs.append('RG_138')
        for x in set(errs): e[x]+=1; bad[x].append(g)
    tot.update(e)
    print(f"{os.path.basename(f).split('_')[-2] if False else os.path.basename(f)[41:-4]:50} {len(ps):4}  {dict(e) if e else 'OK'}")
    for k,gs in bad.items():
        if k in ('REQ_1025','REQ_PK32','RG_627','RG_138','REQ_603'): print('       ',k,', '.join(gs[:12]))
