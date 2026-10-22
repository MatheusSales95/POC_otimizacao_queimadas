import pandas as pd
import pytest
from unittest.mock import Mock

from pathlib import Path
import sys
path_share = Path(__file__).parent.parent.parent.parent
sys.path.append(str(path_share))

from shared.models.evento import Eventos as EventoFogo
from evento_fogo.processamento.resolucao_fusionamentos import (
    ResolvedorFusionamentos,
)


def criar_evento(
    *,
    data_inicio,
    quantidade_focos,
    id_evento,
):
    evento = Mock(spec=EventoFogo)

    evento.data_inicio = pd.Timestamp(data_inicio)
    evento.id_evento = id_evento
    evento.quantidade_focos.return_value = quantidade_focos

    return evento


def test_resolver_grupo_rejeita_grupo_vazio():
    resolvedor = ResolvedorFusionamentos()

    with pytest.raises(
        ValueError,
        match="Não é possível resolver um grupo vazio",
    ):
        resolvedor.resolver_grupo([])


def test_resolver_grupo_escolhe_evento_mais_antigo_como_absorvedor():
    evento_antigo = criar_evento(
        data_inicio="2024-08-01",
        quantidade_focos=2,
        id_evento=10,
    )

    evento_recente = criar_evento(
        data_inicio="2024-08-02",
        quantidade_focos=20,
        id_evento=1,
    )

    absorvedor, absorvidos = (
        ResolvedorFusionamentos()
        .resolver_grupo(
            [
                evento_recente,
                evento_antigo,
            ]
        )
    )

    assert absorvedor is evento_antigo
    assert absorvidos == [evento_recente]


def test_resolver_grupo_desempata_pela_maior_quantidade_de_focos():
    evento_menor = criar_evento(
        data_inicio="2024-08-01",
        quantidade_focos=2,
        id_evento=1,
    )

    evento_maior = criar_evento(
        data_inicio="2024-08-01",
        quantidade_focos=5,
        id_evento=10,
    )

    absorvedor, absorvidos = (
        ResolvedorFusionamentos()
        .resolver_grupo(
            [
                evento_menor,
                evento_maior,
            ]
        )
    )

    assert absorvedor is evento_maior
    assert absorvidos == [evento_menor]


def test_resolver_grupo_desempata_pelo_menor_id_evento():
    evento_id_menor = criar_evento(
        data_inicio="2024-08-01",
        quantidade_focos=5,
        id_evento=1,
    )

    evento_id_maior = criar_evento(
        data_inicio="2024-08-01",
        quantidade_focos=5,
        id_evento=2,
    )

    absorvedor, absorvidos = (
        ResolvedorFusionamentos()
        .resolver_grupo(
            [
                evento_id_maior,
                evento_id_menor,
            ]
        )
    )

    assert absorvedor is evento_id_menor
    assert absorvidos == [evento_id_maior]


def test_resolver_grupo_prioriza_evento_com_id_sobre_evento_sem_id():
    evento_com_id = criar_evento(
        data_inicio="2024-08-01",
        quantidade_focos=5,
        id_evento=10,
    )

    evento_sem_id = criar_evento(
        data_inicio="2024-08-01",
        quantidade_focos=5,
        id_evento=None,
    )

    absorvedor, absorvidos = (
        ResolvedorFusionamentos()
        .resolver_grupo(
            [
                evento_sem_id,
                evento_com_id,
            ]
        )
    )

    assert absorvedor is evento_com_id
    assert absorvidos == [evento_sem_id]


def test_resolver_grupo_retorna_todos_os_demais_eventos_como_absorvidos():
    evento_absorvedor = criar_evento(
        data_inicio="2024-08-01",
        quantidade_focos=3,
        id_evento=1,
    )

    evento_2 = criar_evento(
        data_inicio="2024-08-02",
        quantidade_focos=10,
        id_evento=2,
    )

    evento_3 = criar_evento(
        data_inicio="2024-08-03",
        quantidade_focos=20,
        id_evento=3,
    )

    absorvedor, absorvidos = (
        ResolvedorFusionamentos()
        .resolver_grupo(
            [
                evento_3,
                evento_absorvedor,
                evento_2,
            ]
        )
    )

    assert absorvedor is evento_absorvedor
    assert absorvidos == [
        evento_3,
        evento_2,
    ]


def test_resolver_grupos_resolve_cada_grupo_independentemente():
    evento_a1 = criar_evento(
        data_inicio="2024-08-01",
        quantidade_focos=3,
        id_evento=1,
    )

    evento_a2 = criar_evento(
        data_inicio="2024-08-02",
        quantidade_focos=5,
        id_evento=2,
    )

    evento_b1 = criar_evento(
        data_inicio="2024-08-05",
        quantidade_focos=2,
        id_evento=10,
    )

    evento_b2 = criar_evento(
        data_inicio="2024-08-05",
        quantidade_focos=8,
        id_evento=20,
    )

    resultados = (
        ResolvedorFusionamentos()
        .resolver_grupos(
            [
                [evento_a2, evento_a1],
                [evento_b1, evento_b2],
            ]
        )
    )

    assert len(resultados) == 2

    absorvedor_a, absorvidos_a = resultados[0]
    absorvedor_b, absorvidos_b = resultados[1]

    assert absorvedor_a is evento_a1
    assert absorvidos_a == [evento_a2]

    assert absorvedor_b is evento_b2
    assert absorvidos_b == [evento_b1]