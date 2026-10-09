"""Acesso às fotos no Google Drive: credenciais, download em paralelo e cache local."""

from __future__ import annotations

import json
import os
import random
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable
from urllib.parse import parse_qs, urlparse

import requests
from google.auth.exceptions import GoogleAuthError, RefreshError
from google.auth.transport.requests import AuthorizedSession, Request
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials

from .imagens import ErroFoto, processar_imagem

ESCOPOS = ["https://www.googleapis.com/auth/drive.readonly"]
URL_ARQUIVO = "https://www.googleapis.com/drive/v3/files/{id}"
ARQUIVO_TOKEN = "token.json"  # login OAuth salvo (gerado pelo programa)
DOWNLOADS_SIMULTANEOS = 6
TENTATIVAS = 4
TAMANHO_MAXIMO_BYTES = 60 * 1024 * 1024  # acima disso provavelmente é um vídeo, não uma foto
DIAS_NO_CACHE = 90


class ErroCredenciais(Exception):
    """Problema com o acesso ao Google; a mensagem é exibida ao usuário."""


def pasta_cache_padrao() -> Path:
    """Cache das fotos fora da pasta do projeto, que pode estar sincronizada na nuvem."""
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Caches"
    else:
        base = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache")
    return base / "relatorio_fotografico" / "fotos"


def id_do_link(link: str) -> str | None:
    """Extrai o ID do arquivo de links como drive.google.com/open?id=ID ou /file/d/ID/view."""
    url = urlparse(link)
    if "google." not in url.netloc:
        return None
    ids = parse_qs(url.query).get("id")
    if ids:
        return ids[0]
    partes = url.path.split("/")
    if "d" in partes and partes.index("d") + 1 < len(partes):
        return partes[partes.index("d") + 1] or None
    return None


def carregar_credenciais(pasta: Path):
    """Usa o primeiro .json válido da pasta: conta de serviço ou ID do cliente OAuth (login)."""
    arquivos = sorted(p for p in pasta.glob("*.json") if p.name != ARQUIVO_TOKEN)
    if not arquivos:
        raise ErroCredenciais(
            f'Nenhum arquivo de credenciais (.json) foi encontrado na pasta "{pasta.name}". '
            "Siga o passo a passo do LEIAME.md para criar o acesso ao Google Drive."
        )
    for caminho in arquivos:
        try:
            info = json.loads(caminho.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if info.get("type") == "service_account":
            return service_account.Credentials.from_service_account_info(info, scopes=ESCOPOS)
        if "installed" in info or "web" in info:
            return _credenciais_oauth(caminho, pasta / ARQUIVO_TOKEN)
    raise ErroCredenciais(
        f'Nenhum arquivo .json da pasta "{pasta.name}" é uma credencial do Google válida '
        "(conta de serviço ou ID do cliente OAuth)."
    )


def _credenciais_oauth(arquivo_cliente: Path, arquivo_token: Path) -> Credentials:
    from google_auth_oauthlib.flow import InstalledAppFlow

    credenciais = None
    if arquivo_token.exists():
        try:
            credenciais = Credentials.from_authorized_user_file(str(arquivo_token), ESCOPOS)
        except ValueError:
            credenciais = None
    if credenciais and credenciais.expired and credenciais.refresh_token:
        try:
            credenciais.refresh(Request())
        except RefreshError:  # login expirado ou revogado: pede de novo
            credenciais = None
    if not credenciais or not credenciais.valid:
        print("Abrindo o navegador para você entrar na conta Google que tem acesso às fotos...")
        fluxo = InstalledAppFlow.from_client_secrets_file(str(arquivo_cliente), ESCOPOS)
        credenciais = fluxo.run_local_server(
            port=0,
            authorization_prompt_message="Se o navegador não abrir sozinho, acesse este endereço: {url}",
            success_message="Login concluído. Pode fechar esta aba e voltar ao programa.",
        )
    arquivo_token.write_text(credenciais.to_json(), encoding="utf-8")
    return credenciais


def baixar_fotos(
    credenciais,
    ids: list[str],
    pasta_cache: Path,
    ao_progredir: Callable[[int, int], None] | None = None,
) -> dict[str, bytes | ErroFoto]:
    """Baixa e prepara as fotos. Fotos já baixadas antes são lidas do cache."""
    pasta_cache.mkdir(parents=True, exist_ok=True)
    _limpar_cache_antigo(pasta_cache)
    resultado: dict[str, bytes | ErroFoto] = {}
    pendentes = []
    for id_arquivo in dict.fromkeys(ids):
        no_cache = pasta_cache / f"{id_arquivo}.jpg"
        if no_cache.exists():
            resultado[id_arquivo] = no_cache.read_bytes()
        else:
            pendentes.append(id_arquivo)

    total = len(resultado) + len(pendentes)
    if ao_progredir:
        ao_progredir(len(resultado), total)
    if not pendentes:
        return resultado

    _garantir_token(credenciais)
    sessoes = threading.local()

    def baixar(id_arquivo: str) -> bytes | ErroFoto:
        if not hasattr(sessoes, "sessao"):
            sessoes.sessao = AuthorizedSession(credenciais)
        try:
            foto = processar_imagem(_baixar_arquivo(sessoes.sessao, id_arquivo))
        except ErroFoto as erro:
            return erro
        _salvar_no_cache(pasta_cache / f"{id_arquivo}.jpg", foto)
        return foto

    with ThreadPoolExecutor(max_workers=DOWNLOADS_SIMULTANEOS) as executor:
        futuros = {executor.submit(baixar, id_arquivo): id_arquivo for id_arquivo in pendentes}
        for futuro in as_completed(futuros):
            resultado[futuros[futuro]] = futuro.result()
            if ao_progredir:
                ao_progredir(len(resultado), total)
    return resultado


def _garantir_token(credenciais) -> None:
    if credenciais.valid:
        return
    try:
        credenciais.refresh(Request())
    except RefreshError as erro:
        raise ErroCredenciais(f"O Google recusou as credenciais da pasta credenciais: {erro}") from erro
    except GoogleAuthError as erro:
        raise ErroCredenciais(f"Não foi possível conectar ao Google (verifique a internet): {erro}") from erro


def _baixar_arquivo(sessao: AuthorizedSession, id_arquivo: str) -> bytes:
    for tentativa in range(1, TENTATIVAS + 1):
        try:
            with sessao.get(
                URL_ARQUIVO.format(id=id_arquivo),
                params={"alt": "media", "supportsAllDrives": "true"},
                timeout=(15, 120),
                stream=True,
            ) as resposta:
                if resposta.status_code == 200:
                    if int(resposta.headers.get("Content-Length") or 0) > TAMANHO_MAXIMO_BYTES:
                        raise ErroFoto("O arquivo do link é grande demais para ser uma foto (pode ser um vídeo).")
                    return resposta.content
                motivo = _motivo_do_erro(resposta)
                temporario = resposta.status_code in (429, 500, 502, 503, 504) or motivo in (
                    "rateLimitExceeded",
                    "userRateLimitExceeded",
                )
                if not temporario or tentativa == TENTATIVAS:
                    raise ErroFoto(_mensagem_de_erro(resposta.status_code, motivo))
        except (requests.RequestException, GoogleAuthError) as erro:
            if tentativa == TENTATIVAS:
                raise ErroFoto("Falha de conexão ao baixar a foto (verifique a internet).") from erro
        time.sleep(2**tentativa + random.random())
    raise AssertionError("inalcançável")


def _motivo_do_erro(resposta: requests.Response) -> str:
    try:
        return resposta.json()["error"]["errors"][0]["reason"]
    except (ValueError, KeyError, IndexError, TypeError):
        return ""


def _mensagem_de_erro(status: int, motivo: str) -> str:
    if status == 404:
        return "Foto não encontrada no Google Drive (link quebrado ou sem permissão de acesso)."
    if motivo == "fileNotDownloadable":
        return "O link não aponta para uma foto."
    if status == 403:
        return "Sem permissão para acessar a foto no Google Drive."
    if status == 401:
        return "O Google recusou as credenciais de acesso."
    return f"O Google Drive respondeu com erro {status} ao baixar a foto."


def _salvar_no_cache(destino: Path, dados: bytes) -> None:
    temporario = destino.with_suffix(".tmp")
    temporario.write_bytes(dados)
    temporario.replace(destino)


def _limpar_cache_antigo(pasta_cache: Path) -> None:
    limite = time.time() - DIAS_NO_CACHE * 24 * 3600
    for arquivo in pasta_cache.glob("*"):
        try:
            if arquivo.stat().st_mtime < limite:
                arquivo.unlink()
        except OSError:
            pass
