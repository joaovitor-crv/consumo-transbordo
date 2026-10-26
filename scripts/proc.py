import os
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'load.py')).read())
import json
# período: argumentos 2 e 3 (AAAA-MM-DD); sem eles, do 1º dia do abastecimento ao último dia comum às três bases
D0=pd.Timestamp(sys.argv[2]) if len(sys.argv)>2 else pd.to_datetime(ab.data).min().normalize()
DF=pd.Timestamp(sys.argv[3]) if len(sys.argv)>3 else min(pd.to_datetime(ab.data).max(),pd.to_datetime(bal.data).max(),m.t.max()).normalize()
D1=DF+pd.Timedelta(hours=23,minutes=59,seconds=59)
GAP=300; DESC=90; META=1.0; META_OC=0.10
def turno(h): return 'A' if 7<=h<15 else ('B' if 15<=h<23 else 'C')
ab['data']=pd.to_datetime(ab.data); bal['data']=pd.to_datetime(bal.data); AMAX,BMAX=ab.data.max(),bal.data.max()
ab=ab[(ab.data>=D0)&(ab.data<=D1)]; bal=bal[(bal.data>=D0)&(bal.data<=D1)]
m0max=m.t.max(); m=m[(m.t>=D0)&(m.t<=D1)].copy()
g0=m.groupby('Equipamento').Grupo.agg(lambda s:s.mode().iloc[0])
lg0=((m['Motor Ligado']=='Sim')&(m['RPM Motor']!=850)).groupby(m.Equipamento).sum()
KEEP=set(g0[~g0.str.contains('MANUT')&(lg0.reindex(g0.index)>0)].index)
EXC_M=sorted(set(g0.index)-KEEP); EXC_A=sorted(set(ab.frota)-KEEP); EXC_B=sorted(set(bal.frota)-KEEP)
ab0,bal0=ab.copy(),bal.copy(); ab=ab[ab.frota.isin(KEEP)]; bal=bal[bal.frota.isin(KEEP)]; m=m[m.Equipamento.isin(KEEP)].copy()
m['gap']=(m.groupby('Equipamento').t.shift(-1)-m.t).dt.total_seconds()
m['dt']=m.gap.fillna(60).clip(upper=GAP)
m['lig']=(m['Motor Ligado']=='Sim')&(m['RPM Motor']!=850); m['dia']=m.t.dt.strftime('%d/%m')
m['par']=(m.Estado=='PARADA')&m.lig
# paradas: sequências contínuas
m['blk']=((m.par!=m.groupby('Equipamento').par.shift()) | (m.Equipamento!=m.Equipamento.shift())).cumsum()
P=m[m.par].groupby('blk').agg(frota=('Equipamento','first'),ini=('t','first'),dur=('dt','sum'),op=('Operacao','first'),dia=('dia','first')).reset_index()
P['net']=(P.dur-DESC).clip(lower=0)/3600; P['turno']=P.ini.dt.hour.map(turno)
lig_f=(m.dt*m.lig).groupby(m.Equipamento).sum()/3600
lig_fd=(m.dt*m.lig).groupby([m.Equipamento,m.dia]).sum()/3600
oc_f=P.groupby('frota').net.sum(); par_f=P.groupby('frota').size()
grp=m.groupby('Equipamento').Grupo.agg(lambda s:s.mode().iloc[0])
# por frota
af=ab.groupby('frota').agg(litros=('litros','sum'),custo=('custo','sum'),hor=('hor',lambda s:s.max()-s.min()))
bf=bal.groupby('frota').agg(ton=('liq',lambda s:s.sum()/1000),viagens=('ticket','nunique'))
fr=sorted(set(af.index)|set(bf.index)|set(m.Equipamento))
rows=[]
for f in fr:
    tel=f in lig_f.index and lig_f[f]>0
    L=af.litros.get(f); T=bf.ton.get(f)
    rows.append(dict(frota=int(f),grupo=grp[f] if tel else 'SEM TELEMETRIA',litros=None if L is None else round(L,2),custo=None if L is None else float(af.custo[f]),
      horas=float(lig_f[f]) if tel else (float(af.hor[f]) if f in af.index and af.hor[f]>0 else None),
      ton=None if T is None else round(float(T),3),lt=float(L/T) if L and T else None,
      pct=float(oc_f.get(f,0)/lig_f[f]) if tel else None,paradas=int(par_f.get(f,0)) if tel else None,viagens=None if f not in bf.index else int(bf.viagens[f])))
R=pd.DataFrame(rows)
order=sorted(R.grupo.unique(),key=lambda g:(g=='SEM TELEMETRIA','MANUT' in g,g))
tabela=[dict(grupo=g,linhas=[{k:(None if (isinstance(v,float) and np.isnan(v)) else v) for k,v in r.items() if k!='grupo'} for r in R[R.grupo==g].to_dict('records')]) for g in order]
both=R[R['lt'].notna()]
dias=pd.date_range(D0,DF).strftime('%d/%m')
ab['dia']=ab.data.dt.strftime('%d/%m'); bal['dia']=bal.data.dt.strftime('%d/%m')
bset=set(both.frota)
ld=ab[ab.frota.isin(bset)].groupby('dia').litros.sum(); td=bal[bal.frota.isin(bset)].groupby('dia').liq.sum()/1000
tel=R[R.pct.notna()]; LIG=tel.horas.sum(); OC=P.net.sum()
# frota-dia
ocd=P.groupby(['frota','dia']).net.sum(); fd=pd.concat([lig_fd,ocd],axis=1,keys=['lig','oc']).fillna(0); fd.index.names=['frota','dia']; fd=fd[fd.lig>0.5]; fd['pct']=fd.oc/fd.lig
bins=[-1,.1,.2,.3,.4,.5,9]; labs=['Até 10%','10 a 20%','20 a 30%','30 a 40%','40 a 50%','Acima de 50%']
fx=pd.cut(fd.pct,bins,labels=labs).value_counts().reindex(labs)
top5=fd.sort_values('oc',ascending=False).head(5).reset_index()
odia=(P.groupby('dia').net.sum()/(m.dt*m.lig).groupby(m.dia).sum()*3600)
# RPM
r=m[m.lig&(m['RPM Motor']>0)]; rl=['1 - 900 (lenta)','901 - 1.500','1.501 - 1.800','1.801 - 2.000','Acima de 2.000']
rc=r.groupby(pd.cut(r['RPM Motor'],[0,900,1500,1800,2000,1e9],labels=rl),observed=False).dt.sum(); rc=rc/rc.sum()
mot=P.groupby(P.op.str.strip().str.title()).net.sum().sort_values(ascending=False)
sem_tel=R[R.grupo=='SEM TELEMETRIA']
D=dict(periodo=D0.strftime('%d/%m/%Y')+' - '+DF.strftime('%d/%m/%Y'),
 K=dict(litros=float(R.litros.sum()),custo=float(R.custo.sum()),frotas=int(len(R)),ton=float(R.ton.sum()),lt=float(both.litros.sum()/both.ton.sum()),meta=META,
   horas_oc=float(OC),horas_oc_bruto=float(P.dur.sum()/3600),paradas=int(len(P)),paradas_90=int((P.dur>DESC).sum()),pct_oc=float(OC/LIG)),
 tabela=tabela,oc_faixa=[dict(l=k,v=int(v)) for k,v in fx.items()],
 oc_top=[dict(l=str(k),v=float(v)) for k,v in oc_f.sort_values(ascending=False).head(10).items()],
 oc_tab=[dict(frota=int(x.frota),data=x.dia,lig=float(x.lig),oc=float(x.oc),pct=float(x.pct)) for x in top5.itertuples()],
 oc_dia=[dict(l=d,v=float(odia.get(d,0))) for d in dias],
 lt_dia=[dict(l=d,v=float(ld.get(d,0)/td[d])) for d in dias if td.get(d,0)>0],
 litros_dia=[dict(l=d,v=float(ab[ab.dia==d].litros.sum())) for d in dias],
 ton_dia=[dict(l=d,v=float(bal[bal.dia==d].liq.sum()/1000)) for d in dias],
 rpm=[dict(l=k,v=float(v)) for k,v in rc.items()],
 motivo=[dict(l=k,v=float(v)) for k,v in mot.items()],
 oc_turno=[dict(l=t,v=float(P[P.turno==t].net.sum())) for t in 'ABC'],meta_oc=META_OC)
abs_only=sorted(set(af.index)-set(bf.index)); bal_only=sorted(set(bf.index)-set(af.index))
D['notas']=[
 'Só entram os transbordos das frentes (com telemetria). Ficaram fora os de manutenção/reforma/parado ('+', '.join(map(str,EXC_M))+') e todos os sem telemetria; as frotas fora do painel somam '+f"{len(set(EXC_A)|set(EXC_B)|set(EXC_M))}"+' códigos entre abastecimento, balança e monit.',
 'Transbordos das frentes sem abastecimento ou sem pesagem no período: '+(', '.join(map(str,sorted(set(abs_only)|set(bal_only)))) or 'nenhum')+'.',
 'NOTA90',
 'Nas paradas dos transbordos o monit quase não traz motivo apontado: praticamente todo o tempo ocioso aparece como "Sem Apontamento".',
 'Período comum às três bases: '+D0.strftime('%d/%m')+' a '+DF.strftime('%d/%m')+' (abastecimento até '+AMAX.strftime('%d/%m')+', balança até '+BMAX.strftime('%d/%m')+', monit até '+m0max.strftime('%d/%m')+').']
lit_out=float(ab0.litros.sum()-ab.litros.sum()); ton_out=float(bal0.liq.sum()-bal.liq.sum())/1000
print('fora: litros',lit_out,'ton',ton_out)

print(json.dumps(D['K'],indent=1)); print(R.describe()); print(both['lt'].describe()); print(D['motivo'],D['rpm'],D['oc_faixa'])
for g in tabela: print(g['grupo'],len(g['linhas']))

# monta o painel
B=os.path.dirname(os.path.abspath(__file__))
br=lambda v,d: f'{v:,.{d}f}'.replace(',','X').replace('.',',').replace('X','.')
K=D['K']; D['notas'][2]=f"Motor ocioso descontando 90 s de cada parada: {br(K['paradas'],0)} paradas com motor ligado; {br(K['paradas']-K['paradas_90'],0)} duraram até 90 s e não contam. Sem o desconto seriam {br(K['horas_oc_bruto'],1)} h; com o desconto, {br(K['horas_oc'],1)} h."
open(os.path.join(B,'..','index.html'),'w').write(open(os.path.join(B,'template.html')).read().replace('__DADOS__',json.dumps(D,ensure_ascii=False)))
print('index.html atualizado')
