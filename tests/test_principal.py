import datetime as dt

from relatorio import principal
from relatorio.imagens import ErroFoto
from tests.auxiliares import criar_planilha, foto_jpeg, link


def test_gera_relatorio_e_lista_ocorrencias(projeto):
    carimbo = dt.datetime(2026, 7, 1, 9, 0)
    linhas = [[carimbo, f"Rua {n}", carimbo, f"{link(f'a{n}')}, {link(f'd{n}')}", "Centro", n] for n in range(1, 14)]
    linhas[2][3] = link("a3")  # linha 4 da planilha: sem a foto DEPOIS
    criar_planilha(projeto / "entrada" / "planilha.xlsx", linhas)

    def baixar_falso(ids):
        return {i: ErroFoto("Foto não encontrada no Google Drive.") if i == "a5" else foto_jpeg() for i in ids}

    destino = principal.gerar(raiz=projeto, baixar_fotos=baixar_falso)

    assert destino == projeto / "saida" / "TESTE.docx"
    ocorrencias = (projeto / "saida" / "TESTE - ocorrencias.txt").read_text(encoding="utf-8-sig")
    assert "03/07/2026 – Equipe 1, Ponto 3, foto DEPOIS (linha 4): Link da foto ausente na planilha." in ocorrencias
    assert "03/07/2026 – Equipe 2, Ponto 2, foto ANTES (linha 6): Foto não encontrada no Google Drive." in ocorrencias
    assert "1 registro(s) não couberam no período (linhas 14 a 14)" in ocorrencias

    # Gerar de novo não sobrescreve o relatório anterior (que pode ter sido editado à mão).
    assert principal.gerar(raiz=projeto, baixar_fotos=baixar_falso) == projeto / "saida" / "TESTE (2).docx"


def test_main_mostra_erro_amigavel_sem_planilha(projeto, monkeypatch, capsys):
    monkeypatch.setattr(principal, "RAIZ", projeto)
    assert principal.main([]) == 1
    assert "Nenhuma planilha" in capsys.readouterr().out
