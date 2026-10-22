from io import StringIO
from typing import TypeAlias

import geopandas as gpd
import pandas as pd

from evento_fogo.mapeadores.mapeador_eventos import MapeadorEventos
from shared.models.evento import Eventos as EventoFogo


GeoJSON: TypeAlias = str


class AnalisadorRecorrencia:

    def __init__(
        self,
        eventos_geojson: GeoJSON,
        data_analise,
        janela_operacional_dias: int = 7,
        horizonte_anos: int = 2,
    ):
        self.eventos_geojson = eventos_geojson
        self.data_analise = pd.Timestamp(data_analise)
        self.janela_operacional_dias = janela_operacional_dias
        self.horizonte_anos = horizonte_anos

    def _ler_geojson(self) -> gpd.GeoDataFrame:
        return gpd.read_file(
            StringIO(self.eventos_geojson)
        )

    @staticmethod
    def _validar_colunas(
        gdf: gpd.GeoDataFrame,
    ) -> None:
        colunas_necessarias = {
            "id_evento",
            "data_inicio",
            "data_fim",
            "data_ultima_observacao",
            "predecessores",
            "geometry",
        }

        colunas_faltantes = (
            colunas_necessarias
            - set(gdf.columns)
        )

        if colunas_faltantes:
            raise ValueError(
                "Faltam colunas necessárias para a análise "
                f"de recorrência: {sorted(colunas_faltantes)}"
            )

    @staticmethod
    def _converter_datas(
        gdf: gpd.GeoDataFrame,
    ) -> gpd.GeoDataFrame:
        gdf = gdf.copy()

        for coluna in (
            "data_inicio",
            "data_fim",
            "data_ultima_observacao",
        ):
            gdf[coluna] = pd.to_datetime(
                gdf[coluna],
                errors="coerce",
            )

        return gdf

    @staticmethod
    def _normalizar_ids_recorrentes(
        gdf: gpd.GeoDataFrame,
    ) -> gpd.GeoDataFrame:
        gdf = gdf.copy()

        def normalizar(valor):
            if isinstance(valor, (list, tuple, set)):
                return [
                    str(id_evento)
                    for id_evento in valor
                ]

            return []

        gdf["predecessores"] = (
            gdf["predecessores"]
            .apply(normalizar)
        )

        return gdf

    def _preparar_dados(
        self,
    ) -> gpd.GeoDataFrame:
        gdf = self._ler_geojson()

        self._validar_colunas(gdf)

        gdf = self._converter_datas(gdf)
        gdf = self._normalizar_ids_recorrentes(gdf)

        gdf = gdf.dropna(
            subset=[
                "id_evento",
                "data_inicio",
                "data_ultima_observacao",
                "geometry",
            ]
        ).copy()

        gdf["id_evento"] = (
            gdf["id_evento"]
            .astype(str)
        )

        return gdf.reset_index(drop=True)

    def _selecionar_eventos_alvo(
        self,
        gdf: gpd.GeoDataFrame,
    ) -> gpd.GeoDataFrame:
        inicio_periodo = (
            self.data_analise
            - pd.DateOffset(months=1)
        )

        fim_periodo = self.data_analise

        mascara = (
            gdf["data_inicio"].ge(inicio_periodo)
            & gdf["data_inicio"].lt(fim_periodo)
        )

        return gdf.loc[mascara].copy()

    @staticmethod
    def _obter_fim_referencia(
        evento: pd.Series,
    ) -> pd.Timestamp:
        if pd.notna(evento["data_fim"]):
            return pd.Timestamp(
                evento["data_fim"]
            )

        return pd.Timestamp(
            evento["data_ultima_observacao"]
        )

    def _esta_dentro_horizonte_historico(
        self,
        alvo: pd.Series,
        candidato: pd.Series,
    ) -> bool:
        limite_historico = (
            pd.Timestamp(alvo["data_inicio"])
            - pd.DateOffset(
                years=self.horizonte_anos
            )
        )

        return (
            pd.Timestamp(candidato["data_inicio"])
            >= limite_historico
        )

    def _esta_fora_janela_operacional(
        self,
        alvo: pd.Series,
        candidato: pd.Series,
    ) -> bool:
        data_inicio_alvo = pd.Timestamp(
            alvo["data_inicio"]
        )

        fim_candidato = (
            self._obter_fim_referencia(
                candidato
            )
        )

        limite = (
            data_inicio_alvo
            - pd.Timedelta(
                days=self.janela_operacional_dias
            )
        )

        return fim_candidato < limite

    def _eh_candidato_recorrente(
        self,
        alvo: pd.Series,
        candidato: pd.Series,
    ) -> bool:
        if (
            candidato["id_evento"]
            == alvo["id_evento"]
        ):
            return False

        if (
            pd.Timestamp(candidato["data_inicio"])
            >= pd.Timestamp(alvo["data_inicio"])
        ):
            return False

        if not self._esta_dentro_horizonte_historico(
            alvo,
            candidato,
        ):
            return False

        if not self._esta_fora_janela_operacional(
            alvo,
            candidato,
        ):
            return False

        return alvo.geometry.intersects(
            candidato.geometry
        )

    def _identificar_recorrencias(
        self,
        gdf: gpd.GeoDataFrame,
        alvos: gpd.GeoDataFrame,
    ) -> list[int]:
        indices_atualizados = []

        indice_espacial = gdf.sindex

        for indice_alvo, alvo in alvos.iterrows():
            ids_predecessores = set(
                alvo["predecessores"]
            )

            indices_candidatos = (
                indice_espacial.query(
                    alvo.geometry
                )
            )

            houve_alteracao = False

            for indice_candidato in indices_candidatos:
                candidato = gdf.iloc[
                    indice_candidato
                ]

                if not self._eh_candidato_recorrente(
                    alvo,
                    candidato,
                ):
                    continue

                id_recorrente = str(
                    candidato["id_evento"]
                )

                if id_recorrente in ids_predecessores:
                    continue

                ids_predecessores.add(
                    id_recorrente
                )

                houve_alteracao = True

            if houve_alteracao:
                gdf.at[
                    indice_alvo,
                    "predecessores",
                ] = sorted(ids_predecessores)

                indices_atualizados.append(
                    indice_alvo
                )

        return indices_atualizados

    def analisar(
        self,
    ) -> list[EventoFogo]:
        gdf = self._preparar_dados()

        if gdf.empty:
            return []

        alvos = self._selecionar_eventos_alvo(
            gdf
        )

        if alvos.empty:
            return []

        indices_atualizados = (
            self._identificar_recorrencias(
                gdf,
                alvos,
            )
        )

        if not indices_atualizados:
            return []

        gdf_atualizados = (
            gdf.loc[
                indices_atualizados
            ]
            .copy()
            .reset_index(drop=True)
        )

        return (
            MapeadorEventos()
            .mapear_geojson_banco_para_lista_eventos(
                gdf_atualizados
            )
        )