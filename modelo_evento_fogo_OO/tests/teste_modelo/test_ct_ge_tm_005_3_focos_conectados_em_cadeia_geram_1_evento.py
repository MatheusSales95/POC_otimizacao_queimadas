import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

from evento_fogo.integracao.integrador import integrar_eventos


def criar_geojson_focos(registros, crs="EPSG:4326"):
    gdf = gpd.GeoDataFrame(
        registros,
        geometry="geometry",
        crs=crs,
    )

    return gdf.to_json()


def test_ct_ge_tm_005_3_focos_conectados_em_cadeia_geram_1_evento():
    """
    CT-GE-TM-005

    Verifica que três focos no mesmo dia, conectados
    espacialmente em cadeia, geram um único evento.
    """

    geojson = criar_geojson_focos(
        [
            {
                "id": "foco_1",
                "data": "2025-01-01T12:00:00",
                "satelite": 4,
                "geometry": Point(-48.0000, -22.5000),
            },
            {
                "id": "foco_2",
                "data": "2025-01-01T12:05:00",
                "satelite": 4,
                "geometry": Point(-47.9902, -22.5000),
            },
            {
                "id": "foco_3",
                "data": "2025-01-01T12:10:00",
                "satelite": 4,
                "geometry": Point(-47.9804, -22.5000),
            },
        ]
    )

    resultado = integrar_eventos(
        focos_dia_geojson=geojson,
        gdf_banco=None,
    )

    assert isinstance(resultado, gpd.GeoDataFrame)
    assert len(resultado) == 1

    evento = resultado.iloc[0]

    assert evento["quantidade_focos"] == 3

    assert set(evento["ids_focos"]) == {
        "foco_1",
        "foco_2",
        "foco_3",
    }

    assert len(evento["focos"]) == 3

    assert {
        foco.id_foco
        for foco in evento["focos"]
    } == {
        "foco_1",
        "foco_2",
        "foco_3",
    }

    assert evento["persistencia"] == 1
    assert evento["recorrencia"] == 0

    assert evento.geometry is not None
    assert not evento.geometry.is_empty