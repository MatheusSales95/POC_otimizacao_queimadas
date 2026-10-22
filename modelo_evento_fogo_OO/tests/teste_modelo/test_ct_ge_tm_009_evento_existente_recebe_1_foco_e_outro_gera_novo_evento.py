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


def test_ct_ge_tm_009_evento_existente_recebe_1_foco_e_outro_gera_novo_evento():
    """
    CT-GE-TM-009

    Verifica que, no mesmo processamento diário,
    um foco espacialmente associado a um evento existente
    atualiza esse evento, enquanto outro foco distante
    gera um novo evento.
    """

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
                "data_inicio": pd.Timestamp("2025-01-01"),
                "data_ultima_observacao": pd.Timestamp("2025-01-01"),
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

    geojson = criar_geojson_focos(
        [
            {
                "id": "foco_2",
                "data": "2025-01-02T12:00:00",
                "satelite": 4,
                "geometry": Point(
                    -47.9902,
                    -22.5000,
                ),
            },
            {
                "id": "foco_3",
                "data": "2025-01-02T12:05:00",
                "satelite": 4,
                "geometry": Point(
                    -47.9000,
                    -22.5000,
                ),
            },
        ]
    )

    resultado = integrar_eventos(
        focos_dia_geojson=geojson,
        gdf_banco=gdf_banco,
    )

    assert isinstance(
        resultado,
        gpd.GeoDataFrame,
    )

    assert len(resultado) == 2

    evento_existente = resultado[
        resultado["id_evento"] == 1
    ].iloc[0]

    assert set(
        evento_existente["ids_focos"]
    ) == {
        "foco_1",
        "foco_2",
    }

    assert evento_existente["quantidade_focos"] == 2

    assert (
        evento_existente["data_ultima_observacao"]
        == pd.Timestamp("2025-01-02")
    )

    evento_novo = resultado[
        resultado["id_evento"].isna()
    ].iloc[0]

    assert evento_novo["ids_focos"] == [
        "foco_3"
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