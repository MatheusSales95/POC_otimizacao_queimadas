from datetime import datetime

from shapely.geometry import Point, Polygon
import geopandas as gpd

from evento_fogo.processamento.bufferizador_focos import Bufferizador




def test_bufferizar_focos_retorna_geometria_poligonal():

    gdf_foco = gpd.GeoDataFrame(
        [
            {
                "id": "foco_1",
                "data": datetime(2024, 8, 1, 10, 0),
                "satelite": "GOES-16",
                "geometry": Point(-47.0, -22.0),
            }
        ],
        geometry="geometry",
        crs="EPSG:4326",
    ).to_crs("EPSG:5880")

    buffer_por_satelite = {
        "GOES-16": 1300,
    }

    bufferizador = Bufferizador(
        gdf=gdf_foco,
        buffer_por_satelite=buffer_por_satelite,
        tipo_buffer="quadrado",
    )

    gdf_buffer = bufferizador.bufferizar_focos()

    assert len(gdf_buffer) == 1
    assert isinstance(
        gdf_buffer.iloc[0].geometry,
        Polygon,
    )
    assert gdf_buffer.iloc[0]["id"] == "foco_1"
    assert (
        gdf_buffer.iloc[0]["satelite"]
        == "GOES-16"
    )