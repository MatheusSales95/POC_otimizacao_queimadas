import pandas as pd
import geopandas as gpd
from shared.models.evento import Eventos as EventoFogo
from shared.models.focos import Focos as Foco
from typing import TypeAlias
GeoJSON: TypeAlias = str
from shapely import Point


class MapeadorEventos:
    def __init__(self, crs_saida="EPSG:5880"):
        self.crs_saida = crs_saida # aqui pode se converter listas para eventos nos dois crs usados.
    
    #-------------------------------------------------------------------------------------
    # Auxiliar: Construtor de registros para mapeamentos lista_eventos -> gdf_eventos
    #-------------------------------------------------------------------------------------
    def _construir_registros(
            self,
            eventos: list[EventoFogo],
            incluir_referencia_evento: bool,
            incluir_quantidade_focos: bool,
    ) -> list[dict]:
        registros = []

        for evento in eventos:
            registro = {
                "id_evento": evento.id_evento,
                "focos": list(evento.focos) if evento.focos else [],
                "data_inicio": evento.data_inicio,
                "data_ultima_observacao": evento.data_ultima_observacao,
                "data_fim": evento.data_fim,
                "area_inicio": evento.area_inicio,
                "area_fim": evento.area_fim,
                "status": evento.status,
                "id_evento_absorvedor": evento.id_evento_absorvedor,
                "ids_focos": evento.obter_ids_focos(),
                "geometry": evento.geom,
                "persistencia": evento.persistencia,
                "predecessores": [
                    predecessor.id_evento
                    for predecessor in evento.predecessores
                ],
                "recorrencia": evento.recorrencia,
                "duracao": str(evento.calcular_duracao()) if evento.calcular_duracao() is not None else None,
            }

            if incluir_referencia_evento:
                registro["_evento"] = evento

            if incluir_quantidade_focos:
                registro["quantidade_focos"] = evento.quantidade_focos()


            registros.append(registro)

        return registros


    #-------------------------------------------------------------------------------------
    # Auxiliar: Construtor de geodataframes para mapeamentos lista_eventos -> gdf_eventos
    #-------------------------------------------------------------------------------------
    def _construir_gdf(
        self,
        registros: list[dict],
    ) -> gpd.GeoDataFrame:
        return gpd.GeoDataFrame(
            registros,
            geometry="geometry",
            crs=self.crs_saida,
    )


    #-------------------------------------------------------------------------------------
    # Mapear lista_eventos -> gdf_eventos para processamento temporal
    #-------------------------------------------------------------------------------------
    def mapear_lista_eventos_para_gdf_processamento_temporal(
        self,
        eventos: list[EventoFogo],
    ) -> gpd.GeoDataFrame:
        registros = self._construir_registros(
            eventos,
            incluir_referencia_evento=True,
            incluir_quantidade_focos=False
        )

        return self._construir_gdf(registros)



    #-------------------------------------------------------------------------------------
    # Mapear lista_eventos finais atualizada para -> geojson de saída
    #-------------------------------------------------------------------------------------
    def mapear_lista_eventos_finais_para_gdf(
        self,
        eventos: list[EventoFogo],
    ) -> gpd.GeoDataFrame:
        registros = self._construir_registros(
            eventos,
            incluir_referencia_evento=False,
            incluir_quantidade_focos=True
        )

        return self._construir_gdf(registros)
    
   
    #-------------------------------------------------------------------------------------
    # Mapear geojason (eventos bco ) para lista de eventos 
    #-------------------------------------------------------------------------------------  
    def mapear_geojson_banco_para_lista_eventos(
        self,
        gdf_agregado: gpd.GeoDataFrame,
    ) -> list[EventoFogo]:

        eventos = []

        for _, linha in gdf_agregado.iterrows():
            data_fim = linha.get("data_fim", None)

            if pd.isna(data_fim):
                data_fim = None

            evento = EventoFogo(
                id_evento=linha.get("id_evento"),
                focos = list(linha.get("focos",[])),
                data_inicio=linha["data_inicio"],
                data_ultima_observacao=linha["data_ultima_observacao"],
                data_fim=data_fim,
                area_inicio=linha.get("area_inicio"),
                area_fim=linha.get("area_fim"),
                status=linha.get("status"),
                id_evento_absorvedor=linha.get(
                    "id_evento_absorvedor",
                    None,
                ),
                persistencia=linha.get("persistencia"),
                recorrencia=linha.get("recorrencia", 0),
                geometria=linha.geometry
            )

            eventos.append(evento)

        return eventos