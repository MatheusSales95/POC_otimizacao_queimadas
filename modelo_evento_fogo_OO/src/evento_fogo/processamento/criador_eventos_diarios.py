import geopandas as gpd
from shapely.ops import unary_union

from shared.models.evento import Eventos as EventoFogo
from shared.models.focos import Focos as Foco


class CriadorEventosDiarios:

    @staticmethod
    def _ordenar_focos(
        focos: list[Foco],
    ) -> list[Foco]:

        try:
            return sorted(
                focos,
                key=lambda foco: int(foco.id_foco),
            )
        except (TypeError, ValueError):
            return sorted(
                focos,
                key=lambda foco: str(foco.id_foco),
            )

    def criar_eventos(
        self,
        grupos_espaciais: list[gpd.GeoDataFrame],
    ) -> list[EventoFogo]:

        eventos_diarios = []

        for grupo in grupos_espaciais:
            if grupo.empty:
                raise ValueError(
                    "Um grupo espacial não pode estar vazio."
                )

            colunas_necessarias = {
                "_foco",
                "data",
                "geometry",
            }

            colunas_faltantes = (
                colunas_necessarias
                - set(grupo.columns)
            )

            if colunas_faltantes:
                raise ValueError(
                    "Faltam colunas necessárias para criar o "
                    f"evento diário: {sorted(colunas_faltantes)}"
                )

            datas = grupo["data"].dropna().unique()

            if len(datas) != 1:
                raise ValueError(
                    "Todos os focos de um grupo espacial devem "
                    "pertencer ao mesmo período."
                )

            focos = self._ordenar_focos(
                grupo["_foco"].tolist()
            )

            geom = unary_union(
                grupo.geometry.tolist()
            )

            area = round(geom.area/1_000_000,2) #transformando em km² e definindo casas decimais
            data_referencia = datas[0]

            evento = EventoFogo(
                id_evento=None,
                focos=focos,
                data_inicio=data_referencia,
                data_ultima_observacao=data_referencia,
                area_inicio=area
            )
            evento.geom = geom

            eventos_diarios.append(evento)

        return eventos_diarios