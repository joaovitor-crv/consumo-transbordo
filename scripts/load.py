import pandas as pd, numpy as np, datetime as DT
import sys, glob, os
IN=sys.argv[1] if len(sys.argv)>1 else 'entrada'
A=''
def abast(f):
    d=pd.read_excel(f,header=None); rows=[]; v=None
    for r in d.itertuples(index=False):
        if r[0]=='Veiculo :': v=int(r[1]); continue
        if v and isinstance(r[0],DT.datetime) and pd.notna(r[5]):
            rows.append(dict(frota=v,data=r[0],hor=float(str(r[2]).strip() or 'nan'),litros=float(r[5]),custo=float(r[6])))
    return pd.DataFrame(rows)
XL=sorted(glob.glob(os.path.join(IN,'*.xlsx')))
def kind(f): return str(pd.read_excel(f,header=None,nrows=3).values.ravel())
ab=pd.concat([abast(f) for f in XL if 'Combustivel' in kind(f)])
BAL=[f for f in XL if 'Pesagem' in kind(f)]
b=pd.concat([pd.read_excel(f,header=None).iloc[2:] for f in BAL])
b=b[b[0].apply(lambda x:isinstance(x,DT.datetime))&b[2].notna()]
bal=pd.DataFrame(dict(data=b[0],hora=b[1].astype(str),frota=b[2].astype(int),ticket=b[3].astype(int),liq=b[12].astype(float)))
m=pd.concat([pd.read_csv(f,sep=';',low_memory=False) for f in sorted(glob.glob(os.path.join(IN,'*.csv')))])
m['t']=pd.to_datetime(m['Data/Hora'],dayfirst=True); m=m.sort_values(['Equipamento','t']).reset_index(drop=True)
m['gap']=(m.groupby('Equipamento').t.shift(-1)-m.t).dt.total_seconds()
