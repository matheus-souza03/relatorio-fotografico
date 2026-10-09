"""Distribuição dos registros da planilha pelos dias do relatório.

Cada dia com expediente recebe os próximos 6 registros na ordem da planilha:
os 3 primeiros vão para a Equipe 1 e os 3 seguintes para a Equipe 2.
Dias sem expediente (e os dias depois que os registros acabam) ficam em branco.
"""

from __future__ import annotations

from dataclasses import dataclass

from .calendario import Dia
from .planilha import Registro

EQUIPES = 2
PONTOS_POR_EQUIPE = 3


@dataclass
class DiaDoRelatorio:
    dia: Dia
    equipes: list[list[Registro | None]]  # equipes[0] = Equipe 1; cada equipe tem 3 pontos


def distribuir(dias: list[Dia], registros: list[Registro]) -> tuple[list[DiaDoRelatorio], list[Registro]]:
    """Retorna os dias preenchidos e os registros que não couberam no período."""
    proximo = 0
    resultado = []
    for dia in dias:
        equipes = []
        for _ in range(EQUIPES):
            pontos: list[Registro | None] = []
            for _ in range(PONTOS_POR_EQUIPE):
                if dia.tem_expediente and proximo < len(registros):
                    pontos.append(registros[proximo])
                    proximo += 1
                else:
                    pontos.append(None)
            equipes.append(pontos)
        resultado.append(DiaDoRelatorio(dia, equipes))
    return resultado, registros[proximo:]
