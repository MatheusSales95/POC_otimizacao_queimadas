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


def test_ct_002_2_focos_proximos_geram_1_evento():
    """
    CT-002

    Verifica que dois focos próximos, no mesmo dia,
    geram um único evento contendo ambos os focos.
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
        ]
    )

    resultado = integrar_eventos(
        focos_dia_geojson=geojson,
        gdf_banco=None,
    )

    assert isinstance(resultado, gpd.GeoDataFrame)
    assert len(resultado) == 1

    evento = resultado.iloc[0]

    assert evento["quantidade_focos"] == 2

    assert set(evento["ids_focos"]) == {
        "foco_1",
        "foco_2",
    }

    assert len(evento["focos"]) == 2

    assert {
        foco.id_foco
        for foco in evento["focos"]
    } == {
        "foco_1",
        "foco_2",
    }

    assert evento["data_inicio"] == pd.Timestamp(
        "2025-01-01"
    )

    assert evento["data_ultima_observacao"] == pd.Timestamp(
        "2025-01-01"
    )

    assert evento["persistencia"] == 1
    assert evento["recorrencia"] == 0

    assert evento.geometry is not None
    assert not evento.geometry.is_empty