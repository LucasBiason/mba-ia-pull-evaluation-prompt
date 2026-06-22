"""
Script para fazer pull de prompts do LangSmith Prompt Hub.

Este script:
1. Conecta ao LangSmith usando credenciais do .env
2. Faz pull do prompt de baixa qualidade do Hub (leonanluppi/bug_to_user_story_v1)
3. Salva localmente em prompts/bug_to_user_story_v1.yml

Usa a serializacao nativa do LangChain para extrair as partes do prompt.
"""

import sys
from langchain import hub
from dotenv import load_dotenv

from utils import save_yaml, check_env_vars, print_section_header

load_dotenv()

# Prompt de baixa qualidade publicado pelo Full Cycle no LangSmith Hub.
SOURCE_PROMPT = "leonanluppi/bug_to_user_story_v1"
OUTPUT_PATH = "prompts/bug_to_user_story_v1.yml"


def extract_prompt_parts(prompt) -> dict:
    """
    Extrai system_prompt e user_prompt de um objeto de prompt do LangChain.

    Lida com dois formatos possiveis retornados pelo Hub:
    - ChatPromptTemplate: lista de mensagens (system / human)
    - PromptTemplate: template unico de string

    Args:
        prompt: Objeto de prompt retornado por hub.pull()

    Returns:
        Dict com as chaves system_prompt e user_prompt
    """
    system_prompt = ""
    user_prompt = ""

    messages = getattr(prompt, "messages", None)

    if messages:
        # Formato de chat: percorre as mensagens e classifica por papel.
        for message in messages:
            role = type(message).__name__.lower()

            if hasattr(message, "prompt") and hasattr(message.prompt, "template"):
                template = message.prompt.template
            elif hasattr(message, "content"):
                template = message.content
            else:
                template = str(message)

            if "system" in role:
                system_prompt = template
            elif "human" in role or "user" in role:
                user_prompt = template
    else:
        # Formato de template unico (PromptTemplate).
        system_prompt = getattr(prompt, "template", str(prompt))

    return {
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
    }


def pull_prompts_from_langsmith() -> bool:
    """
    Faz pull do prompt do LangSmith Hub e salva localmente em YAML.

    Returns:
        True se sucesso, False caso contrario
    """
    print_section_header("PULL DO PROMPT DO LANGSMITH HUB")

    if not check_env_vars(["LANGSMITH_API_KEY"]):
        return False

    print(f"Puxando prompt: {SOURCE_PROMPT}")

    try:
        prompt = hub.pull(SOURCE_PROMPT)
    except Exception as e:
        print(f"\n❌ Erro ao fazer pull do prompt '{SOURCE_PROMPT}': {e}")
        print("\nVerifique:")
        print("- LANGSMITH_API_KEY esta configurada corretamente no .env")
        print("- Voce tem conexao com a internet")
        return False

    print("   ✓ Prompt carregado com sucesso")

    parts = extract_prompt_parts(prompt)

    metadata = getattr(prompt, "metadata", None) or {}

    prompt_data = {
        "bug_to_user_story_v1": {
            "description": "Prompt de baixa qualidade puxado do LangSmith Hub para otimizacao",
            "system_prompt": parts["system_prompt"],
            "user_prompt": parts["user_prompt"],
            "version": "v1",
            "source": SOURCE_PROMPT,
            "tags": ["bug-analysis", "user-story", "product-management"],
            "hub_commit": metadata.get("lc_hub_commit_hash", ""),
        }
    }

    if save_yaml(prompt_data, OUTPUT_PATH):
        print(f"   ✓ Prompt salvo em: {OUTPUT_PATH}")
        return True

    print(f"   ❌ Falha ao salvar o prompt em: {OUTPUT_PATH}")
    return False


def main() -> int:
    """Funcao principal."""
    success = pull_prompts_from_langsmith()

    if success:
        print("\n✅ Pull concluido. Proximo passo:")
        print("   Otimize o prompt em prompts/bug_to_user_story_v2.yml")
        return 0

    print("\n❌ Pull falhou. Corrija os erros acima e tente novamente.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
