"""
Avaliacao NATIVA no LangSmith (gera um Experiment = dashboard na UI).

Diferente do src/evaluate.py (que calcula localmente e imprime no terminal), este
script usa langsmith.evaluation.evaluate() para:
  1. Rodar o prompt v2 (pull do Hub) sobre o dataset 'prompt-evaluation-eval';
  2. Aplicar as 5 metricas como EVALUATORS (reaproveitando src/metrics.py);
  3. Registrar tudo como um EXPERIMENT no LangSmith -> visivel na aba "Experiments"
     do dataset, com nota por exemplo, agregados e comparacao entre experimentos.

NAO altera nenhum arquivo "pronto"; apenas consome metrics.py/utils.py.

Uso:
    python scripts/langsmith_eval.py                # avalia lucasbiason/bug_to_user_story_v2
    python scripts/langsmith_eval.py --prompt leonanluppi/bug_to_user_story_v1  # baseline v1
"""

import os
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Permite importar utils.py e metrics.py de src/
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from langchain import hub
from langsmith import Client
from langsmith.evaluation import evaluate

from utils import get_llm
from metrics import evaluate_f1_score, evaluate_clarity, evaluate_precision

load_dotenv()


def build_target(prompt_name: str):
    """Cria a funcao-alvo: recebe inputs do exemplo e devolve a user story gerada."""
    prompt = hub.pull(prompt_name)
    llm = get_llm(temperature=0)
    chain = prompt | llm

    def target(inputs: dict) -> dict:
        response = chain.invoke(inputs)
        return {"answer": getattr(response, "content", str(response))}

    return target


def _extract(run, example):
    inputs = example.inputs or {}
    outputs = example.outputs or {}
    question = inputs.get("bug_report", "")
    reference = outputs.get("reference", "")
    answer = (run.outputs or {}).get("answer", "")
    return question, answer, reference


def all_metrics(run, example):
    """Um unico evaluator que devolve as 5 metricas (3 base + 2 derivadas)."""
    question, answer, reference = _extract(run, example)

    f1 = evaluate_f1_score(question, answer, reference)["score"]
    clarity = evaluate_clarity(question, answer, reference)["score"]
    precision = evaluate_precision(question, answer, reference)["score"]
    helpfulness = round((clarity + precision) / 2, 4)
    correctness = round((f1 + precision) / 2, 4)

    return {
        "results": [
            {"key": "f1_score", "score": f1},
            {"key": "clarity", "score": clarity},
            {"key": "precision", "score": precision},
            {"key": "helpfulness", "score": helpfulness},
            {"key": "correctness", "score": correctness},
        ]
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    username = os.getenv("USERNAME_LANGSMITH_HUB", "-")
    parser.add_argument(
        "--prompt",
        default=f"{username}/bug_to_user_story_v2",
        help="Nome do prompt no Hub (owner/nome).",
    )
    args = parser.parse_args()

    project = os.getenv("LANGSMITH_PROJECT", "prompt-evaluation")
    dataset_name = f"{project}-eval"

    client = Client()
    datasets = [d for d in client.list_datasets(dataset_name=dataset_name)]
    if not datasets:
        print(
            f"❌ Dataset '{dataset_name}' nao existe. Rode src/evaluate.py uma vez para cria-lo."
        )
        return 1

    print(
        f"Avaliando '{args.prompt}' sobre o dataset '{dataset_name}' (Experiment no LangSmith)..."
    )

    results = evaluate(
        build_target(args.prompt),
        data=dataset_name,
        evaluators=[all_metrics],
        experiment_prefix=args.prompt.split("/")[-1],
        metadata={
            "prompt": args.prompt,
            "provider": os.getenv("LLM_PROVIDER", "google"),
        },
    )

    url = getattr(results, "_manager", None)
    print("\n✅ Experiment criado no LangSmith.")
    print(
        "   Abra: LangSmith -> Datasets -> "
        f"{dataset_name} -> aba Experiments (notas por exemplo + agregados)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
