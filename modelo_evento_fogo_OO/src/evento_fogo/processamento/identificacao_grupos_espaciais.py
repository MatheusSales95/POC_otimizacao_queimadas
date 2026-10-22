import geopandas as gpd
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components


class IdentificadorGruposEspaciais:

    @staticmethod
    def _identificar_componentes(
        grupo_data: gpd.GeoDataFrame,
    ):
        quantidade_geometrias = len(grupo_data)

        linhas = list(range(quantidade_geometrias))
        colunas = list(range(quantidade_geometrias))

        indice_espacial = grupo_data.sindex

        for i in range(quantidade_geometrias):
            geometria_i = grupo_data.at[i, "geometry"]

            candidatos = indice_espacial.query(
                geometria_i
            )

            for j in candidatos:
                if j <= i:
                    continue

                geometria_j = grupo_data.at[j, "geometry"]

                if geometria_i.intersects(geometria_j):
                    linhas.extend([i, j])
                    colunas.extend([j, i])

        matriz_adjacencia = csr_matrix(
            (
                [1] * len(linhas),
                (linhas, colunas),
            ),
            shape=(
                quantidade_geometrias,
                quantidade_geometrias,
            ),
        )

        _, componentes = connected_components(
            csgraph=matriz_adjacencia,
            directed=False,
            return_labels=True,
        )

        return componentes

    def identificar_grupos(
        self,
        gdf_bufferizado: gpd.GeoDataFrame,
    ) -> list[gpd.GeoDataFrame]:

        if gdf_bufferizado.empty:
            return []

        colunas_necessarias = {
            "_foco",
            "data",
            "geometry",
        }

        colunas_faltantes = (
            colunas_necessarias
            - set(gdf_bufferizado.columns)
        )

        if colunas_faltantes:
            raise ValueError(
                "Faltam colunas necessárias para a identificação "
                f"dos grupos espaciais: {sorted(colunas_faltantes)}"
            )

        grupos_espaciais = []

        for _, grupo_data in gdf_bufferizado.groupby("data"):
            grupo_data = (
                grupo_data
                .copy()
                .reset_index(drop=True)
            )

            componentes = self._identificar_componentes(
                grupo_data
            )

            grupo_data["_componente_espacial"] = componentes

            for _, grupo_componente in grupo_data.groupby(
                "_componente_espacial"
            ):
                grupo_componente = (
                    grupo_componente
                    .drop(columns="_componente_espacial")
                    .reset_index(drop=True)
                )

                grupos_espaciais.append(
                    grupo_componente
                )

        return grupos_espaciais