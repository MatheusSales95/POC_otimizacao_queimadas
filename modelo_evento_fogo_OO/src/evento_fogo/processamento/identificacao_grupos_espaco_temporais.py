import pandas as pd
import geopandas as gpd
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components
from shared.models.evento import Eventos as EventoFogo


class IdentificadorGruposEspacoTemporais:

    def __init__(self, intervalo_dias: int = 7):
        self.intervalo_dias = intervalo_dias

    def _preparar_gdf_para_identificacao(
        self,
        gdf: gpd.GeoDataFrame,
    ) -> gpd.GeoDataFrame:

        colunas_necessarias = {
            "_evento",
            "data_ultima_observacao",
            "geometry",
        }

        colunas_faltantes = (
            colunas_necessarias
            - set(gdf.columns)
        )

        if colunas_faltantes:
            raise ValueError(
                "Faltam as colunas necessárias para identificar "
                f"os grupos espaço-temporais: {sorted(colunas_faltantes)}"
            )

        df = gdf.copy()

        df["data"] = pd.to_datetime(
            df["data_ultima_observacao"],
            errors="coerce",
        )

        df = df.dropna(
            subset=[
                "_evento",
                "data",
                "geometry",
            ]
        ).copy()

        return (
            df.sort_values(
                "data",
                ascending=False,
            )
            .reset_index(drop=True)
        )

    def _construir_matriz_conectividade(
        self,
        df: gpd.GeoDataFrame,
        ) -> tuple[csr_matrix, list[tuple[int, int]]]:

        n = len(df)

        linhas = list(range(n))
        colunas = list(range(n))
        conexoes = []

        sindex = df.sindex

        for i in range(n):
            data_i = pd.Timestamp(df.at[i, "data"])
            geom_i = df.at[i, "geometry"]

            candidatos_espaciais = set(sindex.query(geom_i))

            for j in candidatos_espaciais:
                if j <= i:
                    continue

                data_j = pd.Timestamp(df.at[j, "data"])
                delta_dias = (data_i - data_j).days

                if delta_dias < 0:
                    continue

                if delta_dias > self.intervalo_dias:
                    continue

                geom_j = df.at[j, "geometry"]

                if geom_i.intersects(geom_j):
                    linhas.extend([i, j])
                    colunas.extend([j, i])

                    conexoes.append((i, j))
            

        matriz = csr_matrix(
            ([1] * len(linhas), (linhas, colunas)),
            shape=(n, n),
        )

        return matriz, conexoes


    def _agrupar_eventos_por_componente(
        self,
        gdf: gpd.GeoDataFrame,
        labels,
    ) -> list[list[EventoFogo]]:

        grupos: dict[int, list[EventoFogo]] = {}

        for label, evento in zip(labels, gdf["_evento"]):
            grupos.setdefault(int(label), []).append(evento)

        return list(grupos.values())
  

    def identificar_grupos(
        self,
        gdf_para_processamento_temporal: gpd.GeoDataFrame,
    ) -> list[list[EventoFogo]]:

        gdf = self._preparar_gdf_para_identificacao(
            gdf_para_processamento_temporal
        )

        if gdf.empty:
            return []

        matriz, _ = self._construir_matriz_conectividade(
            gdf
        )

        _, labels = connected_components(
            csgraph=matriz,
            directed=False,
            return_labels=True,
        )

        return self._agrupar_eventos_por_componente(
            gdf=gdf,
            labels=labels,
        )

