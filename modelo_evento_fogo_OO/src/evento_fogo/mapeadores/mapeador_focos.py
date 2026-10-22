#from typing import List
import geopandas as gpd
from shared.models.focos import Focos as Foco

class MapeadorFocos:
    def __init__(self, crs_saida="EPSG:5880"):
        self.crs_saida = crs_saida
    
    
    def mapear_gdf_para_lista(self, gdf: str) -> list[Foco]:
        focos = []

        for _, linha in gdf.iterrows():
            foco = Foco(
                id_foco = str(linha["id"]),
                data = linha["data"],
                geometria = linha.geometry,
                id_satelite = linha["satelite"],
            )

            focos.append(foco)

        return focos

    def _mapear_foco_para_linha(self,foco:Foco) -> dict:
        return {
            "_foco": foco,
            "id": foco.id_foco,
            "data": foco.data,
            "satelite": foco.id_satelite,
            "geometry": foco.geometria,
        }
    
    def mapear_lista_para_gdf(self,focos: list[Foco]) -> gpd.GeoDataFrame:
        
        linhas = [self._mapear_foco_para_linha(foco) for foco in focos]   
            
        return gpd.GeoDataFrame(
                linhas,
                geometry = "geometry",
                crs=self.crs_saida
            ) 