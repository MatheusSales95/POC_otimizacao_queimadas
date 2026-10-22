import geopandas as gpd
from shapely.ops import unary_union
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components

class AgregadorEspacialFocos:
    def __init__(self, gdf_bufferizado:gpd.GeoDataFrame):
        self.gdf = gdf_bufferizado

    def _ordenar_ids(self,ids):
        """
        Ordena IDs de forma determinística.

        Tenta ordenar como inteiros. Caso não seja possível,
        ordena como string.
        """
        ids_str = [str(i) for i in ids]

        try:
            return sorted(ids_str, key=lambda x: int(x))
        except Exception:
            return sorted(ids_str)


    def agregar_espacialmente(self)-> gpd.GeoDataFrame:

        gdf_bufferizado = self.gdf.copy()

        # Checa de geodataframe está vazio 
        if len(gdf_bufferizado) == 0:
            return gpd.GeoDataFrame(
                columns=[
                    "data",
                    "area_geom",
                    "ids_focos",
                    "geometry"
                ],
                geometry="geometry",
                crs=gdf_bufferizado.crs
            )
        
        resultados = []

        for data_ref, grupo_data in gdf_bufferizado.groupby("data"):
            grupo_data = grupo_data.copy().reset_index(drop=True)

            n = len(grupo_data)

            if n == 1:
                geom_final = grupo_data.iloc[0].geometry
                area_geom = round(geom_final.area/1_000_000,2) #transformando em km² e definindo casas decimais
                id_foco = str(grupo_data.iloc[0]["id"])

                resultados.append({
                    "data": data_ref,
                    "area_geom": area_geom,
                    "ids_focos": [id_foco],
                    "geometry": geom_final
                })
                continue

            linhas = list(range(n))
            colunas = list(range(n))

            sindex = grupo_data.sindex

            for i in range(n):
                geom_i = grupo_data.at[i, "geometry"]

                candidatos = list(sindex.query(geom_i))

                for j in candidatos:
                    if j <= i:
                        continue

                    geom_j = grupo_data.at[j, "geometry"]

                    if geom_i.intersects(geom_j):
                        linhas.extend([i, j])
                        colunas.extend([j, i])

            matriz = csr_matrix(
                ([1] * len(linhas), (linhas, colunas)),
                shape=(n, n)
            )

            
            _, labels = connected_components(
                csgraph=matriz,
                directed=False,
                return_labels=True
            )

            grupo_data["componente"] = labels

            for _, grupo_comp in grupo_data.groupby("componente"):
                grupo_comp = grupo_comp.copy().reset_index(drop=True)

                ids_focos = self._ordenar_ids(grupo_comp["id"].tolist())

                geom_final = unary_union(grupo_comp.geometry.tolist())
                area_geom = round(geom_final.area/1_000_000,2) #transformando em km² e definindo casas decimais

                resultados.append({
                    "data": data_ref,
                    "area_geom": area_geom,
                    "ids_focos": ids_focos,
                    "geometry": geom_final
                })

        gdf_resultado = gpd.GeoDataFrame(
            resultados,
            geometry="geometry",
            crs=gdf_bufferizado.crs # Mantém o crs de entrada (métrico)
        )

        return gdf_resultado.reset_index(drop=True)