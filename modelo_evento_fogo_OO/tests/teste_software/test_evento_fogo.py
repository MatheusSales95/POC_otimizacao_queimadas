
import pandas as pd
from shapely.geometry import Point, box
import pytest

from pathlib import Path
import sys
path_share = Path(__file__).parent.parent.parent.parent
sys.path.append(str(path_share))


from shared.models.evento import (
    Eventos as EventoFogo,
    STATUS_ATIVO,
    STATUS_OBSERVACAO,
    STATUS_EXTINTO,
)

from shared.models.focos import Focos


def criar_evento(
    *,
    id_evento=1,
    focos=None,
    geometria=None,
    data_inicio="2024-08-01",
    data_ultima_observacao="2024-08-01",
    data_fim=None,
    area_inicio=None,
    area_fim=None,
    status=None,
    id_evento_absorvedor=None,
    persistencia=None,
    recorrencia=0,
):
    return EventoFogo(
        id_evento=id_evento,
        focos=focos if focos is not None else [],
        geometria=geometria,
        data_inicio=pd.Timestamp(data_inicio),
        data_ultima_observacao=pd.Timestamp(data_ultima_observacao),
        data_fim=(
            pd.Timestamp(data_fim)
            if data_fim is not None
            else None
        ),
        area_inicio=area_inicio,
        area_fim=area_fim,
        status=status,
        id_evento_absorvedor=id_evento_absorvedor,
        persistencia=persistencia,
        recorrencia=recorrencia,
    )


def test_atualizar_status_mantem_evento_ativo_com_ate_um_dia_sem_focos():
    evento = criar_evento(
        data_ultima_observacao="2024-08-10",
    )

    evento.atualizar_status(
        pd.Timestamp("2024-08-11")
    )

    assert evento.status == STATUS_ATIVO


def test_atualizar_status_coloca_evento_em_observacao_entre_dois_e_seis_dias():
    evento = criar_evento(
        data_ultima_observacao="2024-08-10",
    )

    evento.atualizar_status(
        pd.Timestamp("2024-08-15")
    )

    assert evento.status == STATUS_OBSERVACAO


def test_atualizar_status_extingue_evento_apos_mais_de_seis_dias():
    evento = criar_evento(
        data_ultima_observacao="2024-08-10",
    )

    evento.atualizar_status(
        pd.Timestamp("2024-08-17")
    )

    assert evento.status == STATUS_EXTINTO
    assert evento.data_fim == pd.Timestamp("2024-08-10")


def test_atualizar_status_rejeita_data_base_anterior_a_ultima_observacao():
    evento = criar_evento(
        data_ultima_observacao="2024-08-10",
    )

    with pytest.raises(
        ValueError,
        match="não pode ser anterior",
    ):
        evento.atualizar_status(
            pd.Timestamp("2024-08-09")
        )

#######

def test_recorrencia_corresponde_ao_numero_de_predecessores():
    evento = criar_evento(id_evento=1)

    predecessor_1 = criar_evento(id_evento=10)
    predecessor_2 = criar_evento(id_evento=20)
    predecessor_3 = criar_evento(id_evento=30)

    evento.incorporar_predecessores_recorrencia(
        [
            predecessor_1,
            predecessor_2,
            predecessor_3,
        ]
    )

    assert evento.recorrencia == 3
    assert evento.predecessores == [
        predecessor_1,
        predecessor_2,
        predecessor_3,
    ]

def test_incorporar_predecessores_recorrencia_adiciona_novo_evento():
    evento = criar_evento(id_evento=1)
    predecessor_1 = criar_evento(id_evento=10)
    predecessor_2 = criar_evento(id_evento=20)

    evento.incorporar_predecessores_recorrencia(
        [predecessor_1]
    )

    evento.incorporar_predecessores_recorrencia(
        [predecessor_2]
    )

    assert evento.predecessores == [
        predecessor_1,
        predecessor_2,
    ]

    assert evento.recorrencia == 2

def test_incorporar_predecessores_recorrencia_nao_duplica_evento():
    evento = criar_evento(id_evento=1)
    predecessor = criar_evento(id_evento=10)

    evento.incorporar_predecessores_recorrencia(
        [predecessor]
    )

    evento.incorporar_predecessores_recorrencia(
        [predecessor]
    )

    assert evento.predecessores == [
        predecessor
    ]

    assert evento.recorrencia == 1

def test_quantidade_sitios_conta_coordenadas_distintas():
    evento = criar_evento()

    foco_1 = Focos(
        id_foco="1",
        geometria=Point(10, 20),
    )

    foco_2 = Focos(
        id_foco="2",
        geometria=Point(10, 20),
    )

    foco_3 = Focos(
        id_foco="3",
        geometria=Point(30, 40),
    )

    evento.focos = [
        foco_1,
        foco_2,
        foco_3,
    ]

    assert evento.quantidade_sitios() == 2

def test_calcular_persistencia_relaciona_focos_e_sitios():
    evento = criar_evento()

    evento.focos = [
        Focos(id_foco="1", geometria=Point(10, 20)),
        Focos(id_foco="2", geometria=Point(10, 20)),
        Focos(id_foco="3", geometria=Point(30, 40)),
    ]

    assert evento.calcular_persistencia() == 1.5

def test_calcular_persistencia_sem_focos_retorna_zero():
    evento = criar_evento(
        focos=[]
    )

    assert evento.calcular_persistencia() == 0.0