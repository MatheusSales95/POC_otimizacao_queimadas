import uuid

import pandas as pd
from shapely.geometry import Point

from pathlib import Path
import sys
path_share = Path(__file__).parent.parent.parent.parent
sys.path.append(str(path_share))

from shared.models.focos import Focos




def criar_foco(
    *,
    id_foco=None,
    data="2024-08-01",
    ponto=None,
    geometria=None,
    dias_sem_chuva=None,
    frp=None,
    id_satelite=None,
):
    return Focos(
        id_foco=id_foco or uuid.uuid4(),
        data=pd.Timestamp(data),
        ponto=ponto,
        geometria=geometria,
        dias_sem_chuva=dias_sem_chuva,
        frp=frp,
        id_satelite=id_satelite,
    )


def test_criar_foco_define_atributos():
    id_foco = uuid.uuid4()

    foco = criar_foco(
        id_foco=id_foco,
        dias_sem_chuva=4,
        frp=12,
        id_satelite=3,
    )

    assert foco.id_foco == id_foco
    assert foco.data == pd.Timestamp("2024-08-01")
    assert foco.dias_sem_chuva == 4
    assert foco.frp == 12
    assert foco.id_satelite == 3


def test_criar_foco_assume_zero_dias_sem_chuva():
    foco = criar_foco()

    assert foco.dias_sem_chuva == 0


def test_criar_foco_aceita_geometria_shapely():
    ponto = Point(-47.0, -15.0)

    foco = criar_foco(
        geometria=ponto,
    )

    assert foco.geometria.equals(ponto)


def test_criar_foco_aceita_ponto_em_wkt():
    foco = criar_foco(
        ponto="POINT (-47 -15)",
    )

    assert foco.geometria.equals(
        Point(-47, -15)
    )


def test_criar_foco_aceita_satelite_como_alias_de_id_satelite():
    foco = Focos(
        id_foco=uuid.uuid4(),
        data=pd.Timestamp("2024-08-01"),
        geometria=Point(0, 0),
        satelite=7,
    )

    assert foco.id_satelite == 7

def test_row_to_geojson_serializa_foco():
    id_foco = uuid.uuid4()

    foco = criar_foco(
        id_foco=id_foco,
        geometria=Point(-47, -15),
        dias_sem_chuva=2,
        frp=10,
        id_satelite=5,
    )

    geojson = Focos.row_to_geojson(foco)

    assert geojson["type"] == "Feature"

    assert geojson["properties"]["id"] == str(
        id_foco
    )

    assert geojson["properties"]["dias_sem_chuva"] == 2
    assert geojson["properties"]["frp"] == 10
    assert geojson["properties"]["satelite"] == 5

    assert geojson["geometry"]["type"] == "Point"
    assert geojson["geometry"]["coordinates"] == (
        -47.0,
        -15.0,
    )