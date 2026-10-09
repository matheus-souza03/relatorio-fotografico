import shutil
from pathlib import Path

import pytest

from tests.auxiliares import RAIZ_PROJETO


@pytest.fixture
def projeto(tmp_path: Path) -> Path:
    """Pasta de projeto temporária, com o modelo real e um período de 4 dias (sexta a segunda)."""
    (tmp_path / "entrada").mkdir()
    (tmp_path / "modelo").mkdir()
    shutil.copy(RAIZ_PROJETO / "modelo" / "modelo_dia.docx", tmp_path / "modelo" / "modelo_dia.docx")
    (tmp_path / "configuracao.ini").write_text(
        "[relatorio]\ndata_inicial = 03/07/2026\ndata_final = 06/07/2026\nnome_arquivo = TESTE\n"
        "[dias_sem_expediente]\nferiados_municipais = 12/01\noutros_dias =\ndias_com_expediente =\n",
        encoding="utf-8",
    )
    return tmp_path
