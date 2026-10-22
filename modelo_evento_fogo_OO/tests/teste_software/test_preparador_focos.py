import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Point

from evento_fogo.processamento.preparador_focos import PreparadorFocos


def criar_geojson(registros, crs="EPSG:4326"):
    gdf = gpd.GeoDataFrame(
        registros,
        geometry="geometry",
        crs=crs,
    )

    return gdf.to_json()


def test_preparar_focos_retorna_geodataframe_e_data_processamento():
    geojson = criar_geojson(
        [
            {
                "id": "foco_1",
                "data": "2024-08-01T10:30:00",
                "satelite": 4,
                "geometry": Point(-47.0, -22.0),
            }
        ]
    )

    preparador = PreparadorFocos(
        focos_geojson=geojson,
        agrupar_apenas_por_dia=True,
        crs_saida="EPSG:5880",
    )

    gdf, data_processamento = preparador.preparar_focos()

    assert isinstance(gdf, gpd.GeoDataFrame)
    assert isinstance(data_processamento, pd.Timestamp)
    assert len(gdf) == 1
    assert gdf.crs.to_epsg() == 5880


def test_preparar_focos_preserva_atributos_validos():
    geojson = criar_geojson(
        [
            {
                "id": "foco_1",
                "data": "2024-08-01T10:30:00",
                "satelite": 4,
                "geometry": Point(-47.0, -22.0),
            }
        ]
    )

    gdf, _ = PreparadorFocos(
        focos_geojson=geojson,
        agrupar_apenas_por_dia=False,
    ).preparar_focos()

    foco = gdf.iloc[0]

    assert foco["id"] == "foco_1"
    assert foco["satelite"] == 4
    assert isinstance(foco["data"], pd.Timestamp)
    assert foco.geometry is not None


def test_preparar_focos_normaliza_horarios_quando_agregacao_diaria_esta_ativa():
    geojson = criar_geojson(
        [
            {
                "id": "foco_1",
                "data": "2024-08-01T10:30:00",
                "satelite": 4,
                "geometry": Point(-47.0, -22.0),
            },
            {
                "id": "foco_2",
                "data": "2024-08-01T18:45:00",
                "satelite": 4,
                "geometry": Point(-47.1, -22.1),
            },
        ]
    )

    gdf, data_processamento = PreparadorFocos(
        focos_geojson=geojson,
        agrupar_apenas_por_dia=True,
    ).preparar_focos()

    data_esperada = pd.Timestamp("2024-08-01")

    assert (gdf["data"] == data_esperada).all()
    assert data_processamento == data_esperada


def test_preparar_focos_preserva_horario_quando_agregacao_diaria_esta_desativada():
    geojson = criar_geojson(
        [
            {
                "id": "foco_1",
                "data": "2024-08-01T10:30:00",
                "satelite": 4,
                "geometry": Point(-47.0, -22.0),
            }
        ]
    )

    gdf, data_processamento = PreparadorFocos(
        focos_geojson=geojson,
        agrupar_apenas_por_dia=False,
    ).preparar_focos()

    data_esperada = pd.Timestamp("2024-08-01T10:30:00")

    assert gdf.iloc[0]["data"] == data_esperada
    assert data_processamento == data_esperada


def test_preparar_focos_remove_registros_com_campos_obrigatorios_nulos():
    geojson = criar_geojson(
        [
            {
                "id": "foco_1",
                "data": "2024-08-01T10:30:00",
                "satelite": 4,
                "geometry": Point(-47.0, -22.0),
            },
            {
                "id": None,
                "data": "2024-08-01T12:00:00",
                "satelite": 4,
                "geometry": Point(-47.1, -22.1),
            },
        ]
    )

    gdf, _ = PreparadorFocos(
        focos_geojson=geojson,
        agrupar_apenas_por_dia=True,
    ).preparar_focos()

    assert len(gdf) == 1
    assert gdf.iloc[0]["id"] == "foco_1"


def test_preparar_focos_remove_registros_com_data_invalida():
    geojson = criar_geojson(
        [
            {
                "id": "foco_1",
                "data": "2024-08-01T10:30:00",
                "satelite": 4,
                "geometry": Point(-47.0, -22.0),
            },
            {
                "id": "foco_2",
                "data": "data_invalida",
                "satelite": 4,
                "geometry": Point(-47.1, -22.1),
            },
        ]
    )

    gdf, _ = PreparadorFocos(
        focos_geojson=geojson,
    ).preparar_focos()

    assert len(gdf) == 1
    assert gdf.iloc[0]["id"] == "foco_1"


def test_preparar_focos_rejeita_entrada_sem_coluna_obrigatoria():
    geojson = criar_geojson(
        [
            {
                "id": "foco_1",
                "data": "2024-08-01T10:30:00",
                "geometry": Point(-47.0, -22.0),
            }
        ]
    )

    preparador = PreparadorFocos(
        focos_geojson=geojson,
    )

    with pytest.raises(
        ValueError,
        match="Faltam colunas obrigatórias",
    ):
        preparador.preparar_focos()


def test_preparar_focos_rejeita_entrada_sem_focos_validos():
    geojson = criar_geojson(
        [
            {
                "id": None,
                "data": "data_invalida",
                "satelite": None,
                "geometry": None,
            }
        ]
    )

    preparador = PreparadorFocos(
        focos_geojson=geojson,
    )

    with pytest.raises(
        ValueError,
        match="A entrada não possui focos válidos",
    ):
        preparador.preparar_focos()


def test_preparar_focos_rejeita_focos_de_dias_diferentes_na_agregacao_diaria():
    geojson = criar_geojson(
        [
            {
                "id": "foco_1",
                "data": "2024-08-01T10:00:00",
                "satelite": 4,
                "geometry": Point(-47.0, -22.0),
            },
            {
                "id": "foco_2",
                "data": "2024-08-02T10:00:00",
                "satelite": 4,
                "geometry": Point(-47.1, -22.1),
            },
        ]
    )

    preparador = PreparadorFocos(
        focos_geojson=geojson,
        agrupar_apenas_por_dia=True,
    )

    with pytest.raises(
        ValueError,
        match="exatamente um período de processamento",
    ):
        preparador.preparar_focos()


def test_preparar_focos_reprojeta_para_crs_configurado():
    geojson = criar_geojson(
        [
            {
                "id": "foco_1",
                "data": "2024-08-01T10:00:00",
                "satelite": 4,
                "geometry": Point(-47.0, -22.0),
            }
        ]
    )

    gdf, _ = PreparadorFocos(
        focos_geojson=geojson,
        crs_saida="EPSG:5880",
    ).preparar_focos()

    assert gdf.crs.to_epsg() == 5880