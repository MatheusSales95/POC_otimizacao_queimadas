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


def test_ct_ge_tm_007_foco_mesmo_pixel_incrementa_persistencia():
    """
    CT-GE-TM-007

    Verifica que um foco observado no dia seguinte,
    no mesmo sítio espacial de um foco anterior,
    mantém a continuidade do evento e incrementa
    sua persistência.

    Os focos usados pelo motor OO devem estar no mesmo
    CRS operacional para que quantidade_sitios() possa
    comparar corretamente suas coordenadas.
    """

    # =========================
    # 1. Definir o mesmo sítio em EPSG:4326
    # =========================
    ponto_4326 = Point(
        -48.0000,
        -22.5000,
    )

    # =========================
    # 2. Converter o foco histórico
    #    para o CRS operacional
    # =========================
    ponto_5880 = (
        gpd.GeoSeries(
            [ponto_4326],
            crs="EPSG:4326",
        )
        .to_crs("EPSG:5880")
        .iloc[0]
    )

    foco_anterior = Focos(
        id_foco="foco_1",
        data=pd.Timestamp("2025-01-01"),
        geometria=ponto_5880,
    )

    # =========================
    # 3. Simular evento existente
    #    carregado do banco
    # =========================
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
                "geometry": ponto_5880.buffer(1300),
            }
        ],
        geometry="geometry",
        crs="EPSG:5880",
    )

    # =========================
    # 4. Criar foco do dia seguinte
    #    no mesmo sítio
    # =========================
    geojson = criar_geojson_focos(
        [
            {
                "id": "foco_2",
                "data": "2025-01-02T12:00:00",
                "satelite": 4,
                "geometry": ponto_4326,
            }
        ]
    )

    # =========================
    # 5. Executar o modelo
    # =========================
    resultado = integrar_eventos(
        focos_dia_geojson=geojson,
        gdf_banco=gdf_banco,
    )

    # =========================
    # 6. Validar resultado
    # =========================
    assert isinstance(
        resultado,
        gpd.GeoDataFrame,
    )

    assert len(resultado) == 1

    evento = resultado.iloc[0]

    assert evento["id_evento"] == 1

    assert set(
        evento["ids_focos"]
    ) == {
        "foco_1",
        "foco_2",
    }

    assert evento["quantidade_focos"] == 2

    assert evento["data_inicio"] == pd.Timestamp(
        "2025-01-01"
    )

    assert (
        evento["data_ultima_observacao"]
        == pd.Timestamp("2025-01-02")
    )

    assert evento["persistencia"] == 2.0

    assert evento["recorrencia"] == 0

    assert evento.geometry is not None
    assert not evento.geometry.is_empty