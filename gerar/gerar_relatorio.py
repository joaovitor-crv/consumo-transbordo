"""Gera o index.html do relatório de consumo dos tratores transbordo.

Uso:
  python gerar/gerar_relatorio.py --pdf INDICADOR.pdf --monit MONIT1.csv MONIT2.csv [--frentes 1,2,3]

- Consumo (horas, diesel, L/h, toneladas, L/t): coluna SEMANA do PDF
  "Indicador Consumo de Combustível — Tratores Transbordo". O período do relatório é o da SEMANA.
- Motor ocioso, paradas, RPM, motivos, turnos e operadores: exportação do monit (CSV com ';').
- Requer pdftotext (poppler-utils).

Desenvolvido por João Vitor - CRV
"""
import argparse
import collections
import csv
import json
import os
import re
import subprocess
from datetime import datetime, timedelta

AQUI = os.path.dirname(os.path.abspath(__file__))
CAP = 600          # cada leitura do monit vale no máximo 10 min
DESCONTO = 90      # segundos descontados de cada parada com motor ligado
META_LT, META_OC = 1.0, 0.10   # a meta de L/h vem do PDF, por modelo
MIN_H = 5 * 3600   # mínimo de motor ligado para entrar no ranking de operador
MIN_H_RPM = 20 * 3600  # mínimo de motor ligado para entrar no ranking de excesso de RPM
ROMANO = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7, "VIII": 8, "IX": 9, "X": 10}
BANDAS = ["1 - 900 (lenta)", "901 - 1.650", "1.651 - 1.800", "1.801 - 1.900", "1.901 - 2.000", "2.001+"]
EXCESSO = BANDAS[2:]  # transbordo pode rodar até 1.650 RPM


def num(s):
    s = s.strip()
    if s in ("—", "-", ""):
        return None
    return float(s.replace(".", "").replace(",", "."))


def hm(h):
    """Horas decimais em horas:minutos (0,5 -> 0:30)."""
    m = round(h * 60)
    return f"{br(m // 60, 0)}:{m % 60:02d}"


def sem_null(v):
    """Operador vazio ou "null" (exportação do monit sem operador logado) vira vazio."""
    v = (v or "").strip()
    return "" if v.lower() in ("null", "none", "-") else v


def nome_motivo(m):
    return m.replace("Manutencao", "Manutenção").replace("Refeicao", "Refeição")


def br(v, d):
    return f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


# ---------------- PDF do indicador ----------------
def ler_pdf(caminho, frentes):
    txt = subprocess.run(["pdftotext", "-layout", caminho, "-"], capture_output=True, text=True, check=True).stdout
    per = re.findall(r"(\d{2}/\d{2}/\d{4}) a (\d{2}/\d{2}/\d{4}) · \d+ dias", txt)
    if not per:
        raise SystemExit("Não achei o período da SEMANA no PDF.")
    ini, fim = per[0]
    atual = re.search(r"Atualizado em (\d{2}/\d{2}/\d{4} \d{2}:\d{2})", txt)
    grupos = collections.OrderedDict()
    atual_fr = None
    for ln in txt.splitlines():
        s = ln.strip()
        m = re.match(r"^F-([IVX]+)\b", s)
        if m:
            atual_fr = ROMANO.get(m.group(1))
            continue
        if s.startswith("TOTAL GERAL") or s.startswith("SEM FRENTE"):
            atual_fr = None
            continue
        m = re.match(r"^(\d{5})\s+(.*?)ℓ/h\s+([\d,.]+)\s+(.*)$", s)
        if m and atual_fr in frentes:
            t = m.group(4).split()
            grupos.setdefault(atual_fr, []).append(dict(
                frota=int(m.group(1)), meta=num(m.group(3)), horas=num(t[0]) or 0, litros=num(t[1]) or 0,
                lh=num(t[2]), ton=num(t[3]), lt=num(t[4])))
    falta = [f for f in frentes if f not in grupos]
    if falta:
        raise SystemExit(f"Frente(s) {falta} não encontrada(s) no PDF.")
    grupos = collections.OrderedDict((f, grupos[f]) for f in frentes)
    aviso = re.search(r"integrado só até (\d{2}/\d{2}/\d{4})", txt)
    return ini, fim, (atual.group(1) if atual else ""), grupos, {"aviso_ate": aviso.group(1) if aviso else None}


# ---------------- monit ----------------
def ler_monit(arquivos, frota_frente, ini, fim):
    d0 = datetime.strptime(ini, "%d/%m/%Y")
    d1 = datetime.strptime(fim, "%d/%m/%Y") + timedelta(days=1)
    rows = collections.defaultdict(list)
    fora = set()
    for arq in arquivos:
        with open(arq, encoding="utf-8", errors="replace") as fh:
            for r in csv.DictReader(fh, delimiter=";"):
                eq = r["Equipamento"].strip()
                if eq not in frota_frente:
                    fora.add((eq, r["Grupo"].strip()))
                    continue
                t = datetime.strptime(r["Data/Hora"], "%d/%m/%Y %H:%M:%S")
                if not (d0 <= t < d1):
                    continue
                try:
                    rpm = float(r["RPM Motor"].replace(",", "."))
                except ValueError:
                    rpm = 0
                rows[eq].append(dict(
                    t=t, est=r["Estado"].strip(), lig=r["Motor Ligado"] == "Sim" or rpm >= 700, rpm=rpm,
                    op=r["Operacao"].strip().title(), oper=sem_null(r["Operador"]).title() or "Sem Operador",
                    g=f"FRENTE {frota_frente[eq]}"))
    return rows, d1, fora


def banda(r):
    return BANDAS[0] if r <= 900 else BANDAS[1] if r <= 1650 else BANDAS[2] if r <= 1800 else BANDAS[3] if r <= 1900 else BANDAS[4] if r <= 2000 else BANDAS[5]


def turno(t):
    return "A" if 7 <= t.hour < 15 else "B" if 15 <= t.hour < 23 else "C"


def detalhe(ep_l, ep_o, ep_x, ep_m):
    """Por trator: operadores com motor ligado, ocioso e tempo acima de 1.650 RPM (para o clique nos rankings)."""
    det = collections.defaultdict(list)
    for (eq, op), lig in ep_l.items():
        if lig < 900:  # menos de 15 min de motor ligado no trator: não entra
            continue
        mot = sorted(ep_m[(eq, op)].items(), key=lambda m: -m[1])
        det[eq].append(dict(op=op, lig=lig / 3600, oc=ep_o[(eq, op)] / 3600, x=ep_x[(eq, op)] / 3600,
                            mot=[[nome_motivo(m), round(v / 3600, 4)] for m, v in mot if v > 0]))
    return {eq: sorted(L, key=lambda r: -r["lig"]) for eq, L in det.items()}


def calcular(rows, fim_dt):
    F = {}
    lig_d = collections.defaultdict(float); oc_d = collections.defaultdict(float)
    rpm_b = collections.defaultdict(float); mot = collections.defaultdict(float); tur = collections.defaultdict(float)
    op_l = collections.defaultdict(float); op_o = collections.defaultdict(float); op_f = collections.defaultdict(set)
    fr_rpm = collections.defaultdict(lambda: collections.defaultdict(float))
    eq_rpm = collections.defaultdict(lambda: collections.defaultdict(float))
    op_rpm = collections.defaultdict(lambda: collections.defaultdict(float))
    ep_l = collections.defaultdict(float); ep_o = collections.defaultdict(float); ep_x = collections.defaultdict(float)
    ep_m = collections.defaultdict(lambda: collections.defaultdict(float))  # ocioso por trator, operador e motivo
    longas = {}
    tot = dict(paradas=0, paradas_90=0, oc_bruto=0.0)
    for eq, L in rows.items():
        L.sort(key=lambda x: x["t"])
        for i, x in enumerate(L):
            nt = L[i + 1]["t"] if i + 1 < len(L) else min(x["t"] + timedelta(seconds=60), fim_dt)
            x["d"] = max(0.0, min((nt - x["t"]).total_seconds(), CAP))
        lig = oc = 0.0; par = p10 = p30 = 0; h10 = 0.0
        for x in L:  # tempo de motor ligado (todas as leituras)
            if x["lig"]:
                lig += x["d"]; dia = x["t"].strftime("%d/%m"); lig_d[dia] += x["d"]
                rpm_b[banda(x["rpm"])] += x["d"]; fr_rpm[x["g"]][banda(x["rpm"])] += x["d"]
                eq_rpm[eq][banda(x["rpm"])] += x["d"]
                op_l[x["oper"]] += x["d"]; op_f[x["oper"]].add(eq); op_rpm[x["oper"]][banda(x["rpm"])] += x["d"]
                ep_l[(eq, x["oper"])] += x["d"]
                if banda(x["rpm"]) in EXCESSO: ep_x[(eq, x["oper"])] += x["d"]
        i = 0
        while i < len(L):  # paradas com motor ligado
            if L[i]["est"] == "PARADA" and L[i]["lig"]:
                j = i; dur = 0.0
                while j < len(L) and L[j]["est"] == "PARADA" and L[j]["lig"]:
                    dur += L[j]["d"]; j += 1
                par += 1; tot["paradas"] += 1; tot["oc_bruto"] += dur
                if dur > 600: p10 += 1; h10 += dur
                if dur > 1800: p30 += 1
                if dur > DESCONTO:
                    tot["paradas_90"] += 1; k = (dur - DESCONTO) / dur
                    for s in L[i:j]:
                        v = s["d"] * k; oc += v
                        oc_d[s["t"].strftime("%d/%m")] += v; mot[s["op"]] += v; tur[turno(s["t"])] += v; op_o[s["oper"]] += v; ep_o[(eq, s["oper"])] += v; ep_m[(eq, s["oper"])][s["op"]] += v
                i = j
            else:
                i += 1
        F[eq] = dict(lig=lig, oc=oc, paradas=par, pct=oc / lig if lig else None)
        longas[eq] = dict(frota=eq, p10=p10, p30=p30, h10=h10 / 3600)
    dias = sorted(lig_d, key=lambda s: (s[3:], s[:2]))
    mt = sorted(mot.items(), key=lambda x: -x[1]); outros = sum(v for _, v in mt[7:])
    tl = sum(rpm_b.values()) or 1
    eq_g = {eq: L[0]["g"] for eq, L in rows.items() if L}

    def maquinas(o):
        """Tratores e frentes em que o operador trabalhou, do que teve mais horas de motor ligado para o que teve menos."""
        m = [dict(eq=eq, fr=eq_g.get(eq, "").replace("FRENTE ", "F"), h=h / 3600) for (eq, op), h in ep_l.items() if op == o and h >= 900]
        return sorted(m, key=lambda r: -r["h"])

    ops = [dict(l=o, v=op_o[o] / op_l[o], lig=op_l[o] / 3600, oc=op_o[o] / 3600, maq=maquinas(o),
                fr=", ".join(sorted(op_f[o])) if len(op_f[o]) <= 3 else f"{len(op_f[o])} transbordos")
           for o in op_l if op_l[o] >= MIN_H]
    ops.sort(key=lambda x: -x["v"])
    rtop = [dict(l=e, v=sum(v[b] for b in EXCESSO) / sum(v.values())) for e, v in eq_rpm.items() if sum(v.values()) >= MIN_H_RPM]
    rtop.sort(key=lambda x: -x["v"])
    otop = [dict(l=o, v=sum(v[b] for b in EXCESSO) / sum(v.values()), lig=sum(v.values()) / 3600, maq=maquinas(o),
                 fr=", ".join(sorted(op_f[o])) if len(op_f[o]) <= 3 else f"{len(op_f[o])} transbordos")
            for o, v in op_rpm.items() if sum(v.values()) >= MIN_H_RPM]
    otop.sort(key=lambda x: -x["v"])
    lg = sorted((v for v in longas.values() if v["p10"]), key=lambda x: (-x["p10"], -x["h10"]))
    return dict(
        F=F,
        oc_frota=sorted([dict(l=e, v=x["pct"]) for e, x in F.items() if x["pct"] is not None], key=lambda r: -r["v"]),
        oc_top=[dict(l=e, v=x["oc"] / 3600) for e, x in sorted(F.items(), key=lambda x: -x[1]["oc"])[:10]],
        oc_dia=[dict(l=d, v=oc_d[d] / lig_d[d]) for d in dias if lig_d[d]],
        rpm=[dict(l=b, v=rpm_b[b] / tl) for b in BANDAS],
        rpm_frente=[dict(l=g.title(), **{f"b{i}": fr_rpm[g][b] / (sum(fr_rpm[g].values()) or 1) for i, b in enumerate(BANDAS)})
                    for g in sorted(fr_rpm, key=lambda s: int(s.split()[-1]))],
        rpm_top=rtop[:10],
        rpm_op=otop[:10],
        det=detalhe(ep_l, ep_o, ep_x, ep_m),
        motivo=[dict(l=l, v=v / 3600) for l, v in mt[:7]] + ([dict(l="Outros", v=outros / 3600)] if outros else []),
        outros=[dict(l=nome_motivo(l), v=v / 3600) for l, v in mt[7:] if v > 0],
        oc_turno=[dict(l=t, v=tur[t] / 3600) for t in "ABC"],
        oc_op=ops[:10],
        longas=lg[:8],
        tot=dict(lig=sum(x["lig"] for x in F.values()) / 3600, oc=sum(x["oc"] for x in F.values()) / 3600,
                 oc_bruto=tot["oc_bruto"] / 3600, paradas=tot["paradas"], paradas_90=tot["paradas_90"]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--monit", required=True, nargs="+")
    ap.add_argument("--frentes", default="1,2,3,5,6")
    ap.add_argument("--saida", default=os.path.join(AQUI, "..", "index.html"))
    a = ap.parse_args()
    frentes = [int(x) for x in a.frentes.split(",")]

    ini, fim, atualizado, grupos, totais = ler_pdf(a.pdf, frentes)
    frota_frente = {str(x["frota"]): f for f, L in grupos.items() for x in L}
    rows, fim_dt, fora = ler_monit(a.monit, frota_frente, ini, fim)
    fora_fr = sorted(eq for eq, g in fora if g in {f"FRENTE {f}" for f in frentes})
    M = calcular(rows, fim_dt)

    tab, fr, sem, parados, sem_monit = [], [], [], [], []
    for f in frentes:
        linhas = []
        for x in grupos[f]:
            m = M["F"].get(str(x["frota"]))
            if not m and not x["horas"]:
                parados.append(str(x["frota"]))  # 0 h no indicador e sem monit: não entra na tabela
                continue
            if not m:
                sem.append(str(x["frota"]))
                sem_monit.append(dict(frota=x["frota"], frente=f, litros=x["litros"], horas=x["horas"], lh=x["lh"]))
            linhas.append(dict(x, pct=m["pct"] if m else None, paradas=m["paradas"] if m else None))
        H = sum(x["horas"] for x in grupos[f])
        T = dict(horas=H, litros=sum(x["litros"] for x in grupos[f]), ton=sum(x["ton"] or 0 for x in grupos[f]),
                 meta=sum(x["meta"] * x["horas"] for x in grupos[f]) / H if H else grupos[f][0]["meta"])
        T["lh"] = T["litros"] / H if H else None
        T["lt"] = T["litros"] / T["ton"] if T["ton"] else None
        tab.append(dict(grupo=f"FRENTE {f}", linhas=linhas, tot=T))
        fr.append(dict(l=f"Frente {f}", **T))
    TL = sum(x["litros"] for x in fr); TH = sum(x["horas"] for x in fr); TT = sum(x["ton"] for x in fr)
    t = M["tot"]
    nf = ", ".join(map(str, frentes[:-1])) + (" e " if len(frentes) > 1 else "") + str(frentes[-1])
    D = dict(
        periodo=f"{ini} - {fim}",
        K=dict(litros=TL, frotas=sum(1 for g in tab for x in g["linhas"] if x["horas"] or x["pct"] is not None), ton=TT,
               lt=TL / TT if TT else 0, meta=META_LT, horas=TH, lh=TL / TH if TH else 0,
               meta_lh=sum(x["meta"] * x["horas"] for x in fr) / TH if TH else 0, horas_oc=t["oc"], horas_oc_bruto=t["oc_bruto"],
               paradas=t["paradas"], paradas_90=t["paradas_90"], pct_oc=t["oc"] / t["lig"] if t["lig"] else 0),
        tabela=tab, frentes=fr, meta_oc=META_OC, sem_monit=sem_monit,
        **{k: M[k] for k in ["oc_frota", "oc_top", "oc_dia", "rpm", "rpm_frente", "rpm_top", "rpm_op", "det", "motivo", "outros", "oc_turno", "oc_op", "longas"]},
        notas=[
            f"Litros, horas, toneladas, L/h e L/t: coluna SEMANA ({ini[:5]} a {fim}) do Indicador de Consumo de Combustível — Tratores Transbordo"
            + (f", atualizado em {atualizado}" if atualizado else "") + f". Frentes {nf}.",
            f"Motor ocioso, paradas, RPM, motivos, turnos e operadores: monit de {ini[:5]} a {fim}."
            + (f" Sem telemetria nesse período: {', '.join(sem)} ({'aparece' if len(sem) == 1 else 'aparecem'} na tabela só com os dados de consumo)." if sem else ""),
            *([f"Atenção: segundo o indicador, o abastecimento é lançado à mão e está integrado só até {totais['aviso_ate']}; o diesel da semana depois dessa data pode estar incompleto."] if totais.get("aviso_ate") else []),
            *([f"Sem horas no indicador e sem monit na semana (fora da tabela): {', '.join(parados)}."] if parados else []),
            *([f"No monit nas frentes {nf}, mas sem lançamento nessas frentes no indicador (não entram): {', '.join(fora_fr)}."] if fora_fr else []),
            f"Motor ocioso descontando 90 s de cada parada: {br(t['paradas'], 0)} paradas com motor ligado; "
            f"{br(t['paradas'] - t['paradas_90'], 0)} duraram até 90 s e não contam. Sem o desconto seriam {hm(t['oc_bruto'])} h; "
            f"com o desconto, {hm(t['oc'])} h.",
        ])
    html = open(os.path.join(AQUI, "modelo.html"), encoding="utf-8").read()
    html = html.replace("__DADOS__", json.dumps(D, ensure_ascii=False)).replace("__FRENTES__", f"Frentes {nf}")
    open(a.saida, "w", encoding="utf-8").write(html)
    print(f"Relatório gerado: {ini} a {fim} · frentes {nf} · {D['K']['frotas']} transbordos · "
          f"{br(TL, 0)} L · {br(TT, 0)} t · {br(D['K']['lh'], 2)} L/h · ocioso {br(t['oc'], 1)} h ({br(D['K']['pct_oc'] * 100, 1)}%)")
    if sem:
        print("Sem monit:", ", ".join(sem))


if __name__ == "__main__":
    main()
