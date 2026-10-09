import datetime as dt

import docx
import pytest
from docx.oxml.ns import qn

from relatorio.calendario import montar_calendario
from relatorio.distribuicao import distribuir
from relatorio.documento import Documento, ErroModelo
from relatorio.imagens import ErroFoto
from relatorio.planilha import Registro
from tests.auxiliares import RAIZ_PROJETO, foto_jpeg

MODELO = RAIZ_PROJETO / "modelo" / "modelo_dia.docx"


def gerar(tmp_path, quantidade_registros: int, obter_foto):
    registros = [
        Registro(linha=n, logradouro=f"Rua {n}", bairro="Centro", numero=str(n), link_antes=f"a{n}", link_depois=f"d{n}")
        for n in range(2, 2 + quantidade_registros)
    ]
    # sexta 03/07/2026 (com registros), sábado e domingo
    dias, _ = distribuir(montar_calendario(dt.date(2026, 7, 3), dt.date(2026, 7, 5)), registros)
    documento = Documento(MODELO)
    for dia in dias:
        documento.adicionar_dia(dia, obter_foto)
    destino = tmp_path / "saida.docx"
    documento.salvar(destino)
    return docx.Document(str(destino))


def texto_completo(doc) -> str:
    return "".join(no.text or "" for no in doc.element.body.iter(qn("w:t")))


def test_preenche_datas_enderecos_e_fotos(tmp_path):
    fotos = {"ANTES": foto_jpeg(300, 400), "DEPOIS": foto_jpeg(400, 300)}

    def obter_foto(registro, momento):
        return ErroFoto("Link da foto ausente na planilha.") if registro.linha == 7 and momento == "DEPOIS" else fotos[momento]

    doc = gerar(tmp_path, 6, obter_foto)
    texto = texto_completo(doc)

    assert "{{" not in texto
    assert texto.count("DATA: 03/07/2026 (sexta-feira)") == 3  # Equipe 1, Equipe 2 e carga horária
    assert texto.count("04/07/2026 (sábado) SEM EXPEDIENTE") == 3
    assert texto.count("SEM EXPEDIENTE") == 6
    for n in range(2, 8):
        assert f"Rua {n}Centro{n}" in texto  # logradouro <tab> bairro <tab> nº
    assert texto.count("ERRO – FOTO DEPOIS") == 1
    assert "Linha 7 da planilha" in texto

    imagens = list(doc.element.body.iter(qn("wp:inline")))
    assert len(imagens) == 11
    ids = [int(el.get("id")) for el in doc.element.body.iter(qn("wp:docPr"))]
    assert len(ids) == len(set(ids))
    assert len(doc.sections) == 6  # 2 seções por dia: paisagem (equipes) e retrato (carga horária)


def test_fotos_cabem_no_espaco_sem_distorcer(tmp_path):
    proporcoes = {"ANTES": (300, 400), "DEPOIS": (1600, 900)}
    doc = gerar(tmp_path, 1, lambda _r, momento: foto_jpeg(*proporcoes[momento]))
    tamanhos = [(int(e.get("cx")), int(e.get("cy"))) for e in doc.element.body.iter(qn("wp:extent"))]
    assert len(tamanhos) == 2
    for (cx, cy), (largura, altura) in zip(tamanhos, proporcoes.values()):
        assert cx / cy == pytest.approx(largura / altura, rel=0.01)
        assert cx <= 2200 * 635 and cy <= 2956 * 635  # largura da coluna e altura da linha do modelo


def test_modelo_sem_campos(tmp_path):
    vazio = tmp_path / "vazio.docx"
    docx.Document().save(str(vazio))
    with pytest.raises(ErroModelo, match="DATA"):
        Documento(vazio)
