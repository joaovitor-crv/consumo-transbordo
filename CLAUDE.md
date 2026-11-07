# Relatório de consumo dos transbordos (CRV)

Use sempre o gerador; não redesenhe a página à mão:
```
python3 gerar/gerar_relatorio.py --pdf <INDICADOR_TRANSBORDOS.pdf> --monit <MONIT.csv> --frentes 1,2,3,5,6
```
- Mesmo padrão e métricas do relatório das colhedoras (repositório Consumo-de-colhedora), com as diferenças:
  - motor ocioso: todo o tempo em PARADA com motor ligado conta (basculando não conta), descontando 90 s de cada parada, igual às colhedoras;
  - meta de L/h por modelo, lida do PDF (frente e geral = média ponderada pelas horas);
  - faixas de RPM: até 900, 901–1.650, 1.651–1.800, 1.801–1.900, 1.901–2.000 e 2.001+ (divisão de 1.801–2.000 em 30/10/2026, igual às colhedoras); excesso = acima de 1.650;
  - ranking de excesso de RPM só com pelo menos 20 h de motor ligado; transbordo com 0 h no indicador e sem monit fica fora da tabela;
  - top 10 operadores em excesso de RPM (>1.650, mínimo 20 h); rankings por transbordo clicáveis (operadores do trator); quadro "Com abastecimento, sem dados no Solinftec";
  - cores de RPM: verde (lenta), azul (901–1.650), amarelo pastel (1.651–1.800), laranja pastel (1.801–1.900), laranja (1.901–2.000), vermelho (2.001+).
- Recursos iguais aos das colhedoras (30/10/2026): operador com +N clicável (transbordos que operou); "Outros" dos motivos clicável; % ocioso na lista de operadores abre os apontamentos; operador "null" = "Sem Operador"; horas sempre em horas:minutos; layout em 3 colunas (esquerda: tabela, motivo e turno; meio: registros de ocioso, ocioso por operador, L/h e L/t; direita: RPM, top 10 operadores em excesso, sem Solinftec).
- Layout e opções iguais ao relatório das colhedoras (07/11/2026, pedido do usuário; parâmetros do transbordo mantidos): `gerar/modelo.html` foi feito a partir do modelo das colhedoras, só trocando os textos e as regras do transbordo (excesso acima de 1.650 = faixas a partir de `D.exc_i`; meta de L/h por modelo; 20 h nos rankings de RPM). Inclui: seletor "Semana" no topo, botão "Baixar PDF" (impressão A3 em pé), comparação com a semana anterior (cartões "ant.", coluna "vs" na tabela, barras cinza em L/h e L/t por frente, linhas de ocioso e de RPM), todo nome de operador clicável (transbordos operados com ocioso e acima de 1.650), frentes clicáveis na faixa de RPM por frente e quadro "Operadores acima de 1.650 RPM por frente". Ao mudar o modelo das colhedoras, leve a mudança para cá do mesmo jeito.
- Semanas: cada execução salva `semana-AAAA-MM-DD_AAAA-MM-DD.html`, refaz `semanas.js` e copia a mais recente para `index.html`. A comparação usa a página da semana anterior já gerada (ou `--anterior <semana-*.html>`), porque o PDF dos transbordos não traz a semana anterior. A semana de 19 a 25/10/2026 foi remontada no layout novo a partir dos dados do painel antigo (sem os cliques novos de operador e de frente, que precisam do monit dela). Faça commit das páginas `semana-*.html` e do `semanas.js` junto com o `index.html`.
- Frentes padrão: 1, 2, 3, 5 e 6. Assinatura: "Desenvolvido por João Vitor - CRV".
- Depois de mudar `gerar/modelo.html` ou `gerar/gerar_relatorio.py`, regenere, confira no navegador e faça commit e push.
