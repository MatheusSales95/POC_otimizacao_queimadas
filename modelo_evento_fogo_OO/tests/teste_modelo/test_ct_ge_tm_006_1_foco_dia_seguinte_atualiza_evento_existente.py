import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

from evento_fogo.integracao.integrador import integrar_eventos
from shared.models.focos import Focos as Foco


def criar_geojson_focos(registros, crs="EPSG:4326"):
    gdf = gpd.GeoDataFrame(
        registros,
        geometry="geometry",
        crs=crs,
    )

    return gdf.to_json()


def test_ct_ge_tm_006_1_foco_dia_seguinte_atualiza_evento_existente():
    """
    CT-GE-TM-006

    Verifica que um foco do dia seguinte, espacialmente
    associado a um evento existente, atualiza esse evento
    em vez de criar um novo.
    Obs. Absorção de um novo foco não implica necessariamente em aumento da persistência
    """

    foco_anterior = Foco(
        id_foco="foco_1",
        data=pd.Timestamp("2025-01-01"),
        geometria=Point(-48.0000, -22.5000),
    )

    gdf_banco = gpd.GeoDataFrame(
        [
            {
                "id_evento": 1,
                "focos": [foco_anterior],
                "ids_focos": ["foco_1"],
                "data_inicio": pd.Timestamp("2025-01-01"),
                "data_ultima_observacao": pd.Timestamp("2025-01-01"),
                "data_fim": None,
                "area_inicio": 100.0,
                "area_fim": 100.0,
                "status": 1,
                "persistencia": 1,
                "recorrencia": 0,
                "id_evento_absorvedor": None,
                "geometry": Point(-48.0000, -22.5000),
            }
        ],
        geometry="geometry",
        crs="EPSG:4326",
    ).to_crs("EPSG:5880")

    geojson = criar_geojson_focos(
        [
            {
                "id": "foco_2",
                "data": "2025-01-02T12:00:00",
                "satelite": 4,
                "geometry": Point(-47.9902, -22.5000),
            }
        ]
    )

    resultado = integrar_eventos(
        focos_dia_geojson=geojson,
        gdf_banco=gdf_banco,
    )

    assert isinstance(resultado, gpd.GeoDataFrame)
    assert len(resultado) == 1

    evento = resultado.iloc[0]

    assert evento["id_evento"] == 1

    assert set(evento["ids_focos"]) == {
        "foco_1",
        "foco_2",
    }

    assert evento["quantidade_focos"] == 2

    assert evento["data_inicio"] == pd.Timestamp(
        "2025-01-01"
    )

    assert evento["data_ultima_observacao"] == pd.Timestamp(
        "2025-01-02"
    )

    assert evento["persistencia"] == 1
    assert evento["recorrencia"] == 0