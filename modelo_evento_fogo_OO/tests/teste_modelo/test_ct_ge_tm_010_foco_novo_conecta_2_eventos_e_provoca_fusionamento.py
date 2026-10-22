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


def para_5880(ponto):
    return (
        gpd.GeoSeries(
            [ponto],
            crs="EPSG:4326",
        )
        .to_crs("EPSG:5880")
        .iloc[0]
    )


def test_ct_ge_tm_010_foco_novo_conecta_2_eventos_e_provoca_fusionamento():
    """
    CT-GE-TM-010

    Verifica que um novo foco, ao conectar espacialmente
    dois eventos existentes, provoca o fusionamento dos eventos.
    """

    ponto_1_4326 = Point(-48.0000, -22.5000)
    ponto_2_4326 = Point(-47.9804, -22.5000)

    ponto_1_5880 = para_5880(ponto_1_4326)
    ponto_2_5880 = para_5880(ponto_2_4326)

    foco_1 = Focos(
        id_foco="foco_1",
        data=pd.Timestamp("2025-01-01"),
        geometria=ponto_1_5880,
    )

    foco_2 = Focos(
        id_foco="foco_2",
        data=pd.Timestamp("2025-01-01"),
        geometria=ponto_2_5880,
    )

    gdf_banco = gpd.GeoDataFrame(
        [
            {
                "id_evento": 1,
                "focos": [foco_1],
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
                "geometry": ponto_1_5880.buffer(1300),
            },
            {
                "id_evento": 2,
                "focos": [foco_2],
                "ids_focos": ["foco_2"],
                "data_inicio": pd.Timestamp("2025-01-01"),
                "data_ultima_observacao": pd.Timestamp("2025-01-01"),
                "data_fim": None,
                "area_inicio": 100.0,
                "area_fim": 100.0,
                "status": 1,
                "persistencia": 1,
                "recorrencia": 0,
                "id_evento_absorvedor": None,
                "geometry": ponto_2_5880.buffer(1300),
            },
        ],
        geometry="geometry",
        crs="EPSG:5880",
    )

    geojson = criar_geojson_focos(
        [
            {
                "id": "foco_3",
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

    # Esperamos manter os dois registros:
    # um absorvedor e um extinto por fusão.
    assert len(resultado) == 2

    eventos_ativos = resultado[
        resultado["id_evento_absorvedor"].isna()
    ]

    eventos_absorvidos = resultado[
        resultado["id_evento_absorvedor"].notna()
    ]

    assert len(eventos_ativos) == 1
    assert len(eventos_absorvidos) == 1

    absorvedor = eventos_ativos.iloc[0]
    absorvido = eventos_absorvidos.iloc[0]

    assert set(absorvedor["ids_focos"]) == {
        "foco_1",
        "foco_2",
        "foco_3",
    }

    assert absorvedor["quantidade_focos"] == 3

    assert absorvido["id_evento_absorvedor"] == absorvedor["id_evento"]

    assert (
        absorvedor["data_ultima_observacao"]
        == pd.Timestamp("2025-01-02")
    )