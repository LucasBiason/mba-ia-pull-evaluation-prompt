# Conhecimento de Prompt Evaluation (Full Cycle) aplicado ao bug_to_user_story

Documento de consolidacao do material do curso Full Cycle (MBA Engenharia de Software com IA,
Modulo 02 - Prompt Engineering, Secoes 05, 07 e 08) com foco em enriquecer o projeto
`mba-ia-pull-evaluation-prompt`. Objetivo do projeto: otimizar o prompt `bug_to_user_story_v2`
(Few-shot + Chain of Thought + Role Prompting) ate atingir >= 0.9 em todas as 5 metricas
(Helpfulness, Correctness, F1-Score, Clarity, Precision) com LLM-as-Judge, provider Gemini
(gemini-2.5-flash).

Cada bloco cita o arquivo-fonte para rastreabilidade. Material lido em modo read-only.

## Indice

1. Fundamentos: objetivo, metrica, runner
2. Datasets de avaliacao (formato, origens, splits)
3. Tipos de evaluators
4. LLM-as-Judge: criterios e rubricas recomendados
5. Score continuo vs binario; com vs sem referencia
6. Metricas de classificacao: Precision / Recall / F1 e pairwise
7. Interpretando notas baixas e iterando o prompt (casos degradados)
8. Boas praticas que comprovadamente sobem as notas
9. Pegadinhas e erros comuns
10. Prompt como software: YAML, contrato e testes automatizados
11. Recomendacoes acionaveis para o bug_to_user_story_v2

---

## 1. Fundamentos: objetivo, metrica, runner

O fluxo canonico do curso e: definir **o que** medir (objetivo) -> escolher **como** medir
(metrica) -> escolher **quem** executa (runner/evaluator) -> ler **score + reasoning + custo** no
dashboard.

> "eu sei o que, eu sei como, mas quem vai fazer isso? Quem e o meu runner?"
> -- `07-Prompt-Evaluation/01-evaluators-runner-e-tipos.md`

Regra geral que se repete na secao: **as metricas so importam alinhadas ao objetivo**; nem toda
metrica se aplica a todo caso (`07-Prompt-Evaluation/08-embedding-distance.md`,
`07-Prompt-Evaluation/12-cenas-para-os-proximos-capitulos.md`).

---

## 2. Datasets de avaliacao (formato, origens, splits)

Fonte: `07-Prompt-Evaluation/02-datasets.md` e `03-estrutura-dos-exemplos.md`.

- **Sem dados estruturados antes da execucao nao ha avaliacao.** O dataset e o insumo comum que
  torna a medicao reproduzivel.
- **Formato JSONL** (1 JSON completo por linha). Campos do curso: `input` (codigo + tarefa +
  idioma), `output` (referencia/ground truth) e `metadata` (`topic`, `category`).
- **Tamanho:** 18 exemplos no curso. Recomendacao explicita de **nao exagerar** para nao estourar
  conta gratuita do LangSmith (rate limit).
- **Duas origens:** (a) execucoes reais de producao normalizadas; (b) sintetico gerado por IA com
  um bom prompt cobrindo N cenarios.
- **Gargalo real:** ter um dataset **expressivo** que teste/valide os pressupostos. Muitas pessoas
  travam aqui.
- **Split por complexidade:** o `metadata` carrega categoria/topico, permitindo segmentar leitura
  por tipo de caso. No projeto, o dataset `bug_to_user_story.jsonl` ja usa
  `metadata.complexity` (simple/medium/complex) e `metadata.domain`/`type`.
- **Scripts:** `upload_dataset.py` (sobe o JSONL ao LangSmith) e `reset.py` (apaga o dataset para
  reset limpo).

Exemplo de estrutura de entrada (`02-datasets.md`):

```json
{
  "input": { "language": "Go", "task": "...", "code": "..." },
  "output": { "findings": [ ... ], "summary": "..." },
  "metadata": { "topic": "http", "category": "robustez" }
}
```

Splits de complexidade na evaluation comparativa (`08-evaluation-comparativa.md`): dataset
**balanceado** (ex.: 50% security / 50% performance) para evidenciar a evolucao de um prompt entre
dominios.

---

## 3. Tipos de evaluators

Fonte: `07-Prompt-Evaluation/01-evaluators-runner-e-tipos.md`.

| Tipo                | O que faz                                                                                | Retorno            |
| ------------------- | ---------------------------------------------------------------------------------------- | ------------------ |
| Code Evaluator      | logica programatica (regra/formula/schema). Ex.: Exact Match, json_validity              | numero/string/bool |
| LLM-as-Judge        | LLM aplica rubrica e devolve nota + justificativa (relevance, faithfulness, conciseness) | score + reasoning  |
| Pairwise Evaluator  | compara 2 saidas no mesmo input e devolve preferencia                                    | A/B                |
| Summary Evaluator   | agrega varios exemplos em metricas finais (pass rate, precision, recall, F1)             | metrica do dataset |
| Composite Evaluator | formula ponderada sobre metricas ja medidas, alinhada a prioridade de negocio            | score ponderado    |

Assinatura de um **custom evaluator** (`04-primeira-avaliacao-format-eval.md`):
`(run, example) -> {"score": float, "comment": str}`.

Exemplo de Code Evaluator deterministico (validacao de schema, score 1.0/0.0):

```python
def validate_schema(run, example):
    try:
        data = json.loads(run.outputs.get("output", ""))
        jsonschema.validate(instance=data, schema=EXPECTED_SCHEMA)
        return {"score": 1.0, "comment": "Valid schema"}
    except json.JSONDecodeError as e:
        return {"score": 0.0, "comment": f"Invalid JSON: {e}"}
    except jsonschema.ValidationError as e:
        return {"score": 0.0, "comment": f"Invalid schema: {e.message}"}
```

Composite (`01-evaluators-runner-e-tipos.md`): `quality = 0.9*0.5 + 0.7*0.3 + 0.8*0.2 = 0.83`.

---

## 4. LLM-as-Judge: criterios e rubricas recomendados

Fonte: `07-Prompt-Evaluation/05-evaluators-binarios.md`, `06-score-com-range.md`,
`07-additional-criteria-e-correctness.md`.

Criterios **built-in** do LangChain (nao exigem escrever formula): `conciseness`, `helpfulness`,
`coherence`, `detail`, `depth`, `consistency`, `relevance`, `correctness`.

Criterios **customizados** (rubrica propria via dict `{nome: descricao}`), recomendados pelo
instrutor (`07-additional-criteria-e-correctness.md`):

- **faithfulness:** "A resposta e grounded no codigo; nao invente problema/contexto que nao
  existe." (detecta alucinacao)
- **format_adherence:** "Retornou somente JSON valido, sem texto antes/depois, sem Markdown."
- **code_specificity:** "Apontou a linha, usou termos tecnicos e trouxe dados concretos."

```python
faithfulness = LangChainStringEvaluator("score_string", config={"normalize_by": 10,
    "criteria": {"faithfulness": "A resposta e grounded ...; nao invente ..."}},
    prepare_data=prepare_data_no_ref)
```

Mensagem-chave: o **reasoning** do juiz vale mais que a nota isolada — ele aponta a CAUSA da
penalizacao e serve de diagnostico para iterar o prompt
(`07-additional-criteria-e-correctness.md`).

---

## 5. Score continuo vs binario; com vs sem referencia

Fonte: `05-evaluators-binarios.md`, `06-score-com-range.md`.

- **Binario (0/1):** `criteria` (sem ref) e `labeled_criteria` (com ref). Aparece como contagem
  no dashboard (ex.: correctness 14 yes / 3 no). Bom quando so importa "atende ou nao".
- **Continuo (0..1):** `score_string` / `labeled_score_string` com `normalize_by: 10`. Da
  granularidade — necessario quando a meta e um threshold (ex.: >= 0.9 do desafio).
- **Com vs sem referencia:** `prepare_data_with_ref` passa o `example_outputs` (ground truth);
  `prepare_data_no_ref` julga so a saida. Alerta do instrutor: **mais referencia induz a IA, nao
  garante resultado melhor** (`05-evaluators-binarios.md`).
- **Operacional:** o dashboard tambem mostra latencia P50/P99, tokens e **custo** por execucao
  (`06-score-com-range.md`, `07-additional-criteria-e-correctness.md`).

Resultados tipicos do laboratorio (cenario Go, prompt bom): coherence 0.85, conciseness 0.78,
depth 0.79, detail 0.81, relevance 0.82 — ou seja, **mesmo um prompt bom raramente passa de 0.85**
em metricas subjetivas sem otimizacao especifica.

---

## 6. Metricas de classificacao: Precision / Recall / F1 e pairwise

Fonte: `08-evaluation-comparativa.md`, `07-Prompt-Evaluation/12-cenas-para-os-proximos-capitulos.md`.

- **Precision** = `TP / (TP + FP)` — do que foi apontado, quanto estava certo (poucos falsos
  positivos).
- **Recall** = `TP / (TP + FN)` — dos que existiam, quanto foi achado (poucas omissoes).
- **F1** = `2*P*R / (P + R)` — media harmonica; penaliza desequilibrio entre P e R.

```python
def precision(tp, fp): return tp / (tp + fp) if (tp + fp) else 0.0
def recall(tp, fn):    return tp / (tp + fn) if (tp + fn) else 0.0
def f1(p, r):          return 2 * p * r / (p + r) if (p + r) else 0.0
```

Trade-off por estrategia de prompt (`08-evaluation-comparativa.md`):

- Conservative -> alta precision / baixo recall (CI/CD; evitar falso positivo).
- Aggressive -> baixo precision / alto recall (auditoria pre-release; nao deixar passar).
- Balanced -> melhor F1 (uso geral).

**Pairwise + LLM-as-Judge:** compara A vs B no mesmo dataset; o juiz (cujo prompt **nos
escrevemos**) decide o vencedor e justifica. Serve para medir objetivamente a evolucao v1 -> v2.

Observacao do projeto: o `metrics.py` calcula F1 derivando precision e recall do proprio
LLM-as-Judge (nao por contagem TP/FP/FN). E uma adaptacao valida da definicao do curso para um
caso onde nao ha rotulo de classe explicito.

---

## 7. Interpretando notas baixas e iterando o prompt (casos degradados)

Esta e a parte mais aplicavel. O instrutor degrada **so o prompt** (mantendo dataset e evaluators)
para isolar a causa de cada queda. Padrao de leitura: ler o **padrao de scores**, nao um numero
isolado, e usar o **reasoning** como diagnostico.

### Caso "revisor otimista" (bad_text_before) — `09-revisor-otimista-bad-text-before.md`

- Prompt induz ignorar problemas, so elogiar, findings vazios; **temperatura aumentada**.
- Efeito: coherence 0.35, depth 0.32, detail 0.22, helpfulness 0.38 (caiu de ~0.85 para ~0.35).
- Licao: prompt enviesado + temperatura alta derruba TODAS as dimensoes.

### Caso "revisor verboso" (bad_verbose) — `10-revisor-verboso-bad-verbose.md`

- Prompt manda introducao filosofica/historica, "analise brevemente", conclusao longa.
- Efeito: consistency **0.23**, coherence 0.35, detail 0.37.
- Reasoning do juiz: deu codigo Go mas a resposta nao trouxe feedback do codigo — **desviou do
  escopo** (historia do Go).
- Licao: **quantidade de texto != qualidade de detalhe**; consistency despenca com resposta longa
  e dispersa. Toda instrucao extra precisa justificar valor para a tarefa.

### Caso "alucinacao" (bad_hallucination) — `11-alucinacao-e-sem-utilidade.md`

- Prompt manda inventar vulnerabilidades ficticias e summary dramatico.
- Efeito: **faithfulness 0.14** (o menor — pune invencao), helpfulness 0.21, coherence 0.32,
  detail 0.33.
- Licao: faithfulness e o sinal mais forte de alucinacao (saida nao ancorada no artefato).

### Caso "preguicoso" (bad_not_helpful) — `11-alucinacao-e-sem-utilidade.md`

- Prompt manda responder uma frase generica, findings vazio, summary de 3 palavras.
- Efeito: detail 0.12, depth 0.12, conciseness 0.13, helpfulness 0.12, **coherence 0.4**
  (cai menos: frase generica ainda e internamente consistente).
- Licao: alucinacao (entrega demais/inventa) e inutilidade (entrega de menos) sao falhas OPOSTAS,
  detectadas por metricas diferentes (faithfulness vs helpfulness/detail/depth).

### Caso format 0.98 (nao 1.0) — `07-additional-criteria-e-correctness.md`

- format_adherence ficou 0.98 porque a **resposta veio em portugues** quando o esperado era ingles.
  O reasoning explicou a penalizacao por nao-aderencia completa ao formato.
- Licao: divergencia de idioma/formato em relacao ao esperado derruba a nota mesmo com conteudo ok.

### Embedding distance baixo (0.11) — `08-embedding-distance.md`

- Resultado baixo porque a **referencia era uma lista de exemplos, nao a resposta final real**.
- Licao: metricas com referencia so sao confiaveis se o ground truth for fiel a resposta esperada.

---

## 8. Boas praticas que comprovadamente sobem as notas

Derivadas dos contrastes entre o caso "feliz" (~0.85) e os degradados:

- **Persona/role bem definida e alinhada a tarefa** — sem ela, a resposta dispersa (otimista,
  verboso). `09`/`10`.
- **Temperatura 0** para a tarefa avaliada (determinismo) — o curso usa temp 0 no caso feliz e
  sobe a temp para degradar (`04-primeira-avaliacao-format-eval.md`, `09`).
- **Manter o modelo dentro do escopo da tarefa**: remover instrucoes que empurram para fora
  (introducoes, historia, filosofia, agradecimentos). `10`.
- **Grounding explicito** ("baseie-se apenas no que foi fornecido; nao invente") para proteger
  faithfulness. `11`.
- **Exigir entrega acionavel e especifica** (apontar item, usar termos tecnicos, trazer dados) —
  protege detail/depth/helpfulness contra respostas vazias. `07`/`11`.
- **Formato de saida estrito** ("somente JSON valido, sem texto antes/depois, sem Markdown") —
  protege format_adherence/precision/clarity. `07`.
- **Aderencia ao idioma/formato esperado** (se o ground truth esta em pt-BR, responder em pt-BR).
  `07`.
- **Saida concisa e direta** (sem floreio) — protege conciseness/consistency. `10`.

---

## 9. Pegadinhas e erros comuns

- **Texto antes/depois da resposta estruturada derruba format/precision/clarity.** O parser
  `extract_json_from_response` do projeto tolera isso, mas o **juiz penaliza** mesmo assim — o
  curso mostrou format 0.98 so por desvio. (`07-additional-criteria-e-correctness.md`,
  `09-revisor-otimista...` titulo "bad text before")
- **Verbosidade nao compensa ausencia de analise** — consistency despenca (0.23). `10`.
- **Resposta no idioma errado** penaliza formato mesmo com conteudo correto. `07`.
- **Referencia fraca** (lista de exemplos no lugar da resposta real) gera score baixo enganoso em
  metricas comparativas. `08-embedding-distance.md`.
- **Mais referencia/contexto nem sempre ajuda** — pode induzir o juiz sem garantir qualidade.
  `05-evaluators-binarios.md`.
- **Ler nota isolada** em vez do padrao de metricas + reasoning leva a diagnostico errado. `11`.
- **Dataset pequeno demais ou pouco expressivo** invalida a avaliacao; mas grande demais estoura
  quota. Equilibrar. `02-datasets.md`.

---

## 10. Prompt como software: YAML, contrato e testes automatizados

Fonte: `05-Gerenciamento.../07-visao-geral-com-prompt-yaml.md`,
`08-executando-testes-automatizados.md`, `13-entendendo-langsmith.md`, `RESUMO-SECAO.md`.

- **prompt.yaml** com campos `_type: prompt`, `id`, `version`, `input_variables` (contrato de
  entrada) e `template` (corpo parametrizado). YAML facilita inspecao/validacao/automacao.
- **prompt.tests.yaml** com `cases` (`name`, `inputs`, `expect_contains`). Verifica **compilacao /
  integridade de contrato**, NAO qualidade semantica. Camadas: sintaxe YAML; caminhos do registry
  existem; campos obrigatorios; **consistencia variavel declarada <-> usada no template**; render
  - `expect_contains`.
- **Regra do dia zero:** organizar testes de prompt desde o inicio, senao perde-se o controle
  conforme o acervo cresce. `08-executando-testes-automatizados.md`.
- **LangSmith:** observabilidade + avaliacao (tracing, custos, gestao de prompts). API key via env
  (`LANGSMITH_API_KEY`), plano gratuito com rate limit. `13-entendendo-langsmith.md`.

---

## Recomendacoes acionaveis para o bug_to_user_story_v2

Ajustes concretos no prompt e no fluxo, derivados do material, para maximizar a chance de bater

> = 0.9 em Helpfulness, Correctness, F1-Score, Clarity e Precision.

1. **Role + persona explicita e estavel** (Role Prompting): "Voce e um Product Owner senior que
   converte relatos de bug em User Stories ageis." Persona alinhada a tarefa evita dispersao que
   derrubou os casos otimista/verboso (Helpfulness, Clarity). Fonte: `09`, `10`.

2. **Saida estritamente estruturada e nada alem dela.** Instruir: "Responda APENAS com a User
   Story e os Criterios de Aceitacao; sem texto introdutorio, sem comentarios, sem Markdown extra,
   sem despedidas." Texto antes/depois derruba Precision e Clarity. Fonte: `07`, `09`.

3. **Grounding anti-alucinacao** (protege Correctness/Precision): "Baseie-se SOMENTE nas
   informacoes do relato de bug. NAO invente funcionalidades, IDs, telas ou regras que nao foram
   mencionadas." Foi exatamente o que levou faithfulness a 0.14 no caso de alucinacao. Fonte: `11`.

4. **Aderencia ao idioma e ao formato da referencia.** O dataset esta em pt-BR e usa o template
   "Como um... eu quero... para que..." + "Criterios de Aceitacao" em Given-When-Then (Dado/
   Quando/Entao). Forcar esse formato exato no prompt; divergencia de idioma/formato custou 0.02
   so por isso no curso. Fonte: `07`, dataset `bug_to_user_story.jsonl`.

5. **Few-shot calibrado por complexidade.** Incluir 2-3 exemplos cobrindo os splits do dataset
   (`simple`, `medium`, `complex`), mostrando o nivel de detalhe esperado em cada um — bugs simples
   sem excesso, complexos com contexto tecnico. Alinha com a metrica Completeness e evita tanto o
   "preguicoso" quanto o "verboso". Fonte: `02-datasets.md`, `metrics.py` (completeness),
   `10`/`11`.

6. **Chain of Thought interno, nao exposto.** Pedir raciocinio passo a passo para extrair
   persona, acao e beneficio, mas instruir que o raciocinio NAO apareca na saida final (so a User
   Story). Mantem Clarity/Precision altos sem perder a qualidade do CoT. Fonte: `09` (texto extra
   penaliza), `10`.

7. **Exigir criterios de aceitacao especificos e testaveis** (3-7 itens, Given-When-Then,
   mensuraveis, sem "deve funcionar bem"). Protege Helpfulness e o Acceptance Criteria Score; o
   curso mostrou que respostas vagas/vazias afundam detail/depth/helpfulness (~0.12). Fonte: `11`,
   `metrics.py` (acceptance_criteria).

8. **Concisao com valor.** Cada frase deve agregar a tarefa; remover floreio, historia e
   meta-comentarios. Verbosidade derrubou consistency a 0.23 sem ganhar detail. Fonte: `10`.

9. **Temperatura 0 (ou bem baixa) na geracao avaliada** para determinismo e reprodutibilidade da
   avaliacao; nunca subir temperatura no prompt sob avaliacao. Fonte: `04`, `09`.

10. **Fluxo de iteracao guiado pelo reasoning, nao pela nota.** Para cada metrica < 0.9, abrir o
    `reasoning` do LLM-as-Judge no(s) exemplo(s) reprovado(s), identificar a causa (idioma, texto
    extra, omissao, invencao, vagueza) e corrigir a instrucao especifica do prompt; depois
    re-avaliar (idealmente pairwise v1 vs v2 para confirmar ganho objetivo). Validar tambem o
    contrato do prompt com testes de compilacao (variavel `{bug_report}` declarada e usada) antes
    de cada rodada. Fonte: `07`, `11`, `12`, `08-evaluation-comparativa.md`, `05/08-testes`.
