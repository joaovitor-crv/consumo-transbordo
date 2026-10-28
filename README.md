# Consumo de combustível — Tratores transbordo CRV

Painel de consumo dos transbordos: L/h por modelo (meta do indicador), L/t, motor ocioso, paradas longas, faixa de RPM, excesso de RPM e operadores.

**Período atual:** 19/10/2026 a 25/10/2026 (frentes 1, 2 e 3)

## Bases
- **Indicador Consumo de Combustível — Tratores Transbordo (PDF)**: coluna SEMANA (horas, diesel, L/h, meta por modelo, toneladas, L/t).
- **Monit**: telemetria (estado, motor ligado, RPM, operação, operador).

## Regras
- Frentes pelo indicador (F-I, F-II, F-III…); a frente de cada trator no monit segue a do indicador.
- Meta de L/h por modelo, do indicador (6190J e BH 224: 8,00; 7230J/7M230: 9,50). Frente e geral: média das metas ponderada pelas horas.
- Motor ocioso = PARADA com motor ligado (Sim ou RPM ≥ 700); cada leitura vale até a próxima (máx. 10 min); 90 s descontados de cada parada; basculando não conta. Meta 10%.
- RPM: transbordo pode rodar até 1.650. Faixas: até 900 (lenta), 901–1.650, 1.651–1.800, 1.801–2.000, acima de 2.000. Excesso = acima de 1.650.
- Rankings de operador e de excesso de RPM: só com pelo menos 5 h de motor ligado.
- Turnos: A 07–15h, B 15–23h, C 23–07h.

## Como gerar
```
python gerar/gerar_relatorio.py --pdf INDICADOR_TRANSBORDOS.pdf --monit MONIT.csv --frentes 1,2,3
```
Precisa de Python 3 e `pdftotext` (poppler-utils). Visual em `gerar/modelo.html` (dados em `__DADOS__`).

Desenvolvido por João Vitor - CRV
