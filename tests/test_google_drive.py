import json

import pytest

from relatorio import google_drive
from relatorio.google_drive import ErroCredenciais, baixar_fotos, carregar_credenciais, id_do_link
from relatorio.imagens import ErroFoto
from tests.auxiliares import foto_jpeg


@pytest.mark.parametrize(
    "link, esperado",
    [
        ("https://drive.google.com/open?id=1mupJYI_EUkDkXAQnWbLcdr3HwLuwlxLV", "1mupJYI_EUkDkXAQnWbLcdr3HwLuwlxLV"),
        ("https://drive.google.com/file/d/1ABC-def_123/view?usp=sharing", "1ABC-def_123"),
        ("https://exemplo.com/foto.jpg", None),
    ],
)
def test_id_do_link(link, esperado):
    assert id_do_link(link) == esperado


def test_sem_arquivo_de_credenciais(tmp_path):
    with pytest.raises(ErroCredenciais, match="Nenhum arquivo de credenciais"):
        carregar_credenciais(tmp_path)


def test_arquivo_que_nao_e_credencial(tmp_path):
    (tmp_path / "qualquer.json").write_text(json.dumps({"nome": "teste"}))
    with pytest.raises(ErroCredenciais, match="é uma credencial do Google válida"):
        carregar_credenciais(tmp_path)


class RespostaFalsa:
    def __init__(self, status: int, conteudo: bytes = b"", motivo: str = ""):
        self.status_code = status
        self.content = conteudo
        self.headers = {"Content-Length": str(len(conteudo))}
        self._motivo = motivo

    def json(self):
        return {"error": {"errors": [{"reason": self._motivo}]}}

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


class SessaoFalsa:
    def __init__(self, respostas):
        self.respostas = list(respostas)

    def get(self, *_, **__):
        return self.respostas.pop(0)


@pytest.mark.parametrize(
    "resposta, mensagem",
    [
        (RespostaFalsa(404), "não encontrada"),
        (RespostaFalsa(403, motivo="insufficientFilePermissions"), "Sem permissão"),
        (RespostaFalsa(403, motivo="fileNotDownloadable"), "não aponta para uma foto"),
    ],
)
def test_erros_de_download_viram_mensagem_para_o_relatorio(resposta, mensagem):
    with pytest.raises(ErroFoto, match=mensagem):
        google_drive._baixar_arquivo(SessaoFalsa([resposta]), "id")


def test_limite_de_requisicoes_tenta_de_novo(monkeypatch):
    monkeypatch.setattr(google_drive.time, "sleep", lambda _: None)
    sessao = SessaoFalsa([RespostaFalsa(429), RespostaFalsa(403, motivo="userRateLimitExceeded"), RespostaFalsa(200, b"ok")])
    assert google_drive._baixar_arquivo(sessao, "id") == b"ok"


class CredenciaisFalsas:
    valid = True


def test_baixar_fotos_usa_cache_e_guarda_erros(tmp_path, monkeypatch):
    (tmp_path / "em_cache.jpg").write_bytes(b"foto do cache")
    respostas = {"nova": foto_jpeg(), "quebrada": None}

    def baixar_arquivo(_sessao, id_arquivo):
        if respostas[id_arquivo] is None:
            raise ErroFoto("Foto não encontrada no Google Drive.")
        return respostas[id_arquivo]

    monkeypatch.setattr(google_drive, "AuthorizedSession", lambda _: object())
    monkeypatch.setattr(google_drive, "_baixar_arquivo", baixar_arquivo)
    progresso = []
    fotos = baixar_fotos(CredenciaisFalsas(), ["em_cache", "nova", "quebrada", "nova"], tmp_path, lambda f, t: progresso.append((f, t)))

    assert fotos["em_cache"] == b"foto do cache"
    assert fotos["nova"][:2] == b"\xff\xd8"  # JPEG
    assert isinstance(fotos["quebrada"], ErroFoto)
    assert (tmp_path / "nova.jpg").exists() and not (tmp_path / "quebrada.jpg").exists()
    assert progresso[-1] == (3, 3)
