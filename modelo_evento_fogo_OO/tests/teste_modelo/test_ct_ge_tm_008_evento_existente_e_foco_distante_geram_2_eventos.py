import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

from evento_fogo.integracao.integrador import integrar_eventos
from shared.models.focos import Focos


def criar_geojson_focos(registros, crs="EPSG:4326"):
    gdf = gpd.GeoDataFrame(
        registros,
        geometry="geometry",
        crs=crs,
    )

    return gdf.to_json()


def test_ct_ge_tm_008_evento_existente_e_foco_distante_geram_2_eventos():
    """
    CT-GE-TM-008

    Verifica que um foco observado no dia seguinte,
    espacialmente distante de um evento existente,
    não atualiza esse evento e gera um novo evento.
    """

    # =========================
    # 1. Evento histórico
    # =========================
    ponto_evento_4326 = Point(
        -48.0000,
        -22.5000,
    )

    ponto_evento_5880 = (
        gpd.GeoSeries(
            [ponto_evento_4326],
            crs="EPSG:4326",
        )
        .to_crs("EPSG:5880")
        .iloc[0]
    )

    foco_anterior = Focos(
        id_foco="foco_1",
        data=pd.Timestamp("2025-01-01"),
        geometria=ponto_evento_5880,
    )

    gdf_banco = gpd.GeoDataFrame(
        [
            {
                "id_evento": 1,
                "focos": [foco_anterior],
                "ids_focos": ["foco_1"],
                "data_inicio": pd.Timestamp(
                    "2025-01-01"
                ),
                "data_ultima_observacao": pd.Timestamp(
                    "2025-01-01"
                ),
                "data_fim": None,
                "area_inicio": 100.0,
                "area_fim": 100.0,
                "status": 1,
                "persistencia": 1,
                "recorrencia": 0,
                "id_evento_absorvedor": None,
                "geometry": ponto_evento_5880.buffer(1300),
            }
        ],
        geometry="geometry",
        crs="EPSG:5880",
    )

    # =========================
    # 2. Foco novo distante
    # =========================
    geojson = criar_geojson_focos(
        [
            {
                "id": "foco_2",
                "data": "2025-01-02T12:00:00",
                "satelite": 4,
                "geometry": Point(
                    -47.9000,
                    -22.5000,
                ),
            }
        ]
    )

    # =========================
    # 3. Executar modelo
    # =========================
    resultado = integrar_eventos(
        focos_dia_geojson=geojson,
        gdf_banco=gdf_banco,
    )

    # =========================
    # 4. Validar resultado
    # =========================
    assert isinstance(
        resultado,
        gpd.GeoDataFrame,
    )

    assert len(resultado) == 2

    # O evento histórico deve continuar existindo.
    evento_existente = resultado[
        resultado["id_evento"] == 1
    ].iloc[0]

    assert evento_existente["ids_focos"] == [
        "foco_1"
    ]

    assert (
        evento_existente["data_ultima_observacao"]
        == pd.Timestamp("2025-01-01")
    )

    assert evento_existente["persistencia"] == 1

    # Deve existir um novo evento para o foco distante.
    evento_novo = resultado[
        resultado["id_evento"].isna()
    ].iloc[0]

    assert evento_novo["ids_focos"] == [
        "foco_2"
    ]

    assert evento_novo["quantidade_focos"] == 1

    assert evento_novo["data_inicio"] == pd.Timestamp(
        "2025-01-02"
    )

    assert (
        evento_novo["data_ultima_observacao"]
        == pd.Timestamp("2025-01-02")
    )

    assert evento_novo["persistencia"] == 1
    assert evento_novo["recorrencia"] == 0