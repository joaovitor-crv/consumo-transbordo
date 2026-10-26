# Consumo de combustível — Transbordos CRV

Painel de acompanhamento do consumo de combustível dos transbordos das frentes, no mesmo layout do painel das colhedoras.

**Painel:** `index.html` (abre direto no navegador ou pelo GitHub Pages).

## Bases (não versionadas — ficam na pasta `entrada/`)

| Base | Arquivo | Uso |
|---|---|---|
| Abastecimento | xlsx "Saída de Combustível por Código do Posto" (postos 622xx e 222xx) | litros e custo |
| Balança | xlsx de pesagem, espécie Trator - Transbordo | toneladas (peso líquido, coluna M) e viagens |
| Monit | CSV de exportação (separador `;`) | horas de motor ligado, motor ocioso, paradas e RPM |

## Como atualizar

```bash
pip install pandas openpyxl
python3 scripts/proc.py entrada              # período comum às três bases
python3 scripts/proc.py entrada 2026-10-12 2026-10-22   # ou período fixo
```

O script regrava `index.html` a partir de `scripts/template.html`.

## Regras

- Só entram os transbordos das frentes com telemetria; ficam fora os de manutenção/reforma/parado e os sem telemetria (sem registro no monit).
- L/t = litros ÷ toneladas. Meta 1,00 L/t (mesma das colhedoras): verde até 1,00; cinza 1,01–1,15; amarelo 1,16–1,50; vermelho acima de 1,50.
- Motor ocioso = estado PARADA com motor ligado. Cada parada é uma sequência contínua de leituras; de cada uma são descontados 90 s. Cada leitura vale o tempo até a próxima, no máximo 5 min. Meta 10%.
- **RPM 850 é falha do sistema** e conta como motor desligado (fora de horas ligado, ocioso e faixas de RPM).
- Turnos: A 07–15h, B 15–23h, C 23–07h.
