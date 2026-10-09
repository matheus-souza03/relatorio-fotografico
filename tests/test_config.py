import datetime as dt

import pytest

from relatorio.config import ErroConfiguracao, carregar


def escrever(tmp_path, relatorio: str, sem_expediente: str = "", codificacao: str = "utf-8"):
    caminho = tmp_path / "configuracao.ini"
    caminho.write_bytes(
        f"# configuração\n[relatorio]\n{relatorio}\n[dias_sem_expediente]\n{sem_expediente}\n".encode(codificacao)
    )
    return caminho


def test_configuracao_completa(tmp_path):
    cfg = carregar(
        escrever(
            tmp_path,
            "data_inicial = 27/09/2026\ndata_final = 26/10/2026\nnome_arquivo = RFM57.docx",
            "feriados_municipais = 12/01, 20/01\noutros_dias = 15/10/2026\ndias_com_expediente =",
        )
    )
    assert (cfg.data_inicial, cfg.data_final) == (dt.date(2026, 9, 27), dt.date(2026, 10, 26))
    assert cfg.nome_arquivo == "RFM57"
    assert cfg.feriados_municipais == {(12, 1), (20, 1)}
    assert cfg.outros_dias_sem_expediente == {dt.date(2026, 10, 15)}
    assert cfg.dias_com_expediente == set()


def test_nome_padrao_e_arquivo_salvo_pelo_bloco_de_notas_antigo(tmp_path):
    cfg = carregar(escrever(tmp_path, "data_inicial = 27/09/2026\ndata_final = 26/10/2026\nnome_arquivo =", codificacao="cp1252"))
    assert cfg.nome_arquivo == "Relatorio_Fotografico_27-09-2026_a_26-10-2026"


@pytest.mark.parametrize(
    "relatorio, mensagem",
    [
        ("data_inicial = 2026-09-27\ndata_final = 26/10/2026", "DD/MM/AAAA"),
        ("data_inicial = 27/10/2026\ndata_final = 26/09/2026", "anterior"),
        ("data_inicial = 27/09/2026\ndata_final = 26/10/2027", "mais de"),
    ],
)
def test_erros_de_preenchimento(tmp_path, relatorio, mensagem):
    with pytest.raises(ErroConfiguracao, match=mensagem):
        carregar(escrever(tmp_path, relatorio))
