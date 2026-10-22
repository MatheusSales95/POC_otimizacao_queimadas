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


def test_ct_001_1_foco_gera_1_evento():
    """
    CT-001

    Verifica que um único foco no processamento diário,
    sem eventos anteriores, gera um único evento.
    """

    # =========================
    # 1. Sintetizar massa de dados
    # =========================
    geojson = criar_geojson_focos(
        [
            {
                "id": "foco_1",
                "data": "2025-01-01T12:00:00",
                "satelite": 4,
                "geometry": Point(-48.0000, -22.5000),
            }
        ]
    )

    # =========================
    # 2. Executar o modelo
    # =========================
    resultado = integrar_eventos(
        focos_dia_geojson=geojson,
        gdf_banco=None,
    )

    # =========================
    # 3. Validar resultado
    # =========================
    assert isinstance(resultado, gpd.GeoDataFrame)
    assert len(resultado) == 1

    evento = resultado.iloc[0]

    assert evento["quantidade_focos"] == 1
    assert evento["ids_focos"] == ["foco_1"]

    assert len(evento["focos"]) == 1
    assert evento["focos"][0].id_foco == "foco_1"

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