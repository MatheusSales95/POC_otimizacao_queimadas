import pandas as pd 
import geopandas as gpd 
from evento_fogo.integracao.integrador import integrar_eventos as integrador
import yaml
from datetime import datetime, timedelta
import time

from shared.models.evento import Eventos
from shapely.geometry import shape
from shared.schemas import EventosAdapter
from shared.config import config_keys

gdf_focos = gpd.read_file(f"")


def executarProcessamento(data_inicio, data_fim, raio):
    """Executa o processamento de eventos para um determinado período."""
    
    #transformar string de data no formato data
    data_ini = datetime.fromisoformat(data_inicio).date() 
    data_end = datetime.fromisoformat(data_fim).date()

    #novo raio do AG
    changeRaio(raio)

    delta = data_end - data_ini
    #lista de dias no periodo
    list_days = [data_ini + timedelta(days=i) for i in range(delta.days + 1)]
    gdf_eventos = gpd.GeoDataFrame()
    
    for data in list_days:
        #focos do dia
        focos_day = gdf_focos[(gdf_focos['data_hora']>= f"{data_ini} 00:00:00") & (gdf_focos['data_hora']<= f"{data} 23:59:59")]
        
        if not gdf_eventos.empty:
            gdf_eventos.set_crs(epsg=4326, inplace=True)
            gdf_eventos.to_crs(epsg=5880, inplace=True) 

            gdf_eventos = [gdf_eventos[gdf_eventos['data_inicio'] >= data_ini+timedelta(days=7) & gdf_eventos['data_inicio'] <= data_ini]]
        
        eventos_process = process(focos_day, gdf_eventos)

        if eventos_process is not None and not eventos_process.empty:
            gdf_eventos = pd.concat([gdf_eventos, eventos_process], ignore_index=True)
            
    return gdf_eventos

def process(focos, eventos):
    eventos = integrador(focos, eventos)
    
    return eventos

def changeRaio (raioAG):
    with open("shared/config_keys.yaml", "r") as f: 
        yaml_data = yaml.safe_load(f)
        satelite_data = yaml_data["satelite_data"]
        for satelite in satelite_data:
            if satelite["satelite"] in ["GOES-13", "GOES-16", "GOES-19", "GOES-12", "GOES-08", "GOES-10"]:
                satelite["raio"] = raioAG
            
    