"""Dias do período do relatório e quais deles não têm expediente."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import holidays
from dateutil.easter import easter

DIAS_DA_SEMANA = (
    "segunda-feira",
    "terça-feira",
    "quarta-feira",
    "quinta-feira",
    "sexta-feira",
    "sábado",
    "domingo",
)


@dataclass(frozen=True)
class Dia:
    data: dt.date
    motivo_sem_expediente: str | None = None  # None = dia com expediente

    @property
    def tem_expediente(self) -> bool:
        return self.motivo_sem_expediente is None

    @property
    def texto(self) -> str:
        """Ex.: "29/06/2026 (segunda-feira)"."""
        return f"{self.data:%d/%m/%Y} ({DIAS_DA_SEMANA[self.data.weekday()]})"


def pontos_facultativos(ano: int) -> dict[dt.date, str]:
    """Pontos facultativos tratados como dias sem expediente (o Dia do Servidor não entra)."""
    pascoa = easter(ano)
    return {
        pascoa - dt.timedelta(days=48): "Carnaval",
        pascoa - dt.timedelta(days=47): "Carnaval",
        pascoa - dt.timedelta(days=46): "Quarta-feira de Cinzas",
        pascoa + dt.timedelta(days=60): "Corpus Christi",
        dt.date(ano, 12, 24): "Véspera de Natal",
        dt.date(ano, 12, 31): "Véspera de Ano-Novo",
    }


def montar_calendario(
    inicio: dt.date,
    fim: dt.date,
    feriados_municipais: set[tuple[int, int]] = frozenset(),
    outros_dias_sem_expediente: set[dt.date] = frozenset(),
    dias_com_expediente: set[dt.date] = frozenset(),
) -> list[Dia]:
    anos = list(range(inicio.year, fim.year + 1))
    feriados = holidays.Brazil(subdiv="RJ", years=anos)  # nacionais + estaduais do RJ
    facultativos: dict[dt.date, str] = {}
    for ano in anos:
        facultativos.update(pontos_facultativos(ano))

    def motivo(data: dt.date) -> str | None:
        if data in dias_com_expediente:
            return None
        if data.weekday() >= 5:
            return DIAS_DA_SEMANA[data.weekday()]
        if data in feriados:
            return f"feriado: {feriados.get(data)}"
        if data in facultativos:
            return f"ponto facultativo: {facultativos[data]}"
        if (data.day, data.month) in feriados_municipais:
            return "feriado municipal"
        if data in outros_dias_sem_expediente:
            return "sem expediente (configuração)"
        return None

    total = (fim - inicio).days + 1
    return [Dia(data, motivo(data)) for data in (inicio + dt.timedelta(days=n) for n in range(total))]
