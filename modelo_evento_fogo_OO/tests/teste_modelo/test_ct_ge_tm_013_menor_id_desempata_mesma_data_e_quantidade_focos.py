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


def test_ct_ge_tm_013_menor_id_desempata_mesma_data_e_quantidade_focos():
    """
    CT-GE-TM-013

    Verifica que, quando dois eventos envolvidos em um
    fusionamento possuem a mesma data de início e a mesma
    quantidade de focos, o evento de menor id_evento é
    escolhido como absorvedor.

    Prioridade esperada:
    1. evento mais antigo;
    2. evento com mais focos;
    3. menor id_evento.
    """

    ponto_evento_20_4326 = Point(
        -48.0000,
        -22.5000,
    )

    ponto_evento_10_4326 = Point(
        -47.9804,
        -22.5000,
    )

    ponto_evento_20_5880 = para_5880(
        ponto_evento_20_4326
    )

    ponto_evento_10_5880 = para_5880(
        ponto_evento_10_4326
    )

    foco_1 = Focos(
        id_foco="foco_1",
        data=pd.Timestamp("2025-01-01"),
        geometria=ponto_evento_20_5880,
    )

    foco_2 = Focos(
        id_foco="foco_2",
        data=pd.Timestamp("2025-01-01"),
        geometria=ponto_evento_10_5880,
    )

    gdf_banco = gpd.GeoDataFrame(
        [
            {
                "id_evento": 20,
                "focos": [foco_1],
                "ids_focos": ["foco_1"],
                "data_inicio": pd.Timestamp(
                    "2025-01-01"
                ),
                "data_ultima_observacao": pd.Timestamp(
                    "2025-01-01"
                ),
                "data_fim": None,
                "area_inicio": 100.0,
                "area_fim": None,
                "status": 1,
                "persistencia": 1,
                "recorrencia": 0,
                "id_evento_absorvedor": None,
                "geometry": (
                    ponto_evento_20_5880.buffer(1300)
                ),
            },
            {
                "id_evento": 10,
                "focos": [foco_2],
                "ids_focos": ["foco_2"],
                "data_inicio": pd.Timestamp(
                    "2025-01-01"
                ),
                "data_ultima_observacao": pd.Timestamp(
                    "2025-01-01"
                ),
                "data_fim": None,
                "area_inicio": 100.0,
                "area_fim": None,
                "status": 1,
                "persistencia": 1,
                "recorrencia": 0,
                "id_evento_absorvedor": None,
                "geometry": (
                    ponto_evento_10_5880.buffer(1300)
                ),
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
                "geometry": Point(
                    -47.9902,
                    -22.5000,
                ),
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

    # Mesmo início e mesma quantidade de focos.
    # O menor ID deve vencer.
    assert absorvedor["id_evento"] == 10

    assert absorvido["id_evento"] == 20

    assert (
        absorvido["id_evento_absorvedor"]
        == 10
    )

    assert set(
        absorvedor["ids_focos"]
    ) == {
        "foco_1",
        "foco_2",
        "foco_3",
    }

    assert absorvedor["quantidade_focos"] == 3

    assert (
        absorvedor["data_ultima_observacao"]
        == pd.Timestamp("2025-01-02")
    )