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


def test_ct_ge_tm_011_evento_mais_antigo_e_escolhido_como_absorvedor():
    """
    CT-GE-TM-011

    Verifica que, em um fusionamento, o evento mais antigo
    é escolhido como absorvedor, independentemente de possuir
    área menor ou ID maior que o outro evento.
    """

    ponto_evento_antigo_4326 = Point(-48.0000, -22.5000)
    ponto_evento_novo_4326 = Point(-47.9804, -22.5000)

    ponto_evento_antigo_5880 = para_5880(
        ponto_evento_antigo_4326
    )

    ponto_evento_novo_5880 = para_5880(
        ponto_evento_novo_4326
    )

    foco_antigo = Focos(
        id_foco="foco_1",
        data=pd.Timestamp("2025-01-01"),
        geometria=ponto_evento_antigo_5880,
    )

    foco_novo = Focos(
        id_foco="foco_2",
        data=pd.Timestamp("2025-01-02"),
        geometria=ponto_evento_novo_5880,
    )

    gdf_banco = gpd.GeoDataFrame(
        [
            {
                # Mais antigo, mas com ID maior e área menor.
                "id_evento": 20,
                "focos": [foco_antigo],
                "ids_focos": ["foco_1"],
                "data_inicio": pd.Timestamp("2025-01-01"),
                "data_ultima_observacao": pd.Timestamp("2025-01-02"),
                "data_fim": None,
                "area_inicio": 100.0,
                "area_fim": 100.0,
                "status": 1,
                "persistencia": 1,
                "recorrencia": 0,
                "id_evento_absorvedor": None,
                "geometry": ponto_evento_antigo_5880.buffer(1300),
            },
            {
                # Mais novo, com ID menor e área maior.
                "id_evento": 10,
                "focos": [foco_novo],
                "ids_focos": ["foco_2"],
                "data_inicio": pd.Timestamp("2025-01-02"),
                "data_ultima_observacao": pd.Timestamp("2025-01-02"),
                "data_fim": None,
                "area_inicio": 500.0,
                "area_fim": 500.0,
                "status": 1,
                "persistencia": 1,
                "recorrencia": 0,
                "id_evento_absorvedor": None,
                "geometry": ponto_evento_novo_5880.buffer(1300),
            },
        ],
        geometry="geometry",
        crs="EPSG:5880",
    )

    geojson = criar_geojson_focos(
        [
            {
                "id": "foco_3",
                "data": "2025-01-03T12:00:00",
                "satelite": 4,
                "geometry": Point(-47.9902, -22.5000),
            }
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

    absorvedor = resultado[
        resultado["id_evento_absorvedor"].isna()
    ].iloc[0]

    absorvido = resultado[
        resultado["id_evento_absorvedor"].notna()
    ].iloc[0]

    assert absorvedor["id_evento"] == 20

    assert absorvido["id_evento"] == 10

    assert (
        absorvido["id_evento_absorvedor"]
        == 20
    )

    assert set(
        absorvedor["ids_focos"]
    ) == {
        "foco_1",
        "foco_2",
        "foco_3",
    }

    assert absorvedor["quantidade_focos"] == 3