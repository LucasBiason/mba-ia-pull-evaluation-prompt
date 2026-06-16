"""
Testes automatizados para validacao de prompts.

Validam o prompt otimizado em prompts/bug_to_user_story_v2.yml contra os
requisitos do desafio: persona definida, formato exigido, exemplos few-shot,
ausencia de TODOs e no minimo 2 tecnicas declaradas.
"""

import pytest
import yaml
import sys
from pathlib import Path

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils import validate_prompt_structure

PROMPT_KEY = "bug_to_user_story_v2"
PROMPT_PATH = Path(__file__).parent.parent / "prompts" / f"{PROMPT_KEY}.yml"


def load_prompts(file_path):
    """Carrega prompts do arquivo YAML."""
    with open(file_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture
def prompt_data():
    """Retorna o dict interno do prompt otimizado (v2)."""
    data = load_prompts(PROMPT_PATH)
    assert data is not None, f"Nao foi possivel carregar {PROMPT_PATH}"
    assert PROMPT_KEY in data, f"Chave '{PROMPT_KEY}' ausente no YAML"
    return data[PROMPT_KEY]


class TestPrompts:
    def test_prompt_has_system_prompt(self, prompt_data):
        """Verifica se o campo 'system_prompt' existe e nao esta vazio."""
        assert "system_prompt" in prompt_data, "Campo 'system_prompt' ausente"
        assert prompt_data["system_prompt"].strip(), "system_prompt esta vazio"

    def test_prompt_has_role_definition(self, prompt_data):
        """Verifica se o prompt define uma persona (ex: 'Voce e um Product Manager')."""
        system_prompt = prompt_data["system_prompt"].lower()
        assert "voce e" in system_prompt or "você é" in system_prompt, (
            "Nao foi encontrada definicao de persona ('Voce e...')"
        )
        role_markers = [
            "product manager",
            "product owner",
            "especialista",
            "engenheiro",
        ]
        assert any(marker in system_prompt for marker in role_markers), (
            "Nenhum papel/persona reconhecido no system_prompt"
        )

    def test_prompt_mentions_format(self, prompt_data):
        """Verifica se o prompt exige formato Markdown ou User Story padrao."""
        system_prompt = prompt_data["system_prompt"].lower()
        format_markers = [
            "markdown",
            "como um",
            "criterios de aceitacao",
            "critérios de aceitação",
        ]
        assert any(marker in system_prompt for marker in format_markers), (
            "O prompt nao menciona o formato esperado (Markdown / User Story)"
        )

    def test_prompt_has_few_shot_examples(self, prompt_data):
        """Verifica se o prompt contem exemplos de entrada/saida (tecnica Few-shot)."""
        system_prompt = prompt_data["system_prompt"].lower()
        assert "exemplo" in system_prompt, "Nenhum exemplo encontrado no prompt"
        assert "entrada" in system_prompt and (
            "saida" in system_prompt or "saída" in system_prompt
        ), "Exemplos few-shot devem conter pares de Entrada/Saida"

    def test_prompt_no_todos(self, prompt_data):
        """Garante que nenhum '[TODO]' ficou no texto."""
        full_text = yaml.safe_dump(prompt_data, allow_unicode=True)
        assert "TODO" not in full_text, "Ainda ha TODO(s) no prompt"

    def test_minimum_techniques(self, prompt_data):
        """Verifica (via metadados do yaml) se pelo menos 2 tecnicas foram listadas."""
        techniques = prompt_data.get("techniques_applied", [])
        assert isinstance(techniques, list), "techniques_applied deve ser uma lista"
        assert len(techniques) >= 2, (
            f"Minimo de 2 tecnicas requeridas, encontradas: {len(techniques)}"
        )
        # Reforco usando o validador compartilhado do projeto.
        is_valid, errors = validate_prompt_structure(prompt_data)
        assert is_valid, f"validate_prompt_structure falhou: {errors}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
