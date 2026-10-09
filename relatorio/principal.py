"""Execução principal: lê a configuração e a planilha, baixa as fotos e gera o .docx."""

from __future__ import annotations

import argparse
import datetime as dt
import traceback
from pathlib import Path
from typing import Callable

from . import calendario, config, distribuicao, documento, google_drive, planilha
from .distribuicao import DiaDoRelatorio
from .imagens import ErroFoto
from .planilha import Registro

RAIZ = Path(__file__).resolve().parent.parent
MOMENTOS = ("ANTES", "DEPOIS")
ATIVIDADES_POR_DIA = distribuicao.EQUIPES * distribuicao.PONTOS_POR_EQUIPE
MAXIMO_OCORRENCIAS_NA_TELA = 15

BaixarFotos = Callable[[list[str]], "dict[str, bytes | ErroFoto]"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Gera o relatório fotográfico mensal.")
    parser.add_argument(
        "--sem-fotos",
        action="store_true",
        help="não baixa as fotos; útil para conferir datas e páginas antes de configurar o Google",
    )
    argumentos = parser.parse_args(argv)
    try:
        gerar(sem_fotos=argumentos.sem_fotos)
    except (
        config.ErroConfiguracao,
        planilha.ErroPlanilha,
        google_drive.ErroCredenciais,
        documento.ErroModelo,
    ) as erro:
        print(f"\nERRO: {erro}")
        return 1
    except KeyboardInterrupt:
        print("\nCancelado.")
        return 130
    except Exception:
        traceback.print_exc()
        print("\nERRO inesperado. Envie a mensagem acima para quem mantém o programa.")
        return 1
    return 0


def gerar(raiz: Path | None = None, sem_fotos: bool = False, baixar_fotos: BaixarFotos | None = None) -> Path:
    """Gera o relatório e retorna o caminho do .docx criado."""
    raiz = raiz or RAIZ
    print("=== Relatório Fotográfico ===")
    cfg = config.carregar(raiz / "configuracao.ini")

    caminho_planilha, outras_planilhas = planilha.localizar_planilha(raiz / "entrada")
    registros = planilha.ler_registros(caminho_planilha)
    if registros:
        faixa = f"linhas {registros[0].linha} a {registros[-1].linha}"
        print(f"Planilha: {caminho_planilha.name} ({len(registros)} registros, {faixa})")
    else:
        print(f"Planilha: {caminho_planilha.name} (nenhum registro encontrado)")
    if outras_planilhas:
        print(f'  Atenção: há {len(outras_planilhas) + 1} planilhas na pasta "entrada"; foi usada a mais recente.')

    dias = calendario.montar_calendario(
        cfg.data_inicial,
        cfg.data_final,
        cfg.feriados_municipais,
        cfg.outros_dias_sem_expediente,
        cfg.dias_com_expediente,
    )
    dias_relatorio, sobra = distribuicao.distribuir(dias, registros)
    _mostrar_periodo(cfg, dias)

    usados = [registro for dia in dias_relatorio for registro in _registros_do_dia(dia)]
    ids = [
        id_arquivo
        for registro in usados
        for link in (registro.link_antes, registro.link_depois)
        if link and (id_arquivo := google_drive.id_do_link(link))
    ]
    if sem_fotos or not ids:
        fotos: dict[str, bytes | ErroFoto] = {}
    elif baixar_fotos is not None:
        fotos = baixar_fotos(ids)
    else:
        credenciais = google_drive.carregar_credenciais(raiz / "credenciais")
        fotos = google_drive.baixar_fotos(credenciais, ids, google_drive.pasta_cache_padrao(), _mostrar_progresso)
        print()

    def obter_foto(registro: Registro, momento: str) -> bytes | ErroFoto:
        if sem_fotos:
            return ErroFoto("Fotos não baixadas (teste com --sem-fotos).")
        link = registro.link_antes if momento == "ANTES" else registro.link_depois
        if not link:
            return ErroFoto("Link da foto ausente na planilha.")
        id_arquivo = google_drive.id_do_link(link)
        if not id_arquivo:
            return ErroFoto("O link da foto não é do Google Drive.")
        return fotos.get(id_arquivo) or ErroFoto("A foto não foi baixada.")

    print("Montando o documento...")
    relatorio = documento.Documento(raiz / "modelo" / "modelo_dia.docx")
    for dia in dias_relatorio:
        relatorio.adicionar_dia(dia, obter_foto)
    pasta_saida = raiz / "saida"
    pasta_saida.mkdir(exist_ok=True)
    destino = _caminho_livre(pasta_saida / f"{cfg.nome_arquivo}.docx")
    relatorio.salvar(destino)
    print(f"\nRelatório salvo em: {destino.relative_to(raiz)}")

    ocorrencias = _ocorrencias(dias_relatorio, sobra, obter_foto, incluir_fotos=not sem_fotos)
    if sem_fotos:
        print("As fotos não foram baixadas (--sem-fotos): no lugar delas há um aviso de erro.")
    if ocorrencias:
        arquivo = destino.with_name(f"{destino.stem} - ocorrencias.txt")
        _salvar_ocorrencias(arquivo, destino, caminho_planilha, ocorrencias)
        print(f"\nATENÇÃO: {len(ocorrencias)} ocorrência(s). Detalhes em: {arquivo.relative_to(raiz)}")
        for linha in ocorrencias[:MAXIMO_OCORRENCIAS_NA_TELA]:
            print(f"  - {linha}")
        if len(ocorrencias) > MAXIMO_OCORRENCIAS_NA_TELA:
            print(f"  ... e mais {len(ocorrencias) - MAXIMO_OCORRENCIAS_NA_TELA} no arquivo.")
    else:
        print("Nenhuma ocorrência: todas as fotos foram inseridas.")
    return destino


def _registros_do_dia(dia: DiaDoRelatorio) -> list[Registro]:
    return [registro for equipe in dia.equipes for registro in equipe if registro is not None]


def _mostrar_periodo(cfg: config.Configuracao, dias: list[calendario.Dia]) -> None:
    uteis = sum(dia.tem_expediente for dia in dias)
    print(
        f"Período: {cfg.data_inicial:%d/%m/%Y} a {cfg.data_final:%d/%m/%Y} "
        f"({len(dias)} dias, {uteis} com expediente = {uteis * ATIVIDADES_POR_DIA} atividades)"
    )
    folgas = [dia for dia in dias if not dia.tem_expediente and dia.data.weekday() < 5]
    if folgas:
        print("Dias da semana sem expediente:")
        for dia in folgas:
            print(f"  - {dia.texto}: {dia.motivo_sem_expediente}")


def _mostrar_progresso(feitas: int, total: int) -> None:
    print(f"\rBaixando fotos do Google Drive... {feitas}/{total}", end="", flush=True)


def _caminho_livre(destino: Path) -> Path:
    """Nunca sobrescreve um relatório existente (ele pode já ter sido editado à mão)."""
    candidato, numero = destino, 2
    while candidato.exists():
        candidato = destino.with_name(f"{destino.stem} ({numero}){destino.suffix}")
        numero += 1
    return candidato


def _ocorrencias(
    dias_relatorio: list[DiaDoRelatorio],
    sobra: list[Registro],
    obter_foto: Callable[[Registro, str], bytes | ErroFoto],
    incluir_fotos: bool,
) -> list[str]:
    ocorrencias = []
    for dia in dias_relatorio:
        for numero_equipe, equipe in enumerate(dia.equipes, start=1):
            for numero_ponto, registro in enumerate(equipe, start=1):
                if registro is None:
                    continue
                local = f"{dia.dia.data:%d/%m/%Y} – Equipe {numero_equipe}, Ponto {numero_ponto}"
                for aviso in registro.avisos:
                    ocorrencias.append(f"{local} (linha {registro.linha}): {aviso}")
                if not incluir_fotos:
                    continue
                for momento in MOMENTOS:
                    foto = obter_foto(registro, momento)
                    if isinstance(foto, ErroFoto):
                        ocorrencias.append(f"{local}, foto {momento} (linha {registro.linha}): {foto}")

    sem_registros = [
        dia for dia in dias_relatorio if dia.dia.tem_expediente and len(_registros_do_dia(dia)) < ATIVIDADES_POR_DIA
    ]
    if sem_registros:
        ocorrencias.append(
            f"Os registros da planilha acabaram em {sem_registros[0].dia.data:%d/%m/%Y}: "
            f"{len(sem_registros)} dia(s) com expediente ficaram sem fotos (ou incompletos)."
        )
    if sobra:
        ocorrencias.append(
            f"{len(sobra)} registro(s) não couberam no período (linhas {sobra[0].linha} a {sobra[-1].linha}). "
            "Eles devem entrar no próximo relatório."
        )
    return ocorrencias


def _salvar_ocorrencias(arquivo: Path, relatorio: Path, caminho_planilha: Path, ocorrencias: list[str]) -> None:
    cabecalho = [
        f"Relatório: {relatorio.name}",
        f"Planilha: {caminho_planilha.name}",
        f"Gerado em: {dt.datetime.now():%d/%m/%Y %H:%M}",
        "",
        'No Word, procure por "ERRO" para encontrar as fotos que precisam ser inseridas à mão.',
        "",
    ]
    arquivo.write_text("\n".join(cabecalho + [f"- {linha}" for linha in ocorrencias]) + "\n", encoding="utf-8-sig")
