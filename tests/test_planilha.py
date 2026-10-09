import datetime as dt
import os
import time

import pytest

from relatorio.planilha import ErroPlanilha, formatar_numero, limpar_endereco, localizar_planilha, ler_registros
from tests.auxiliares import criar_planilha, link


@pytest.mark.parametrize(
    "valor, esperado",
    [(14.0, "14"), (195, "195"), ("03", "3"), (" 1330 ", "1330"), ("s/n", "S/N"), ("S/N", "S/N"), ("Casa b", "Casa b"), (None, "")],
)
def test_formatar_numero(valor, esperado):
    assert formatar_numero(valor) == (esperado, None)


def test_numero_que_virou_data_volta_a_ser_numero():
    numero, aviso = formatar_numero(dt.datetime(1901, 8, 6))
    assert numero == "584"
    assert "584" in aviso


@pytest.mark.parametrize(
    "valor, esperado",
    [
        ("Rua Barão de vila franca,obs: praça Mário Moreira.", "Rua Barão de vila franca"),
        ("Estrada de palmeirinha ( casa rosa )", "Estrada de palmeirinha"),
        ("Estrada de morrinhos  ( sítio 3 irmãos  )", "Estrada de morrinhos"),
        ("  Avenida   atlântica ", "Avenida atlântica"),
        ("Rua Obstáculo", "Rua Obstáculo"),
        ("(fazenda)", "(fazenda)"),
        (None, ""),
    ],
)
def test_limpar_endereco(valor, esperado):
    assert limpar_endereco(valor) == esperado


def test_ler_registros_na_ordem_da_planilha(tmp_path):
    carimbo = dt.datetime(2026, 7, 1, 9, 30)
    caminho = criar_planilha(
        tmp_path / "p.xlsx",
        [
            [carimbo, "Rua A ", carimbo, f"{link('a1')}, {link('a2')}", "Centro ", 14.0],
            [carimbo, "Rua B", carimbo, link("b1"), "Matias", "03"],
            [None, None, None, None, None, None],
            [carimbo, "Rua C", carimbo, f"{link('c1')}, {link('c2')}, {link('c3')}", "Caxias", "S/N"],
            [carimbo, None, carimbo, " ", None, None],
        ],
    )
    registros = ler_registros(caminho)

    assert [r.linha for r in registros] == [2, 3, 5, 6]
    a, b, c, vazio = registros
    assert (a.logradouro, a.bairro, a.numero) == ("Rua A", "Centro", "14")
    assert (a.link_antes, a.link_depois) == (link("a1"), link("a2"))
    assert (b.link_antes, b.link_depois, b.numero) == (link("b1"), None, "3")
    assert (c.link_antes, c.link_depois) == (link("c1"), link("c2"))
    assert "3 links" in c.avisos[0]
    assert (vazio.link_antes, vazio.link_depois) == (None, None)


def test_planilha_sem_as_colunas_esperadas(tmp_path):
    import openpyxl

    livro = openpyxl.Workbook()
    livro.active.append(["Nome", "Telefone"])
    livro.save(tmp_path / "outra.xlsx")
    with pytest.raises(ErroPlanilha, match="colunas esperadas"):
        ler_registros(tmp_path / "outra.xlsx")


def test_localizar_planilha_usa_a_mais_recente(tmp_path):
    antiga = criar_planilha(tmp_path / "antiga.xlsx", [])
    nova = criar_planilha(tmp_path / "nova.xlsx", [])
    (tmp_path / "~$nova.xlsx").write_bytes(b"arquivo temporario do Excel")
    os.utime(antiga, (time.time() - 3600, time.time() - 3600))

    assert localizar_planilha(tmp_path) == (nova, [antiga])


def test_localizar_planilha_sem_arquivo(tmp_path):
    with pytest.raises(ErroPlanilha, match="Nenhuma planilha"):
        localizar_planilha(tmp_path)
