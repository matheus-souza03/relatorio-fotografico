"""Leitura da planilha de respostas do Google Forms (.xlsx)."""

from __future__ import annotations

import datetime as dt
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import openpyxl

# Nomes aceitos para cada coluna, já normalizados (minúsculas, sem acento e sem ":").
COLUNAS = {
    "carimbo": ("carimbo de data/hora",),
    "logradouro": ("logradouro",),
    "bairro": ("bairro",),
    "numero": ("no", "n", "numero", "num"),
    "fotos": ("fotos (antes e depois)", "fotos"),
}
COLUNAS_OBRIGATORIAS = ("logradouro", "bairro", "numero", "fotos")
LINHAS_PROCURANDO_CABECALHO = 10

RE_LINK = re.compile(r"https?://[^\s,;]+")
RE_OBSERVACAO = re.compile(r"[\s,;\-–]*\bobs\b.*$", re.IGNORECASE | re.DOTALL)
RE_PARENTESES = re.compile(r"\s*\([^)]*\)?")
RE_SEM_NUMERO = re.compile(r"s\s*/?\s*n[º°o.]?", re.IGNORECASE)
EPOCA_EXCEL = dt.datetime(1899, 12, 30)


class ErroPlanilha(Exception):
    """Problema que impede a leitura da planilha; a mensagem é exibida ao usuário."""


@dataclass
class Registro:
    """Uma linha da planilha: um serviço, com foto de antes, de depois e o endereço."""

    linha: int  # número da linha como aparece no Excel/Google Planilhas
    logradouro: str
    bairro: str
    numero: str
    link_antes: str | None
    link_depois: str | None
    avisos: list[str] = field(default_factory=list)


def localizar_planilha(pasta: Path) -> tuple[Path, list[Path]]:
    """Retorna a planilha .xlsx mais recente da pasta e a lista das outras encontradas."""
    candidatas = sorted(
        (p for p in pasta.glob("*.xlsx") if not p.name.startswith(("~$", "."))),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not candidatas:
        raise ErroPlanilha(f'Nenhuma planilha (.xlsx) foi encontrada na pasta "{pasta.name}".')
    return candidatas[0], candidatas[1:]


def ler_registros(caminho: Path) -> list[Registro]:
    """Lê os registros na ordem da planilha, ignorando linhas totalmente vazias."""
    try:
        livro = openpyxl.load_workbook(caminho, read_only=True, data_only=True)
    except Exception as erro:
        raise ErroPlanilha(f'Não foi possível abrir a planilha "{caminho.name}": {erro}') from erro

    try:
        for aba in livro.worksheets:
            linhas = enumerate(aba.iter_rows(values_only=True), start=1)
            colunas = _localizar_cabecalho(linhas)
            if colunas is None:
                continue
            registros = []
            for numero_linha, valores in linhas:
                registro = _criar_registro(numero_linha, valores, colunas)
                if registro is not None:
                    registros.append(registro)
            return registros
    finally:
        livro.close()

    raise ErroPlanilha(
        f'A planilha "{caminho.name}" não tem as colunas esperadas: '
        '"Logradouro:", "Bairro:", "Nº" e "Fotos (antes e depois)".'
    )


def limpar_endereco(valor: object) -> str:
    """Remove espaços extras e observações, como faz o Gledson ao montar o relatório à mão.

    Ex.: "Rua Barão de vila franca,obs: praça Mário Moreira." -> "Rua Barão de vila franca"
         "Estrada de palmeirinha ( casa rosa )"             -> "Estrada de palmeirinha"
    """
    original = _sem_espacos_extras(valor)
    texto = RE_PARENTESES.sub("", RE_OBSERVACAO.sub("", original)).strip(" ,;-–.")
    return texto or original


def formatar_numero(valor: object) -> tuple[str, str | None]:
    """Formata a coluna "Nº". Retorna (texto, aviso ou None)."""
    if valor is None:
        return "", None
    if isinstance(valor, (dt.datetime, dt.date)):
        # O Excel/Google às vezes converte o número digitado em data; a data guarda o número original.
        momento = valor if isinstance(valor, dt.datetime) else dt.datetime.combine(valor, dt.time())
        numero = str((momento - EPOCA_EXCEL).days)
        return numero, f'o Nº veio como data ({momento:%d/%m/%Y}); foi usado "{numero}". Confira.'
    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor)), None
    texto = _sem_espacos_extras(valor)
    if re.fullmatch(r"[0-9]+", texto):
        return str(int(texto)), None  # "03" -> "3"
    if RE_SEM_NUMERO.fullmatch(texto):
        return "S/N", None
    return texto, None


def extrair_links(valor: object) -> list[str]:
    return RE_LINK.findall(str(valor)) if valor is not None else []


def _localizar_cabecalho(linhas) -> dict[str, int] | None:
    for numero_linha, valores in linhas:
        colunas: dict[str, int] = {}
        for indice, valor in enumerate(valores):
            nome = _normalizar(valor)
            for chave, aceitos in COLUNAS.items():
                if nome in aceitos and chave not in colunas:
                    colunas[chave] = indice
        if all(chave in colunas for chave in COLUNAS_OBRIGATORIAS):
            return colunas
        if numero_linha >= LINHAS_PROCURANDO_CABECALHO:
            return None
    return None


def _criar_registro(numero_linha: int, valores: tuple, colunas: dict[str, int]) -> Registro | None:
    def valor(chave: str) -> object:
        indice = colunas.get(chave)
        if indice is None or indice >= len(valores):
            return None
        return valores[indice]

    if all(_vazio(valor(chave)) for chave in colunas):
        return None

    avisos = []
    links = extrair_links(valor("fotos"))
    if len(links) > 2:
        avisos.append(f"tem {len(links)} links de fotos; foram usados os dois primeiros.")
    numero, aviso_numero = formatar_numero(valor("numero"))
    if aviso_numero:
        avisos.append(aviso_numero)

    return Registro(
        linha=numero_linha,
        logradouro=limpar_endereco(valor("logradouro")),
        bairro=limpar_endereco(valor("bairro")),
        numero=numero,
        link_antes=links[0] if len(links) > 0 else None,
        link_depois=links[1] if len(links) > 1 else None,
        avisos=avisos,
    )


def _normalizar(valor: object) -> str:
    if valor is None:
        return ""
    texto = unicodedata.normalize("NFKD", str(valor).replace("°", "o"))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return " ".join(texto.lower().split()).rstrip(" :")


def _sem_espacos_extras(valor: object) -> str:
    return " ".join(str(valor).split()) if valor is not None else ""


def _vazio(valor: object) -> bool:
    return valor is None or (isinstance(valor, str) and not valor.strip())
