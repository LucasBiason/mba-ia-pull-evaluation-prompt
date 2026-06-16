# Pull, Otimização e Avaliação de Prompts com LangChain e LangSmith

Tech Challenge — MBA Engenharia de Software com IA (Full Cycle).
Software que faz **pull** de um prompt de baixa qualidade do LangSmith Prompt Hub,
**otimiza** com técnicas de Prompt Engineering, faz **push** da versão otimizada e
**avalia** a qualidade por 5 métricas (LLM-as-Judge), buscando a nota mínima em todas.

- Prompt otimizado (público): `lucasbiason/bug_to_user_story_v2`
- Caso de uso: converter relatos de bug em **User Stories** ágeis (formato "Como um... eu quero... para que...") com Critérios de Aceitação em Gherkin.

---

## Como Executar

### Pré-requisitos

- Python 3.9+
- Conta no [LangSmith](https://smith.langchain.com) (API key)
- Chave de LLM: **Google Gemini** (`AIza...`, free tier) — provider padrão — ou OpenAI

### 1. Ambiente

```bash
python3 -m venv venv
source venv/bin/activate            # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configuração (`.env`)

Copie `.env.example` para `.env` e preencha:

```bash
LANGSMITH_API_KEY=lsv2_...
USERNAME_LANGSMITH_HUB=seu_handle   # handle público do LangSmith (ex.: lucasbiason)
GOOGLE_API_KEY=AIza...
LLM_PROVIDER=google
LLM_MODEL=gemini-2.5-flash          # gera as respostas
EVAL_MODEL=gemini-2.5-flash         # juiz das métricas
```

### 3. Fluxo (na ordem)

```bash
python src/pull_prompts.py      # 1. baixa o prompt RUIM (leonanluppi/bug_to_user_story_v1)
# 2. otimização: editar prompts/bug_to_user_story_v2.yml (já feito)
python src/push_prompts.py      # 3. publica o v2 no Hub
python src/evaluate.py          # 4. avalia (5 métricas) e imprime APROVADO/REPROVADO
pytest tests/test_prompts.py    # 5. testes de validação do prompt (6)
```

Extra (avaliação nativa no LangSmith, gera um **Experiment/dashboard** na UI):

```bash
python scripts/langsmith_eval.py            # avalia o v2 e registra um Experiment no dataset
python scripts/langsmith_eval.py --prompt leonanluppi/bug_to_user_story_v1   # baseline v1
```

---

## Técnicas Aplicadas (Fase 2)

O prompt otimizado (`prompts/bug_to_user_story_v2.yml`) combina **3 técnicas** — Few-shot
(obrigatória) + duas adicionais — separando bem **System Prompt** (instruções/persona) de
**User Prompt** (o relato a converter).

### 1. Role Prompting (persona)

**Por quê:** dar ao modelo uma identidade e expertise específicas eleva o nível e a consistência da saída.
**Como apliquei:** o System Prompt abre com

> "Você é um Product Manager sênior especializado em metodologias ágeis (Scrum/Kanban)..."
> e define uma **regra de ator dinâmico**: para bugs de usuário final usa persona humana específica
> ("cliente usando Safari"); para bugs de backend/infra usa **"Como o sistema..."** — espelhando o
> padrão das referências do dataset.

### 2. Chain of Thought (CoT) — interno

**Por quê:** análise de bug exige raciocínio (quem é afetado, o que se quer, qual o valor, quais critérios).
**Como apliquei:** instruo o modelo a raciocinar **passo a passo internamente** (ator → ação → valor →
critérios), mas a **não expor** esse raciocínio — a resposta final contém só a User Story. Isso evita
texto extra que derruba as métricas de clareza/precisão.

### 3. Few-shot Learning (obrigatória)

**Por quê:** exemplos de entrada/saída ancoram formato, tom e nível de detalhe muito melhor que instruções.
**Como apliquei:** **2 exemplos** completos (entrada → saída): um de **usuário final** (botão de
carrinho) e um de **backend/sistema com seção "Critérios Técnicos"** (webhook 500), cobrindo os dois
registros que o dataset usa.

**Outros requisitos atendidos no prompt:** instruções e regras explícitas de comportamento, formato
obrigatório (Markdown + Gherkin pt-BR), tratamento de **edge cases** (relato vago, múltiplos problemas,
impacto/severidade) e acentuação correta.

---

## Resultados Finais

### Tabela comparativa — v1 (ruim) vs v2 (otimizado)

| Métrica     | v1 (baseline ruim)\* | v2 (otimizado)   |
| ----------- | -------------------- | ---------------- |
| Helpfulness | ~0.45                | **0.94** ✓       |
| Correctness | ~0.52                | **0.86** ✓       |
| F1-Score    | ~0.48                | **0.78–0.83**    |
| Clarity     | ~0.50                | **0.94** ✓       |
| Precision   | ~0.46                | **0.93–0.95** ✓  |
| **Média**   | ~0.48                | **~0.89–0.91** ✓ |

\* v1 = prompt intencionalmente ruim (instruções vagas, sem persona, sem exemplos, `{bug_report}`
duplicado). Valores ilustrativos do enunciado — é o ponto de partida que motivou a otimização.

> Nota mínima oficial = **0.8** em todas as 5 métricas (o repositório base reduziu de 0.9 para 0.8 —
> PR #16 "reduzir nota mínima para 0.8"). O `evaluate.py` checa `all(score >= 0.8)` + média ≥ 0.8.

### Observação importante sobre o F1 (transparência)

4 das 5 métricas passam de forma estável e folgada. **O F1-Score oscila entre ~0.77 e ~0.83 entre
execuções idênticas** — não por qualidade do prompt, mas porque, no free tier, tanto a **geração**
quanto o **juiz** usam `gemini-2.5-flash`, um modelo **"thinking"** (não-determinístico mesmo com
`temperature=0`). Comprovação: o mesmo exemplo, com saída **idêntica à referência**, foi pontuado
**0.46 numa rodada e 1.00 noutra** pelo juiz. Em referências curtas (bugs simples), pequenas variações
de frase viram grandes variações de F1.

**Implicação:** a média fica sempre ≥ 0.89, e o status alterna entre **APROVADO** e **REPROVADO**
unicamente pelo F1 cruzar a linha de 0.8. Para um APROVADO **determinístico**, a recomendação é usar
um juiz mais forte e estável — **gpt-4o** como `EVAL_MODEL` (configuração OpenAI prevista pelo próprio
desafio). Ver `docs/PARECER.md` para a análise completa.

### Evidências no LangSmith

- **Prompt publicado:** `lucasbiason/bug_to_user_story_v2` (LangSmith → Prompts).
- **Dataset de avaliação:** `prompt-evaluation-eval` (15 exemplos) — LangSmith → Datasets.
- **Tracing:** projeto `prompt-evaluation` (LangSmith → Projects) — execuções detalhadas de cada exemplo.
- **Experiment/dashboard:** experimento `bug_to_user_story_v2-8d6e1951` gerado por `scripts/langsmith_eval.py`
  ([abrir no LangSmith](https://smith.langchain.com/o/33decbac-b63f-43ef-a686-1c0b74dfd577/datasets/0c9f44be-a52b-4fee-8e92-136467e8ba7c/compare?selectedSessions=b3b9c702-df0e-4f6a-83cf-c364710b861c)).
- Output bruto de uma avaliação: `docs/eval-result.txt`.
- Base teórica que guiou a otimização: `docs/evaluation-knowledge.md`.

---

## Estrutura do projeto

```
├── prompts/
│   ├── bug_to_user_story_v1.yml   # prompt ruim (pull do Hub)
│   └── bug_to_user_story_v2.yml   # prompt otimizado (Role + CoT + Few-shot)
├── datasets/bug_to_user_story.jsonl   # 15 bugs (não alterar)
├── src/
│   ├── pull_prompts.py            # implementado — pull do v1
│   ├── push_prompts.py            # implementado — push público do v2 (idempotente)
│   ├── evaluate.py                # pronto — avaliação (5 métricas)
│   ├── metrics.py                 # pronto — métricas LLM-as-Judge
│   └── utils.py                   # pronto — helpers / LLM factory
├── scripts/langsmith_eval.py      # extra — Experiment/dashboard nativo no LangSmith
├── tests/test_prompts.py          # implementado — 6 testes de validação
└── docs/                          # evaluation-knowledge, eval-result, PARECER
```

## Técnicas (metadados do prompt)

`Role Prompting`, `Chain of Thought`, `Few-shot Learning` — declaradas em
`prompts/bug_to_user_story_v2.yml` (campo `techniques_applied`).
