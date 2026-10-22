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


def test_ct_ge_tm_012_evento_com_mais_focos_desempata_mesma_data_inicio():
    """
    CT-GE-TM-012

    Verifica que, quando dois eventos envolvidos em um
    fusionamento possuem a mesma data de início, o evento
    com maior quantidade de focos é escolhido como absorvedor.

    O evento com mais focos possui ID maior, garantindo que
    a quantidade de focos tenha precedência sobre o menor ID.

    Prioridade esperada:
    1. evento mais antigo;
    2. evento com mais focos;
    3. menor id_evento.
    """

    # =========================
    # 1. Definir posições
    # =========================
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

    # =========================
    # 2. Criar focos históricos
    # =========================

    # Evento 20 possui dois focos.
    foco_1 = Focos(
        id_foco="foco_1",
        data=pd.Timestamp("2025-01-01"),
        geometria=ponto_evento_20_5880,
    )

    foco_2 = Focos(
        id_foco="foco_2",
        data=pd.Timestamp("2025-01-01"),
        geometria=ponto_evento_20_5880,
    )

    # Evento 10 possui apenas um foco.
    foco_3 = Focos(
        id_foco="foco_3",
        data=pd.Timestamp("2025-01-01"),
        geometria=ponto_evento_10_5880,
    )

    # =========================
    # 3. Simular eventos existentes
    # =========================
    gdf_banco = gpd.GeoDataFrame(
        [
            {
                # Mesmo início.
                # Mais focos.
                # ID maior.
                #
                # Deve ser o absorvedor.
                "id_evento": 20,
                "focos": [
                    foco_1,
                    foco_2,
                ],
                "ids_focos": [
                    "foco_1",
                    "foco_2",
                ],
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
                # Mesmo início.
                # Menos focos.
                # ID menor.
                #
                # Deve ser absorvido.
                "id_evento": 10,
                "focos": [
                    foco_3,
                ],
                "ids_focos": [
                    "foco_3",
                ],
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

    # =========================
    # 4. Foco diário que conecta
    #    os dois eventos
    # =========================
    geojson = criar_geojson_focos(
        [
            {
                "id": "foco_4",
                "data": "2025-01-02T12:00:00",
                "satelite": 4,
                "geometry": Point(
                    -47.9902,
                    -22.5000,
                ),
            }
        ]
    )

    # =========================
    # 5. Executar modelo
    # =========================
    resultado = integrar_eventos(
        focos_dia_geojson=geojson,
        gdf_banco=gdf_banco,
    )

    # =========================
    # 6. Validar fusionamento
    # =========================
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

    # =========================
    # 7. Validar prioridade
    # =========================

    # Evento 20 deve vencer porque possui
    # mais focos, apesar de ter ID maior.
    assert absorvedor["id_evento"] == 20

    assert absorvido["id_evento"] == 10

    assert (
        absorvido["id_evento_absorvedor"]
        == 20
    )

    # =========================
    # 8. Validar incorporação
    # =========================
    assert set(
        absorvedor["ids_focos"]
    ) == {
        "foco_1",
        "foco_2",
        "foco_3",
        "foco_4",
    }

    assert absorvedor["quantidade_focos"] == 4

    assert (
        absorvedor["data_ultima_observacao"]
        == pd.Timestamp("2025-01-02")
    )