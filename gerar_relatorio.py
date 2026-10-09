"""Gera o relatório fotográfico mensal.

Normalmente é executado pelos atalhos "Gerar Relatorio - Mac.command" ou
"Gerar Relatorio - Windows.bat". Para rodar direto: python gerar_relatorio.py [--sem-fotos]
"""

import sys

from relatorio.principal import main

if __name__ == "__main__":
    sys.exit(main())
