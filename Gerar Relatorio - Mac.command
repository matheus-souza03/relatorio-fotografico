#!/bin/bash
# Gera o relatório fotográfico. Dê dois cliques neste arquivo.
# Na primeira vez, prepara o Python numa pasta do usuário (fora da pasta do projeto).

cd "$(dirname "$0")" || exit 1
VENV="${RELATORIO_VENV:-$HOME/.relatorio_fotografico/venv}"

pausar() {
    echo
    read -r -p "Pressione Enter para fechar esta janela..." _
}

if [ ! -x "$VENV/bin/python" ]; then
    echo "Preparando o programa (somente na primeira vez; pode levar alguns minutos)..."
    if ! command -v python3 >/dev/null 2>&1; then
        echo "ERRO: o Python 3 não está instalado. Instale pelo site https://www.python.org/downloads/ e tente de novo."
        pausar
        exit 1
    fi
    mkdir -p "$(dirname "$VENV")"
    if ! python3 -m venv --clear "$VENV"; then
        echo "ERRO: não foi possível preparar o Python. Veja a seção \"Problemas comuns\" do LEIAME.md."
        pausar
        exit 1
    fi
fi

echo "Verificando componentes..."
if ! "$VENV/bin/python" -m pip install --disable-pip-version-check -q -r requirements.txt; then
    echo "ERRO: não foi possível instalar os componentes. Verifique a conexão com a internet e tente de novo."
    pausar
    exit 1
fi
"$VENV/bin/python" -m pip install --disable-pip-version-check -q -r requirements-opcional.txt >/dev/null 2>&1

echo
"$VENV/bin/python" gerar_relatorio.py "$@"
codigo=$?
pausar
exit $codigo
