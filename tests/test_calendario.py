import datetime as dt

from relatorio.calendario import montar_calendario


def motivos(inicio, fim, **kwargs):
    return {dia.data: dia.motivo_sem_expediente for dia in montar_calendario(inicio, fim, **kwargs)}


def test_texto_da_data():
    (dia,) = montar_calendario(dt.date(2026, 6, 29), dt.date(2026, 6, 29))
    assert dia.texto == "29/06/2026 (segunda-feira)"
    assert dia.tem_expediente


def test_fins_de_semana():
    m = motivos(dt.date(2026, 6, 26), dt.date(2026, 6, 29))
    assert m[dt.date(2026, 6, 26)] is None
    assert m[dt.date(2026, 6, 27)] == "sábado"
    assert m[dt.date(2026, 6, 28)] == "domingo"
    assert m[dt.date(2026, 6, 29)] is None


def test_feriados_nacionais_e_estaduais():
    m = motivos(dt.date(2026, 4, 20), dt.date(2026, 4, 24))
    assert "Tiradentes" in m[dt.date(2026, 4, 21)]
    assert "São Jorge" in m[dt.date(2026, 4, 23)]  # feriado estadual do RJ
    m = motivos(dt.date(2026, 9, 7), dt.date(2026, 9, 7))
    assert "Independência" in m[dt.date(2026, 9, 7)]


def test_pontos_facultativos():
    # Páscoa de 2027: 28/03
    m = motivos(dt.date(2027, 2, 8), dt.date(2027, 2, 11))
    assert "Carnaval" in m[dt.date(2027, 2, 8)]
    assert "Carnaval" in m[dt.date(2027, 2, 9)]
    assert "Cinzas" in m[dt.date(2027, 2, 10)]
    assert m[dt.date(2027, 2, 11)] is None
    assert "Corpus Christi" in motivos(dt.date(2027, 5, 27), dt.date(2027, 5, 27))[dt.date(2027, 5, 27)]
    m = motivos(dt.date(2026, 12, 24), dt.date(2026, 12, 31))
    assert "Véspera de Natal" in m[dt.date(2026, 12, 24)]
    assert "Véspera de Ano-Novo" in m[dt.date(2026, 12, 31)]


def test_dia_do_servidor_tem_expediente():
    assert motivos(dt.date(2026, 10, 28), dt.date(2026, 10, 28))[dt.date(2026, 10, 28)] is None


def test_feriado_municipal_e_ajustes_da_configuracao():
    m = motivos(
        dt.date(2027, 1, 11),
        dt.date(2027, 1, 16),
        feriados_municipais={(12, 1)},
        outros_dias_sem_expediente={dt.date(2027, 1, 14)},
        dias_com_expediente={dt.date(2027, 1, 16)},
    )
    assert m[dt.date(2027, 1, 11)] is None
    assert m[dt.date(2027, 1, 12)] == "feriado municipal"
    assert m[dt.date(2027, 1, 14)] == "sem expediente (configuração)"
    assert m[dt.date(2027, 1, 16)] is None  # sábado trabalhado
