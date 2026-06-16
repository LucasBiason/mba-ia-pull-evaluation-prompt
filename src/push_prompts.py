"""
Script para fazer push de prompts otimizados ao LangSmith Prompt Hub.

Este script:
1. Le os prompts otimizados de prompts/bug_to_user_story_v2.yml
2. Valida os prompts
3. Faz push PUBLICO para o LangSmith Hub
4. Adiciona metadados (tags, descricao, tecnicas utilizadas)

SIMPLIFICADO: Codigo mais limpo e direto ao ponto.
"""

import os
import sys
from dotenv import load_dotenv
from langchain import hub
from langchain_core.prompts import ChatPromptTemplate

from utils import load_yaml, check_env_vars, print_section_header

load_dotenv()

PROMPT_KEY = "bug_to_user_story_v2"
PROMPT_PATH = "prompts/bug_to_user_story_v2.yml"


def validate_prompt(prompt_data: dict) -> tuple[bool, list]:
    """
    Valida estrutura basica de um prompt (versao simplificada).

    Garante que os campos exigidos existem, que nao restam TODOs e que pelo
    menos 2 tecnicas de prompt engineering foram declaradas.

    Args:
        prompt_data: Dados do prompt (dict interno do YAML)

    Returns:
        (is_valid, errors) - Tupla com status e lista de erros
    """
    errors = []

    for field in ("description", "system_prompt", "user_prompt", "version"):
        if not str(prompt_data.get(field, "")).strip():
            errors.append(f"Campo obrigatorio ausente ou vazio: {field}")

    system_prompt = str(prompt_data.get("system_prompt", ""))
    if "TODO" in system_prompt or "[TODO]" in system_prompt:
        errors.append("system_prompt ainda contem TODO")

    if "{bug_report}" not in str(prompt_data.get("user_prompt", "")):
        errors.append("user_prompt deve conter a variavel {bug_report}")

    techniques = prompt_data.get("techniques_applied", []) or []
    if len(techniques) < 2:
        errors.append(
            f"Minimo de 2 tecnicas requeridas, encontradas: {len(techniques)}"
        )

    return (len(errors) == 0, errors)


def push_prompt_to_langsmith(
    prompt_name: str, prompt_data: dict, is_public: bool = True
) -> bool:
    """
    Faz push do prompt otimizado para o LangSmith Hub.

    Publica como PUBLICO quando ha um handle definido (USERNAME_LANGSMITH_HUB
    real). Sem handle (owner "-"), o LangSmith nao permite prompt publico, entao
    publica como PRIVADO no proprio workspace (suficiente para a avaliacao).

    Args:
        prompt_name: Nome completo do prompt (owner/nome)
        prompt_data: Dados do prompt
        is_public: Se True, publica como publico (requer handle)

    Returns:
        True se sucesso, False caso contrario
    """
    system_prompt = prompt_data["system_prompt"]
    user_prompt = prompt_data.get("user_prompt", "{bug_report}")

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("user", user_prompt),
        ]
    )

    techniques = ", ".join(prompt_data.get("techniques_applied", []))
    description = (
        f"{prompt_data.get('description', '').strip()} "
        f"Tecnicas aplicadas: {techniques}."
    ).strip()

    try:
        url = hub.push(
            prompt_name,
            prompt,
            new_repo_is_public=is_public,
            new_repo_description=description,
            tags=prompt_data.get("tags", []),
        )
        visibilidade = "PUBLICO" if is_public else "PRIVADO"
        print(f"   ✓ Push realizado com sucesso ({visibilidade})")
        print(f"   ✓ URL: {url}")
        if not is_public:
            print("   ⚠️  Publicado como PRIVADO (sem handle no LangSmith).")
            print("      Para deixar publico: crie um handle na UI do LangSmith,")
            print(
                "      defina USERNAME_LANGSMITH_HUB=<seu_handle> e rode o push de novo."
            )
        return True

    except Exception as e:
        msg = str(e).lower()
        # Idempotencia: se o prompt ja existe identico, o LangSmith retorna 409
        # "Nothing to commit". Nao e erro — o prompt ja esta publicado.
        if "nothing to commit" in msg or "has not changed" in msg or "409" in msg:
            print(
                "   ✓ Prompt ja publicado e identico ao ultimo commit (nada a atualizar)."
            )
            print(f"   ✓ Disponivel como: {prompt_name}")
            return True

        print(f"\n❌ Erro ao fazer push do prompt '{prompt_name}': {e}")
        print("\nVerifique:")
        print("- LANGSMITH_API_KEY esta configurada corretamente no .env")
        print("- USERNAME_LANGSMITH_HUB corresponde ao seu usuario do LangSmith Hub")
        return False


def main() -> int:
    """Funcao principal."""
    print_section_header("PUSH DO PROMPT OTIMIZADO AO LANGSMITH HUB")

    if not check_env_vars(["LANGSMITH_API_KEY", "USERNAME_LANGSMITH_HUB"]):
        return 1

    username = os.getenv("USERNAME_LANGSMITH_HUB")

    data = load_yaml(PROMPT_PATH)
    if not data or PROMPT_KEY not in data:
        print(f"❌ Nao foi possivel carregar '{PROMPT_KEY}' de {PROMPT_PATH}")
        return 1

    prompt_data = data[PROMPT_KEY]

    is_valid, errors = validate_prompt(prompt_data)
    if not is_valid:
        print("❌ Validacao do prompt falhou:")
        for error in errors:
            print(f"   - {error}")
        return 1

    print("   ✓ Prompt validado")

    prompt_name = f"{username}/{PROMPT_KEY}"
    # Sem handle (USERNAME == "-") o LangSmith nao aceita prompt publico.
    is_public = username not in ("", "-")
    print(f"Publicando: {prompt_name} ({'publico' if is_public else 'privado'})")

    if push_prompt_to_langsmith(prompt_name, prompt_data, is_public):
        print("\n✅ Push concluido. Proximo passo:")
        print("   python src/evaluate.py")
        return 0

    print("\n❌ Push falhou. Corrija os erros acima e tente novamente.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
