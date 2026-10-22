from datetime import datetime

import geopandas as gpd
from shapely.geometry import Point


from evento_fogo.mapeadores.mapeador_focos import MapeadorFocos
from shared.models.focos import Focos as Foco


def test_mapear_gdf_para_lista_retorna_objetos_foco():
    gdf = gpd.GeoDataFrame(
        {
            "id": ["foco_1"],
            "data": [datetime(2024, 8, 1, 10, 0)],
            "satelite": [4],
            "geometry": [Point(500000, 7500000)],
        },
        geometry="geometry",
        crs="EPSG:5880",
    )

    mapeador = MapeadorFocos()

    focos = mapeador.mapear_gdf_para_lista(gdf)

    assert isinstance(focos, list)
    assert len(focos) == 1
    assert isinstance(focos[0], Foco)


def test_mapear_gdf_para_lista_preserva_atributos():
    geometria = Point(500000, 7500000)
    data = datetime(2024, 8, 1, 10, 0)

    gdf = gpd.GeoDataFrame(
        {
            "id": ["foco_1"],
            "data": [data],
            "satelite": [4],
            "geometry": [geometria],
        },
        geometry="geometry",
        crs="EPSG:5880",
    )

    foco = MapeadorFocos().mapear_gdf_para_lista(gdf)[0]

    assert foco.id_foco == "foco_1"
    assert foco.data == data
    assert foco.id_satelite == 4
    assert foco.geometria.equals(geometria)


def test_mapear_lista_para_gdf_retorna_geodataframe():
    foco = Foco(
        id_foco="foco_1",
        data=datetime(2024, 8, 1, 10, 0),
        geometria=Point(500000, 7500000),
        id_satelite=4,
    )

    mapeador = MapeadorFocos(crs_saida="EPSG:5880")

    gdf = mapeador.mapear_lista_para_gdf([foco])

    assert isinstance(gdf, gpd.GeoDataFrame)
    assert len(gdf) == 1
    assert gdf.crs.to_epsg() == 5880


def test_mapear_lista_para_gdf_preserva_atributos():
    geometria = Point(500000, 7500000)
    data = datetime(2024, 8, 1, 10, 0)

    foco = Foco(
        id_foco="foco_1",
        data=data,
        geometria=geometria,
        id_satelite=4,
    )

    gdf = MapeadorFocos().mapear_lista_para_gdf([foco])

    linha = gdf.iloc[0]

    assert linha["id"] == foco.id_foco
    assert linha["data"] == foco.data
    assert linha["satelite"] == foco.id_satelite
    assert linha.geometry.equals(foco.geometria)
    assert linha["_foco"] is foco
