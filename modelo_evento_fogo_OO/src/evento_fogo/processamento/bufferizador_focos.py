import geopandas as gpd
from shapely.geometry import Polygon

class Bufferizador:
    def __init__(
            self, 
            gdf: gpd.GeoDataFrame, 
            buffer_por_satelite: int, 
            tipo_buffer: str
            ) -> gpd.GeoDataFrame:
        self.gdf = gdf
        self.buffer_por_satelite = buffer_por_satelite
        self.tipo_buffer = tipo_buffer

    def criar_geometria_bufferizada(
            self,
            linha,
            raio_buffer
            ) -> Polygon:
  
        if self.tipo_buffer == "quadrado":
            return linha.geometry.buffer(raio_buffer, cap_style=3)

        if self.tipo_buffer == "circular":
            return linha.geometry.buffer(raio_buffer)

        raise ValueError(f"Tipo de buffer inválido: {self.tipo_buffer}")


    def bufferizar_focos(self) -> gpd.GeoDataFrame:
        gdf_bufferizado = self.gdf.copy()
        geometrias_bufferizadas = []
  
        for _, linha in gdf_bufferizado.iterrows():
            satelite = linha["satelite"]
            raio_buffer = self.buffer_por_satelite[satelite]
            geometria_bufferizada = self.criar_geometria_bufferizada(linha=linha, raio_buffer=raio_buffer)
            geometrias_bufferizadas.append(geometria_bufferizada)

        gdf_bufferizado["geometry"] = geometrias_bufferizadas

        return gdf_bufferizado