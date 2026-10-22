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


def test_ct_ge_tm_003_2_focos_distantes_geram_2_eventos():
    """
    CT-GE-TM-003

    Verifica que dois focos espacialmente distantes,
    no mesmo dia, geram dois eventos distintos.
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
                "geometry": Point(-47.9000, -22.5000),
            },
        ]
    )

    resultado = integrar_eventos(
        focos_dia_geojson=geojson,
        gdf_banco=None,
    )

    assert isinstance(resultado, gpd.GeoDataFrame)
    assert len(resultado) == 2

    # Cada evento deve conter apenas um foco
    assert set(resultado["quantidade_focos"]) == {1}

    # Os dois focos devem estar representados,
    # cada um em seu respectivo evento.
    ids_focos_resultado = {
        id_foco
        for ids_evento in resultado["ids_focos"]
        for id_foco in ids_evento
    }

    assert ids_focos_resultado == {
        "foco_1",
        "foco_2",
    }

    # Ambos são eventos iniciados no dia analisado.
    assert set(resultado["data_inicio"]) == {
        pd.Timestamp("2025-01-01")
    }

    assert set(
        resultado["data_ultima_observacao"]
    ) == {
        pd.Timestamp("2025-01-01")
    }

    # Eventos recém-criados possuem persistência 1
    # e ainda não possuem recorrência.
    assert set(resultado["persistencia"]) == {1}
    assert set(resultado["recorrencia"]) == {0}

    assert resultado.geometry.notna().all()
    assert not resultado.geometry.is_empty.any()