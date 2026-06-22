# Processo de otimização e resultados

Este documento registra como cheguei ao prompt final: quais eram as limitações do prompt
original, o que ajustei em cada rodada e como isso se refletiu nas métricas.

A proposta do desafio é partir de um prompt de baixa qualidade publicado no LangSmith,
entender suas limitações, reescrevê-lo aplicando técnicas de prompt engineering e medir a
qualidade com as cinco métricas (Helpfulness, Correctness, F1-Score, Clarity e Precision)
até alcançar 0.8 em todas.

Trabalhei o tempo todo com a configuração oficial do desafio (gemini-2.5-flash para gerar a
resposta e para julgar). Ao final, executei também uma avaliação com o gpt-4o como juiz, para
ter uma segunda opinião mais rigorosa do resultado.

## O ponto de partida (v1)

O `leonanluppi/bug_to_user_story_v1` foi escrito de forma propositalmente simples: persona
genérica ("você é um assistente"), sem instrução de formato, sem exemplos e com a variável
`{bug_report}` repetida no texto. Na prática, ele devolve um texto solto, sem o formato de
User Story e sem critérios de aceitação. Nas métricas, isso fica em torno de 0.45 a 0.50 em
todas — é o ponto de partida da otimização.

## As rodadas de teste

Preferi ajustar um ponto por vez e executar o `evaluate.py` a cada mudança, para acompanhar o
efeito de cada ajuste nas notas em vez de alterar tudo de uma só vez. Resumo do caminho:

| Versão    | O que mudei                                                      | Por quê                                                                     | Resultado                              |
| --------- | ---------------------------------------------------------------- | --------------------------------------------------------------------------- | -------------------------------------- |
| v2        | Role Prompting (PM sênior) + formato fixo (User Story + Gherkin) | Dar identidade ao modelo e fixar o formato da saída                         | Gemini ~0.90, F1 ainda instável        |
| v2.1–v2.2 | Acentuação correta e critérios mais fiéis ao relato              | As referências do dataset são acentuadas e específicas                      | Clarity e Precision subiram e estáveis |
| v2.3      | Inferência de domínio (deixar de assumir e-commerce)             | O modelo tendia a assumir "loja/carrinho" em bugs de CRM ou de dashboard    | gpt-4o em 0.79                         |
| v2.4      | Chain of Thought interno + tratamento de edge cases              | Conduzir o raciocínio ator → ação → valor → critério sem poluir a resposta  | gpt-4o em 0.82                         |
| v2.5      | Seção "Critérios Técnicos" para bugs com cálculo/performance/API | As referências técnicas trazem a abordagem de solução, não apenas o sintoma | Gemini 0.9170 (aprovado)               |

A partir da v2.3, a maior parte das métricas já passava com folga. O trabalho das últimas
rodadas concentrou-se quase todo no F1, que era a métrica que permanecia próxima do limite.

## Resultado final

Rodada final do v2.5 na configuração oficial (gemini-2.5-flash gerando e julgando):

```
==================================================
Prompt: lucasbiason/bug_to_user_story_v2
==================================================

Métricas Derivadas:
  - Helpfulness: 0.96 ✓
  - Correctness: 0.89 ✓

Métricas Base:
  - F1-Score: 0.82 ✓
  - Clarity: 0.95 ✓
  - Precision: 0.97 ✓

--------------------------------------------------
MÉDIA GERAL: 0.9170
--------------------------------------------------

STATUS: APROVADO - Todas as métricas >= 0.8
```

As cinco métricas acima de 0.8 e média 0.9170 — é o resultado que o desafio pede.

## Sobre a variação do F1

Quatro das cinco métricas passam de forma consistente e quase não mudam entre execuções. A
mais sensível é o F1, que oscila próximo de 0.8 mesmo com `temperature=0`. O motivo é que, no
free tier, tanto a geração quanto o juiz usam o gemini-2.5-flash, um modelo "thinking" e não
determinístico. Observei o mesmo exemplo, com a saída idêntica à referência, receber 0.46 em
uma rodada e quase 1.00 em outra do mesmo juiz. Em bugs simples, com referência curta, qualquer
diferença de uma palavra já altera bastante o F1.

Para não depender de uma execução favorável, reavaliei o mesmo v2.5 com o gpt-4o como juiz, que
é mais rigoroso e estável:

- Gemini (oficial): média 0.9170, com as cinco métricas acima de 0.8.
- gpt-4o (segunda opinião): média 0.8235, com quatro métricas passando e o F1 em 0.75.

Optei por não elevar o F1 acima de 0.8 no gpt-4o incluindo os próprios exemplos do dataset como
few-shot — isso equivaleria a memorizar as respostas da avaliação e comprometeria a generalização
do prompt. Os exemplos que uso no prompt são casos diferentes de propósito (salvar perfil, total
de relatórios e cálculo de frete), fora do conjunto de avaliação. Por isso o F1 permanece honesto
em 0.75 sob o juiz mais severo, e ainda assim a média fica acima do mínimo.
