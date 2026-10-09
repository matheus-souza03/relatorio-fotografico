"""Montagem do .docx a partir do modelo de um dia (modelo/modelo_dia.docx).

O modelo tem as 3 páginas de um dia (Equipe 1, Equipe 2 e carga horária) com campos
entre chaves duplas, que o programa substitui em cada dia do relatório:

    {{DATA}}             data do dia, ex.: 29/06/2026 (segunda-feira)
    {{SEM_EXPEDIENTE}}   " SEM EXPEDIENTE" em fins de semana, feriados e pontos facultativos
    {{E1_P2_ANTES}}      foto de antes do ponto 2 da equipe 1 (idem para DEPOIS)
    {{E1_P2_ENDERECO}}   endereço do ponto 2 da equipe 1
"""

from __future__ import annotations

import copy
import datetime as dt
import re
from io import BytesIO
from pathlib import Path
from typing import Callable

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.oxml.shape import CT_Inline
from docx.shared import Pt, RGBColor
from docx.text.paragraph import Paragraph
from docx.text.run import Run

from .distribuicao import EQUIPES, PONTOS_POR_EQUIPE, DiaDoRelatorio
from .imagens import ErroFoto
from .planilha import Registro

RE_CAMPO = re.compile(r"\{\{([A-Z0-9_]+)\}\}")
RE_CAMPO_DO_PONTO = re.compile(r"E(\d)_P(\d)_(ANTES|DEPOIS|ENDERECO)")
CAMPOS_DE_TEXTO = ("DATA", "SEM_EXPEDIENTE")
TEXTO_SEM_EXPEDIENTE = " SEM EXPEDIENTE"

EMU_POR_TWIP = 635
MARGEM_INTERNA_CELULA_TWIPS = 108  # margem esquerda/direita padrão do estilo "Tabela com grade"
FOLGA_TWIPS = 60
ALTURA_PADRAO_FOTO_TWIPS = 2956  # usada se a linha das fotos não tiver altura definida no modelo
PRIMEIRO_ID_DE_FORMA = 10_000  # acima dos IDs das imagens do cabeçalho e rodapé
COR_ERRO = RGBColor(0xC0, 0x00, 0x00)
TAMANHO_ERRO = Pt(8)

ObterFoto = Callable[[Registro, str], "bytes | ErroFoto"]


class ErroModelo(Exception):
    """Problema no arquivo de modelo; a mensagem é exibida ao usuário."""


class Documento:
    def __init__(self, caminho_modelo: Path):
        try:
            self._doc = Document(str(caminho_modelo))
        except Exception as erro:
            raise ErroModelo(f'Não foi possível abrir o modelo "{caminho_modelo}": {erro}') from erro

        corpo = self._doc.element.body
        self._sectpr_final = corpo.find(qn("w:sectPr"))
        self._prototipo = [el for el in corpo if el is not self._sectpr_final]
        for elemento in self._prototipo:
            corpo.remove(elemento)
        if self._prototipo and self._prototipo[-1].tag != qn("w:p"):
            self._prototipo.append(OxmlElement("w:p"))  # a quebra de seção precisa de um parágrafo

        self._caixas_de_foto = self._validar_modelo()
        self._proximo_id = PRIMEIRO_ID_DE_FORMA
        self._ultimo_paragrafo = None

    def adicionar_dia(self, dia: DiaDoRelatorio, obter_foto: ObterFoto) -> None:
        bloco = [copy.deepcopy(elemento) for elemento in self._prototipo]
        textos = {
            "DATA": dia.dia.texto,
            "SEM_EXPEDIENTE": "" if dia.dia.tem_expediente else TEXTO_SEM_EXPEDIENTE,
        }
        for elemento in bloco:
            for paragrafo in list(elemento.iter(qn("w:p"))):
                self._preencher(paragrafo, textos, dia, obter_foto)

        # Cada dia termina com uma quebra de seção: a página de carga horária é retrato
        # e a página seguinte (Equipe 1 do próximo dia) é paisagem.
        self._ultimo_paragrafo = bloco[-1]
        self._ultimo_paragrafo.set_sectPr(copy.deepcopy(self._sectpr_final))
        for elemento in bloco:
            self._sectpr_final.addprevious(elemento)

    def salvar(self, caminho: Path) -> None:
        if self._ultimo_paragrafo is not None:  # o último dia usa a seção final do documento
            self._ultimo_paragrafo.pPr._remove_sectPr()
        agora = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
        propriedades = self._doc.core_properties
        propriedades.created = agora
        propriedades.modified = agora
        propriedades.revision = 1
        self._doc.save(str(caminho))

    def _validar_modelo(self) -> dict[str, tuple[int, int]]:
        """Confere os campos do modelo e mede o espaço disponível para cada foto (EMU)."""
        paragrafos_por_campo: dict[str, list] = {}
        for elemento in self._prototipo:
            for paragrafo in elemento.iter(qn("w:p")):
                for campo in RE_CAMPO.findall(_texto(paragrafo)):
                    paragrafos_por_campo.setdefault(campo, []).append(paragrafo)

        campos_dos_pontos = {
            f"E{equipe}_P{ponto}_{tipo}"
            for equipe in range(1, EQUIPES + 1)
            for ponto in range(1, PONTOS_POR_EQUIPE + 1)
            for tipo in ("ANTES", "DEPOIS", "ENDERECO")
        }
        faltando = sorted(({"DATA"} | campos_dos_pontos) - paragrafos_por_campo.keys())
        if faltando:
            raise ErroModelo("O modelo está sem os campos: " + ", ".join(f"{{{{{c}}}}}" for c in faltando))
        desconhecidos = sorted(paragrafos_por_campo.keys() - campos_dos_pontos - set(CAMPOS_DE_TEXTO))
        if desconhecidos:
            raise ErroModelo("O modelo tem campos desconhecidos: " + ", ".join(f"{{{{{c}}}}}" for c in desconhecidos))

        return {
            campo: _espaco_da_celula(paragrafos[0])
            for campo, paragrafos in paragrafos_por_campo.items()
            if campo.endswith(("_ANTES", "_DEPOIS"))
        }

    def _preencher(self, paragrafo, textos: dict[str, str], dia: DiaDoRelatorio, obter_foto: ObterFoto) -> None:
        campos = RE_CAMPO.findall(_texto(paragrafo))
        for campo in campos:
            ponto = RE_CAMPO_DO_PONTO.fullmatch(campo)
            if ponto:
                registro = dia.equipes[int(ponto[1]) - 1][int(ponto[2]) - 1]
                self._preencher_ponto(paragrafo, campo, ponto[3], registro, obter_foto)
                return  # o parágrafo inteiro foi substituído
        for campo in campos:
            _substituir_texto(paragrafo, f"{{{{{campo}}}}}", textos.get(campo, ""))

    def _preencher_ponto(self, paragrafo, campo: str, tipo: str, registro: Registro | None, obter_foto: ObterFoto) -> None:
        formatacao = _formatacao_do_campo(paragrafo)
        _esvaziar(paragrafo)
        if registro is None:
            return

        if tipo == "ENDERECO":
            # Mesmo formato do relatório feito à mão: logradouro <tab> bairro <tab> nº
            partes = [parte for parte in (registro.logradouro, registro.bairro, registro.numero) if parte]
            for indice, parte in enumerate(partes):
                run = _novo_run(paragrafo, formatacao)
                if indice:
                    run.append(OxmlElement("w:tab"))
                _adicionar_texto(run, parte)
            return

        formato = Paragraph(paragrafo, None).paragraph_format
        formato.alignment = WD_ALIGN_PARAGRAPH.CENTER
        formato.space_before = 0
        formato.space_after = 0
        formato.line_spacing = 1.0

        foto = obter_foto(registro, tipo)
        if isinstance(foto, ErroFoto):
            self._escrever_erro(paragrafo, formatacao, tipo, registro, str(foto))
        else:
            self._inserir_foto(paragrafo, formatacao, foto, *self._caixas_de_foto[campo])

    def _inserir_foto(self, paragrafo, formatacao, foto: bytes, largura_maxima: int, altura_maxima: int) -> None:
        """Insere a foto no maior tamanho que cabe no espaço, sem distorcer."""
        rid, imagem = self._doc.part.get_or_add_image(BytesIO(foto))
        escala = min(largura_maxima / imagem.px_width, altura_maxima / imagem.px_height)
        self._proximo_id += 1
        inline = CT_Inline.new_pic_inline(
            self._proximo_id,
            rid,
            imagem.filename,
            int(imagem.px_width * escala),
            int(imagem.px_height * escala),
        )
        desenho = OxmlElement("w:drawing")
        desenho.append(inline)
        _novo_run(paragrafo, formatacao).append(desenho)

    @staticmethod
    def _escrever_erro(paragrafo, formatacao, tipo: str, registro: Registro, motivo: str) -> None:
        linhas = [f"ERRO – FOTO {tipo}", f"Linha {registro.linha} da planilha", motivo, "Inserir manualmente."]
        for indice, linha in enumerate(linhas):
            run = _novo_run(paragrafo, formatacao)
            if indice:
                run.append(OxmlElement("w:br"))
            _adicionar_texto(run, linha)
            fonte = Run(run, None).font
            fonte.bold = indice == 0
            fonte.color.rgb = COR_ERRO
            fonte.size = TAMANHO_ERRO


def _texto(paragrafo) -> str:
    return "".join(no.text or "" for no in paragrafo.iter(qn("w:t")))


def _substituir_texto(paragrafo, alvo: str, novo: str) -> None:
    """Substitui `alvo` mesmo que o Word tenha dividido o texto em vários pedaços (runs)."""
    while True:
        nos = list(paragrafo.iter(qn("w:t")))
        textos = [no.text or "" for no in nos]
        inicio = "".join(textos).find(alvo)
        if inicio < 0:
            return
        fim = inicio + len(alvo)
        posicao = 0
        primeiro = True
        for no, texto in zip(nos, textos):
            inicio_no, posicao = posicao, posicao + len(texto)
            if posicao <= inicio or inicio_no >= fim:
                continue
            antes = texto[: max(0, inicio - inicio_no)]
            depois = texto[max(0, fim - inicio_no) :]
            no.text = antes + (novo if primeiro else "") + depois
            no.set(qn("xml:space"), "preserve")
            primeiro = False


def _formatacao_do_campo(paragrafo):
    """Formatação (w:rPr) do trecho onde está o campo, para o texto novo sair igual."""
    for no in paragrafo.iter(qn("w:t")):
        if "{{" in (no.text or ""):
            return no.getparent().find(qn("w:rPr"))
    return None


def _esvaziar(paragrafo) -> None:
    for filho in list(paragrafo):
        if filho.tag != qn("w:pPr"):
            paragrafo.remove(filho)


def _novo_run(paragrafo, formatacao):
    run = OxmlElement("w:r")
    if formatacao is not None:
        run.append(copy.deepcopy(formatacao))
    paragrafo.append(run)
    return run


def _adicionar_texto(run, texto: str) -> None:
    no = OxmlElement("w:t")
    no.text = texto
    no.set(qn("xml:space"), "preserve")
    run.append(no)


def _espaco_da_celula(paragrafo) -> tuple[int, int]:
    """Largura e altura úteis (EMU) da célula de tabela onde está o parágrafo."""
    celula, linha, tabela = _ancestral(paragrafo, "w:tc"), _ancestral(paragrafo, "w:tr"), _ancestral(paragrafo, "w:tbl")
    if celula is None or linha is None or tabela is None:
        raise ErroModelo("Os campos de foto do modelo precisam ficar dentro de células de tabela.")

    larguras = [int(coluna.get(qn("w:w"))) for coluna in tabela.find(qn("w:tblGrid")).findall(qn("w:gridCol"))]
    propriedades_linha = linha.find(qn("w:trPr"))
    inicio = _valor_inteiro(propriedades_linha, "w:gridBefore", 0)
    for outra in linha.findall(qn("w:tc")):
        if outra is celula:
            break
        inicio += _valor_inteiro(outra.find(qn("w:tcPr")), "w:gridSpan", 1)
    colunas = _valor_inteiro(celula.find(qn("w:tcPr")), "w:gridSpan", 1)

    largura = sum(larguras[inicio : inicio + colunas]) - 2 * MARGEM_INTERNA_CELULA_TWIPS - FOLGA_TWIPS
    altura = _valor_inteiro(propriedades_linha, "w:trHeight", ALTURA_PADRAO_FOTO_TWIPS) - FOLGA_TWIPS
    return largura * EMU_POR_TWIP, altura * EMU_POR_TWIP


def _ancestral(elemento, tag: str):
    for pai in elemento.iterancestors(qn(tag)):
        return pai
    return None


def _valor_inteiro(propriedades, tag: str, padrao: int) -> int:
    if propriedades is None:
        return padrao
    filho = propriedades.find(qn(tag))
    return int(filho.get(qn("w:val"))) if filho is not None else padrao
