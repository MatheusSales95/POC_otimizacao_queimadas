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


def test_integrar_eventos_cria_evento_a_partir_dos_focos_do_dia():
    geojson = criar_geojson_focos(
        [
            {
                "id": "foco_1",
                "data": "2024-08-01T10:30:00",
                "satelite": 4,
                "geometry": Point(-47.0, -22.0),
            }
        ]
    )

    resultado = integrar_eventos(
        focos_dia_geojson=geojson,
        gdf_banco=None,
    )

    assert isinstance(resultado, gpd.GeoDataFrame)
    assert len(resultado) == 1

    evento = resultado.iloc[0]

    assert pd.isna(evento["id_evento"])
    assert evento["quantidade_focos"] == 1
    assert evento["ids_focos"] == ["foco_1"]

    assert len(evento["focos"]) == 1
    assert evento["focos"][0].id_foco == "foco_1"

    assert evento["data_inicio"] == pd.Timestamp("2024-08-01")
    assert evento["data_ultima_observacao"] == pd.Timestamp("2024-08-01")

    assert evento.geometry is not None
    assert not evento.geometry.is_empty

    assert evento["recorrencia"] == 0
    assert evento["persistencia"] == 1