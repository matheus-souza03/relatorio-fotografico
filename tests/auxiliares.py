"""Funções de apoio para os testes."""

import io
from pathlib import Path

import openpyxl
from PIL import Image

RAIZ_PROJETO = Path(__file__).resolve().parent.parent
CABECALHO = ["Carimbo de data/hora", "Logradouro:", "Coluna 2", "Fotos (antes e depois)", "Bairro:", "Nº"]


def link(id_arquivo: str) -> str:
    return f"https://drive.google.com/open?id={id_arquivo}"


def criar_planilha(caminho: Path, linhas: list[list]) -> Path:
    livro = openpyxl.Workbook()
    aba = livro.active
    aba.title = "Respostas ao formulário 1"
    aba.append(CABECALHO)
    for linha in linhas:
        aba.append(linha)
    livro.save(caminho)
    return caminho


def foto_jpeg(largura: int = 300, altura: int = 400, cor: str = "steelblue") -> bytes:
    saida = io.BytesIO()
    Image.new("RGB", (largura, altura), cor).save(saida, "JPEG")
    return saida.getvalue()
