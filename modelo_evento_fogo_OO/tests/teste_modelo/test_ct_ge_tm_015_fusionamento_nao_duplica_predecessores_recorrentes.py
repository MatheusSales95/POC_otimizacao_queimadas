import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

from evento_fogo.integracao.integrador import integrar_eventos
from shared.models.evento import Eventos
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


def test_ct_ge_tm_015_fusionamento_nao_duplica_predecessores_recorrentes():
    """
    CT-GE-TM-015

    Verifica que, durante um fusionamento, predecessores
    recorrentes presentes nos dois eventos não são
    duplicados no evento absorvedor.

    Antes do fusionamento:

    - evento 10 possui predecessores 100 e 200;
    - evento 20 possui predecessores 200 e 300.

    Após o fusionamento:

    - o absorvedor possui predecessores 100, 200 e 300;
    - o predecessor 200 aparece apenas uma vez;
    - recorrencia do absorvedor é 3;
    - o absorvido perde seus predecessores;
    - a recorrencia do absorvido passa para zero.
    """

    # =========================
    # 1. Geometrias
    # =========================
    ponto_10_4326 = Point(-48.0000, -22.5000)
    ponto_20_4326 = Point(-47.9804, -22.5000)

    ponto_10_5880 = para_5880(ponto_10_4326)
    ponto_20_5880 = para_5880(ponto_20_4326)

    # =========================
    # 2. Focos históricos
    # =========================
    foco_10 = Focos(
        id_foco="foco_10",
        data=pd.Timestamp("2025-01-01"),
        geometria=ponto_10_5880,
    )

    foco_20 = Focos(
        id_foco="foco_20",
        data=pd.Timestamp("2025-01-01"),
        geometria=ponto_20_5880,
    )

    # =========================
    # 3. Predecessores recorrentes
    # =========================
    predecessor_100 = Eventos(
        id_evento=100,
        data_inicio=pd.Timestamp("2024-01-01"),
    )

    predecessor_200 = Eventos(
        id_evento=200,
        data_inicio=pd.Timestamp("2024-02-01"),
    )

    predecessor_300 = Eventos(
        id_evento=300,
        data_inicio=pd.Timestamp("2024-03-01"),
    )

    # =========================
    # 4. Eventos existentes
    # =========================
    evento_10 = Eventos(
        id_evento=10,
        focos=[foco_10],
        geometria=ponto_10_5880.buffer(1300),
        data_inicio=pd.Timestamp("2025-01-01"),
        data_ultima_observacao=pd.Timestamp("2025-01-01"),
        status=1,
        persistencia=1,
        recorrencia=2,
    )

    evento_10.predecessores = [
        predecessor_100,
        predecessor_200,
    ]

    evento_20 = Eventos(
        id_evento=20,
        focos=[foco_20],
        geometria=ponto_20_5880.buffer(1300),
        data_inicio=pd.Timestamp("2025-01-01"),
        data_ultima_observacao=pd.Timestamp("2025-01-01"),
        status=1,
        persistencia=1,
        recorrencia=2,
    )

    evento_20.predecessores = [
        predecessor_200,
        predecessor_300,
    ]

    # Evento 10 deve vencer pelo menor ID:
    # mesma data e mesma quantidade de focos.
    gdf_banco = gpd.GeoDataFrame(
        [
            {
                "id_evento": evento_10.id_evento,
                "focos": evento_10.focos,
                "data_inicio": evento_10.data_inicio,
                "data_ultima_observacao":
                    evento_10.data_ultima_observacao,
                "data_fim": None,
                "area_inicio": 100.0,
                "area_fim": None,
                "status": 1,
                "persistencia": 1,
                "recorrencia": evento_10.recorrencia,
                "predecessores": evento_10.predecessores,
                "id_evento_absorvedor": None,
                "geometry": evento_10.geom,
            },
            {
                "id_evento": evento_20.id_evento,
                "focos": evento_20.focos,
                "data_inicio": evento_20.data_inicio,
                "data_ultima_observacao":
                    evento_20.data_ultima_observacao,
                "data_fim": None,
                "area_inicio": 100.0,
                "area_fim": None,
                "status": 1,
                "persistencia": 1,
                "recorrencia": evento_20.recorrencia,
                "predecessores": evento_20.predecessores,
                "id_evento_absorvedor": None,
                "geometry": evento_20.geom,
            },
        ],
        geometry="geometry",
        crs="EPSG:5880",
    )

    # =========================
    # 5. Foco diário que provoca fusionamento
    # =========================
    geojson = criar_geojson_focos(
        [
            {
                "id": "foco_novo",
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
    # 6. Executar modelo
    # =========================
    resultado = integrar_eventos(
        focos_dia_geojson=geojson,
        gdf_banco=gdf_banco,
    )

    # =========================
    # 7. Identificar absorvedor e absorvido
    # =========================
    assert len(resultado) == 2

    absorvedor = resultado[
        resultado["id_evento_absorvedor"].isna()
    ].iloc[0]

    absorvido = resultado[
        resultado["id_evento_absorvedor"].notna()
    ].iloc[0]

    assert absorvedor["id_evento"] == 10
    assert absorvido["id_evento"] == 20

    # =========================
    # 8. Validar deduplicação
    # =========================
    assert absorvedor["recorrencia"] == 3

    ids_predecessores_absorvedor = set(
        absorvedor["predecessores"]
    )

    assert ids_predecessores_absorvedor == {
        100,
        200,
        300,
    }

    assert len(
        absorvedor["predecessores"]
    ) == 3

    # =========================
    # 9. Validar evento absorvido
    # =========================
    assert absorvido["recorrencia"] == 0

    assert absorvido["predecessores"] == []

    assert (
        absorvido["id_evento_absorvedor"]
        == 10
    )