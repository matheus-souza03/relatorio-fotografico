import datetime as dt

from relatorio.calendario import montar_calendario
from relatorio.distribuicao import distribuir
from relatorio.planilha import Registro


def registros(quantidade: int) -> list[Registro]:
    return [Registro(linha=n, logradouro=f"Rua {n}", bairro="", numero="", link_antes=None, link_depois=None) for n in range(2, 2 + quantidade)]


def linhas(dia):
    return [[r.linha if r else None for r in equipe] for equipe in dia.equipes]


def test_seis_por_dia_util_na_ordem_da_planilha():
    # sexta 03/07, sábado, domingo, segunda 06/07
    dias = montar_calendario(dt.date(2026, 7, 3), dt.date(2026, 7, 6))
    resultado, sobra = distribuir(dias, registros(12))

    assert linhas(resultado[0]) == [[2, 3, 4], [5, 6, 7]]
    assert linhas(resultado[1]) == [[None] * 3, [None] * 3]
    assert linhas(resultado[2]) == [[None] * 3, [None] * 3]
    assert linhas(resultado[3]) == [[8, 9, 10], [11, 12, 13]]
    assert sobra == []


def test_registros_que_sobram_ficam_para_o_proximo_relatorio():
    dias = montar_calendario(dt.date(2026, 7, 3), dt.date(2026, 7, 3))
    _, sobra = distribuir(dias, registros(8))
    assert [r.linha for r in sobra] == [8, 9]


def test_quando_os_registros_acabam_o_restante_fica_em_branco():
    dias = montar_calendario(dt.date(2026, 7, 2), dt.date(2026, 7, 3))
    resultado, sobra = distribuir(dias, registros(4))
    assert linhas(resultado[0]) == [[2, 3, 4], [5, None, None]]
    assert linhas(resultado[1]) == [[None] * 3, [None] * 3]
    assert sobra == []
