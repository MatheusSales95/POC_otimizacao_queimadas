from io import StringIO
import geopandas as gpd
import pandas as pd
from typing import TypeAlias
GeoJSON: TypeAlias = str

class PreparadorFocos:
    def __init__(
        self,
        focos_geojson: GeoJSON,
        agrupar_apenas_por_dia: bool = True,
        crs_saida: str = "EPSG:5880",
    ):
        self.focos_geojson = focos_geojson
        self.agrupar_apenas_por_dia = agrupar_apenas_por_dia
        self.crs_saida = crs_saida

    def _ler_geojson(self) -> gpd.GeoDataFrame:
        return gpd.read_file(
            StringIO(self.focos_geojson)
        )

    @staticmethod
    def _validar_colunas(gdf: gpd.GeoDataFrame) -> None:
        colunas_necessarias = {
            "id",
            "data",
            "satelite",
            "geometry",
        }

        faltantes = colunas_necessarias - set(gdf.columns)

        if faltantes:
            raise ValueError(
                "Faltam colunas obrigatórias nos focos: "
                f"{sorted(faltantes)}"
            )

    @staticmethod
    def _converter_datas(
        gdf: gpd.GeoDataFrame,
    ) -> gpd.GeoDataFrame:
        gdf = gdf.copy()

        gdf["data"] = pd.to_datetime(
            gdf["data"],
            errors="coerce",
        )

        return gdf

    @staticmethod
    def _remover_registros_invalidos(
        gdf: gpd.GeoDataFrame,
    ) -> gpd.GeoDataFrame:
        return gdf.dropna(
            subset=[
                "id",
                "data",
                "satelite",
                "geometry",
            ]
        ).copy()

    def _aplicar_granularidade(
        self,
        gdf: gpd.GeoDataFrame,
    ) -> gpd.GeoDataFrame:
        gdf = gdf.copy()

        if self.agrupar_apenas_por_dia:
            gdf["data"] = gdf["data"].dt.floor("D")

        return gdf

    @staticmethod
    def _obter_data_processamento(
        gdf: gpd.GeoDataFrame,
    ) -> pd.Timestamp:
        datas = gdf["data"].dropna().unique()

        if len(datas) != 1:
            raise ValueError(
                "A entrada de focos deve conter dados "
                "de exatamente um período de processamento."
            )

        return pd.Timestamp(datas[0])

    def preparar_focos(
        self,
    ) -> tuple[gpd.GeoDataFrame, pd.Timestamp]:
        gdf = self._ler_geojson()

        self._validar_colunas(gdf)

        gdf = self._converter_datas(gdf)
        gdf = self._remover_registros_invalidos(gdf)
        gdf = self._aplicar_granularidade(gdf)

        if gdf.empty:
            raise ValueError(
                "A entrada não possui focos válidos para processamento."
            )

        data_processamento = self._obter_data_processamento(gdf)

        return gdf.to_crs(self.crs_saida).reset_index(drop=True), data_processamento