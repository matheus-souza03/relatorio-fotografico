"""Cria modelo/modelo_dia.docx a partir de um relatório montado à mão (ex.: RFM54.docx).

Uso, na pasta do projeto:
    python ferramentas/criar_modelo.py documentos_exemplo/RFM54.docx

O modelo é o primeiro dia do relatório de origem (Equipe 1, Equipe 2 e carga horária),
sem fotos e sem horas, com os campos {{...}} que o gerador preenche (veja
relatorio/documento.py). Só é preciso rodar de novo para recriar o modelo a partir de
outro relatório; mudanças simples (nº do contrato, nomes) podem ser feitas direto no
modelo pelo Word, desde que os campos {{...}} sejam mantidos.
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, Twips
from docx.table import Table, _Cell
from docx.text.paragraph import Paragraph
from docx.text.run import Run

RAIZ = Path(__file__).resolve().parent.parent
DESTINO = RAIZ / "modelo" / "modelo_dia.docx"
ALTURA_LINHA_FOTOS = Twips(2956)  # ~5,2 cm, como no relatório original
TAMANHO_SEM_EXPEDIENTE = Pt(10)  # nas páginas das equipes, "SEM EXPEDIENTE" é menor que a data
MARCAS_DO_WORD = ("w:proofErr", "w:lastRenderedPageBreak", "w:bookmarkStart", "w:bookmarkEnd")
ATRIBUTOS_DO_WORD = (qn("w14:paraId"), qn("w14:textId"))


def criar_modelo(origem: Path, destino: Path) -> None:
    doc = Document(str(origem))
    corpo = doc.element.body
    sectpr_final = corpo.find(qn("w:sectPr"))
    elementos = [elemento for elemento in corpo if elemento is not sectpr_final]

    # O primeiro dia vai até a 2ª quebra de seção: paisagem (equipes) e retrato (carga horária).
    quebras = [indice for indice, elemento in enumerate(elementos) if _quebra_de_secao(elemento)]
    fim_equipes, fim_dia = quebras[0], quebras[1]
    for elemento in elementos[fim_dia + 1 :]:
        corpo.remove(elemento)
    equipes, carga_horaria = elementos[: fim_equipes + 1], elementos[fim_equipes + 1 : fim_dia + 1]

    # A seção final do documento passa a ser a da página de carga horária (com cabeçalho e rodapé).
    ultimo = carga_horaria[-1]
    corpo.replace(sectpr_final, copy.deepcopy(ultimo.pPr.sectPr))
    ultimo.pPr._remove_sectPr()

    for elemento in equipes + carga_horaria:
        _remover_marcas_do_word(elemento)

    _preparar_paginas_das_equipes(corpo, equipes)
    _preparar_carga_horaria(corpo, carga_horaria)
    _remover_relacoes_sem_uso(doc)

    doc.core_properties.title = "Relatório Fotográfico"
    doc.core_properties.last_modified_by = ""
    destino.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(destino))


def _preparar_paginas_das_equipes(corpo, elementos: list) -> None:
    datas = [el for el in elementos if el.tag == qn("w:p") and _texto(el).strip().upper().startswith("DATA")]
    tabelas = [el for el in elementos if el.tag == qn("w:tbl")]
    if len(datas) != 2 or len(tabelas) != 2:
        raise SystemExit("Formato inesperado: o 1º dia deveria ter 2 páginas de equipe (DATA + tabela de fotos).")

    for paragrafo in datas:
        _campo_data(paragrafo, TAMANHO_SEM_EXPEDIENTE)
    for equipe, tabela in enumerate(tabelas, start=1):
        _campos_da_tabela_de_fotos(tabela, equipe)

    # No original, a página da Equipe 2 começava porque linhas em branco empurravam o texto.
    # Aqui as linhas em branco saem e entra uma quebra de página explícita.
    for tabela in tabelas:
        seguinte = tabela.getnext()
        while seguinte is not None and seguinte.tag == qn("w:p") and _vazio(seguinte) and not _quebra_de_secao(seguinte):
            proximo = seguinte.getnext()
            corpo.remove(seguinte)
            seguinte = proximo
    titulo_equipe_2 = tabelas[0].getnext()
    Paragraph(titulo_equipe_2, None).paragraph_format.page_break_before = True


def _preparar_carga_horaria(corpo, elementos: list) -> None:
    tabelas = [el for el in elementos if el.tag == qn("w:tbl")]
    mao_de_obra = next(t for t in tabelas if _texto(t).strip().upper().startswith("DATA"))
    veiculos = tabelas[tabelas.index(mao_de_obra) + 1]

    _campo_data(next(mao_de_obra.iter(qn("w:p"))))
    for tabela in (mao_de_obra, veiculos):  # as horas são preenchidas à mão
        for linha in tabela.findall(qn("w:tr"))[2:]:
            for paragrafo in linha.findall(qn("w:tc"))[-1].iter(qn("w:p")):
                _esvaziar(paragrafo)

    # A página termina na última assinatura; o gerador põe a quebra de seção nesse parágrafo.
    while elementos[-1].tag == qn("w:p") and _vazio(elementos[-1]):
        corpo.remove(elementos.pop())


def _campo_data(paragrafo, tamanho_sem_expediente: Pt | None = None) -> None:
    """Troca "DATA: 27/06/2026 (sábado) SEM EXPEDIENTE" por "DATA: {{DATA}}{{SEM_EXPEDIENTE}}"."""
    runs = paragrafo.findall(qn("w:r"))
    formatacao_rotulo = runs[0].find(qn("w:rPr"))
    formatacao_valor = runs[1].find(qn("w:rPr")) if len(runs) > 1 else formatacao_rotulo
    _esvaziar(paragrafo)
    _novo_run(paragrafo, formatacao_rotulo, "DATA: ")
    _novo_run(paragrafo, formatacao_valor, "{{DATA}}")
    sem_expediente = _novo_run(paragrafo, formatacao_valor, "{{SEM_EXPEDIENTE}}")
    if tamanho_sem_expediente is not None:
        Run(sem_expediente, None).font.size = tamanho_sem_expediente


def _campos_da_tabela_de_fotos(tabela, equipe: int) -> None:
    cabecalho, fotos, enderecos = tabela.findall(qn("w:tr"))[:3]

    ponto = 0
    for celula_rotulo, celula_foto in zip(cabecalho.findall(qn("w:tc")), fotos.findall(qn("w:tc"))):
        rotulo = _texto(celula_rotulo).strip().upper()
        if rotulo == "ANTES":
            ponto += 1
        if rotulo in ("ANTES", "DEPOIS"):
            paragrafo = _campo_na_celula(celula_foto, f"E{equipe}_P{ponto}_{rotulo}")
            formato = Paragraph(paragrafo, None).paragraph_format
            formato.alignment = WD_ALIGN_PARAGRAPH.CENTER
            formato.space_before = formato.space_after = 0
            formato.line_spacing = 1.0
            _Cell(celula_foto, None).vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER

    ponto = 0
    for celula in enderecos.findall(qn("w:tc")):  # o endereço ocupa as colunas ANTES + DEPOIS
        if celula.find(qn("w:tcPr") + "/" + qn("w:gridSpan")) is not None:
            ponto += 1
            _campo_na_celula(celula, f"E{equipe}_P{ponto}_ENDERECO")

    fotos.trHeight_val = ALTURA_LINHA_FOTOS
    Table(tabela, None).autofit = False  # colunas fixas: a foto nunca alarga a tabela


def _campo_na_celula(celula, campo: str):
    paragrafos = celula.findall(qn("w:p"))
    for extra in paragrafos[1:]:
        celula.remove(extra)
    paragrafo = paragrafos[0]
    run = paragrafo.find(qn("w:r"))
    formatacao = run.find(qn("w:rPr")) if run is not None else paragrafo.find(qn("w:pPr") + "/" + qn("w:rPr"))
    _esvaziar(paragrafo)
    _novo_run(paragrafo, formatacao, f"{{{{{campo}}}}}")
    return paragrafo


def _remover_relacoes_sem_uso(doc) -> None:
    """Remove as fotos, cabeçalhos e rodapés dos outros dias, que não são mais usados."""
    usadas = set(doc.element.xpath("//@r:id | //@r:embed | //@r:link"))
    for rid, relacao in list(doc.part.rels.items()):
        if relacao.reltype in (RT.IMAGE, RT.HEADER, RT.FOOTER) and rid not in usadas:
            doc.part.rels.pop(rid)


def _remover_marcas_do_word(elemento) -> None:
    """Remove marcas internas do Word que não podem se repetir quando o dia é copiado."""
    for tag in MARCAS_DO_WORD:
        for marca in list(elemento.iter(qn(tag))):
            marca.getparent().remove(marca)
    for no in elemento.iter():
        for atributo in list(no.attrib):
            if atributo in ATRIBUTOS_DO_WORD or "rsid" in atributo:
                del no.attrib[atributo]


def _quebra_de_secao(elemento) -> bool:
    return elemento.tag == qn("w:p") and elemento.find(qn("w:pPr") + "/" + qn("w:sectPr")) is not None


def _texto(elemento) -> str:
    return "".join(no.text or "" for no in elemento.iter(qn("w:t")))


def _vazio(paragrafo) -> bool:
    return not _texto(paragrafo).strip() and paragrafo.find(".//" + qn("w:drawing")) is None


def _esvaziar(paragrafo) -> None:
    for filho in list(paragrafo):
        if filho.tag != qn("w:pPr"):
            paragrafo.remove(filho)


def _novo_run(paragrafo, formatacao, texto: str):
    run = OxmlElement("w:r")
    if formatacao is not None:
        run.append(copy.deepcopy(formatacao))
    no = OxmlElement("w:t")
    no.text = texto
    no.set(qn("xml:space"), "preserve")
    run.append(no)
    paragrafo.append(run)
    return run


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    criar_modelo(Path(sys.argv[1]), DESTINO)
    print(f"Modelo criado em {DESTINO.relative_to(RAIZ)}")
