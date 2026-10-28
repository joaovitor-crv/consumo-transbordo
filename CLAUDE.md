# Relatório de consumo dos transbordos (CRV)

Use sempre o gerador; não redesenhe a página à mão:
```
python3 gerar/gerar_relatorio.py --pdf <INDICADOR_TRANSBORDOS.pdf> --monit <MONIT.csv> --frentes 1,2,3
```
- Mesmo padrão e métricas do relatório das colhedoras (repositório Consumo-de-colhedora), com as diferenças:
  - motor ocioso: todo o tempo em PARADA com motor ligado, sem o desconto de 90 s (definido pelo usuário em 28/10/2026); basculando não conta;
  - meta de L/h por modelo, lida do PDF (frente e geral = média ponderada pelas horas);
  - faixas de RPM: até 900, 901–1.650, 1.651–1.800, 1.801–2.000, acima de 2.000; excesso = acima de 1.650 (faixas "para teste", combinadas em 28/10/2026);
  - cores de RPM: verde (lenta), azul (901–1.650), amarelo pastel, laranja pastel, vermelho (acima de 2.000).
- Frentes padrão: 1, 2 e 3. Assinatura: "Desenvolvido por João Vitor - CRV".
- Depois de mudar `gerar/modelo.html` ou `gerar/gerar_relatorio.py`, regenere, confira no navegador e faça commit e push.
