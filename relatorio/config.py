"""Leitura do arquivo configuracao.ini."""

from __future__ import annotations

import configparser
import datetime as dt
import re
from dataclasses import dataclass
from pathlib import Path

FORMATO_DATA = "%d/%m/%Y"
MAXIMO_DIAS_NO_PERIODO = 62
CARACTERES_PROIBIDOS_EM_NOME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


class ErroConfiguracao(Exception):
    """Problema no configuracao.ini; a mensagem é exibida ao usuário."""


@dataclass
class Configuracao:
    data_inicial: dt.date
    data_final: dt.date
    nome_arquivo: str
    feriados_municipais: set[tuple[int, int]]  # (dia, mês), repetem todo ano
    outros_dias_sem_expediente: set[dt.date]
    dias_com_expediente: set[dt.date]


def carregar(caminho: Path) -> Configuracao:
    if not caminho.exists():
        raise ErroConfiguracao(f"Arquivo de configuração não encontrado: {caminho}")

    parser = configparser.ConfigParser(interpolation=None)
    try:
        parser.read_string(_ler_texto(caminho), source=caminho.name)
    except configparser.Error as erro:
        raise ErroConfiguracao(f"O arquivo {caminho.name} está com o formato errado: {erro}") from erro

    relatorio = _secao(parser, "relatorio")
    sem_expediente = _secao(parser, "dias_sem_expediente")

    inicio = _data(relatorio.get("data_inicial", ""), "data_inicial")
    fim = _data(relatorio.get("data_final", ""), "data_final")
    if fim < inicio:
        raise ErroConfiguracao("A data_final não pode ser anterior à data_inicial.")
    if (fim - inicio).days + 1 > MAXIMO_DIAS_NO_PERIODO:
        raise ErroConfiguracao(
            f"O período de {inicio:%d/%m/%Y} a {fim:%d/%m/%Y} tem mais de {MAXIMO_DIAS_NO_PERIODO} dias. "
            "Confira as datas no arquivo de configuração."
        )

    nome = CARACTERES_PROIBIDOS_EM_NOME.sub("", relatorio.get("nome_arquivo", "")).strip(" .")
    if nome.lower().endswith(".docx"):
        nome = nome[:-5].strip()
    if not nome:
        nome = f"Relatorio_Fotografico_{inicio:%d-%m-%Y}_a_{fim:%d-%m-%Y}"

    return Configuracao(
        data_inicial=inicio,
        data_final=fim,
        nome_arquivo=nome,
        feriados_municipais=_lista_dia_mes(sem_expediente.get("feriados_municipais", ""), "feriados_municipais"),
        outros_dias_sem_expediente=_lista_datas(sem_expediente.get("outros_dias", ""), "outros_dias"),
        dias_com_expediente=_lista_datas(sem_expediente.get("dias_com_expediente", ""), "dias_com_expediente"),
    )


def _ler_texto(caminho: Path) -> str:
    """Lê o arquivo aceitando UTF-8 (com ou sem BOM) e o padrão antigo do Bloco de Notas."""
    dados = caminho.read_bytes()
    try:
        return dados.decode("utf-8-sig")
    except UnicodeDecodeError:
        return dados.decode("cp1252", errors="replace")


def _secao(parser: configparser.ConfigParser, nome: str) -> configparser.SectionProxy:
    if not parser.has_section(nome):
        raise ErroConfiguracao(f"A seção [{nome}] não foi encontrada no arquivo de configuração.")
    return parser[nome]


def _data(texto: str, campo: str) -> dt.date:
    try:
        return dt.datetime.strptime(texto.strip(), FORMATO_DATA).date()
    except ValueError:
        raise ErroConfiguracao(
            f'O campo "{campo}" deve estar no formato DD/MM/AAAA (encontrado: "{texto.strip()}").'
        ) from None


def _itens(texto: str) -> list[str]:
    return [item for item in re.split(r"[,;\s]+", texto) if item]


def _lista_datas(texto: str, campo: str) -> set[dt.date]:
    return {_data(item, campo) for item in _itens(texto)}


def _lista_dia_mes(texto: str, campo: str) -> set[tuple[int, int]]:
    dias = set()
    for item in _itens(texto):
        try:
            data = dt.datetime.strptime(f"{item}/2000", FORMATO_DATA)  # 2000 é bissexto: aceita 29/02
        except ValueError:
            raise ErroConfiguracao(f'O campo "{campo}" deve ter datas no formato DD/MM (encontrado: "{item}").') from None
        dias.add((data.day, data.month))
    return dias
