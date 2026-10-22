from evento_fogo.integracao.integrador import integrar_eventos as integrador
import geopandas as gpd
import pandas as pd
import traceback
import json
from shared.schemas import EventosAdapter, FocosAdapter

from shared.models.focos import Focos
from shapely.geometry import Point
from datetime import datetime

from shared.config import config_keys
geojson_foco = config_keys.get("geojson", {}).get("foco", {})


key_id = geojson_foco.get("id_foco", "id_foco")
key_data = geojson_foco.get("data", "data")
key_satelite = geojson_foco.get("id_satelite", "id_satelite")

def process(focos, evento, gdf_regioes)-> tuple[dict, gpd.GeoDataFrame]:
    """Processa o arquivo de focos e retorna um GeoDataFrame de eventos agregados e dicionário de status. Para tal chama o módulo que é o kernel do sistema de processamento."""
    try:
       
        focos_validos = FocosAdapter.model_validate(focos)
        
        if not focos_validos.features:
            return {"status": "erro", "detalhe": "Nenhum foco encontrado na data."}, None
            
        eventos_validos = EventosAdapter.model_validate(evento)

        focos_json = focos_validos.model_dump_json()
       
        is_db_vazio = not eventos_validos.features
     
        if is_db_vazio:
            print("DEBUG: O banco de eventos está VAZIO. Primeira rodada: todos os eventos gerados serão novos.")
            gdf_eventos = gpd.GeoDataFrame()
            eventos = integrador(focos_json, gdf_eventos)
        else:
            print(f"DEBUG: O banco já possui {len(eventos_validos.features)} eventos.")
            
            gdf_eventos = gpd.GeoDataFrame.from_features(eventos_validos.model_dump())

            def converter_focos_para_objetos(lista_focos_dict):
                objetos = []
                if not lista_focos_dict:
                    return objetos
                for f_dict in lista_focos_dict:
                    if isinstance(f_dict, Focos):
                        objetos.append(f_dict)
                        continue
                    try:
                        coords = f_dict['geometry']['coordinates']
                        props = f_dict['properties']
                        
                        data_str = props.get(key_data)
                        data = datetime.fromisoformat(data_str) if data_str else None
                        
                        objetos.append(Focos(
                                id_foco=props.get(key_id),
                                data=data,            
                                geometria=Point(coords[0], coords[1]),
                                satelite=props.get(key_satelite) or 'Desconhecido'
                            ))
                    except Exception as e:
                        print(f"Erro ao converter foco: {e}")
                return objetos

            if 'focos' in gdf_eventos.columns:
                gdf_eventos['focos'] = gdf_eventos['focos'].apply(converter_focos_para_objetos)
            # --------------------------------------------------
            
            gdf_eventos.set_crs(epsg=4326, inplace=True)
            gdf_eventos.to_crs(epsg=5880, inplace=True) # Integrador exige o CRS métrico
            
            eventos = integrador(focos_json, gdf_eventos)

        if eventos is not None and not eventos.empty:
            eventos.to_crs(epsg=4326, inplace=True)
            
            # --- CRUZAMENTO ESPACIAL COM REGIÕES ---
            if not gdf_regioes.empty:
                gdf_regioes_4326 = gdf_regioes.to_crs(epsg=4326)
                # left join espacial
                joined = gpd.sjoin(eventos, gdf_regioes_4326, how='left', predicate='intersects')
                
                # Agrupa a lista de IDs de região por evento
                agrupado = joined.groupby(joined.index)['id_regiao'].apply(
                    lambda x: [int(i) for i in x if not pd.isna(i)]
                )
                eventos['ids_regioes'] = agrupado
            else:
                eventos['ids_regioes'] = [[] for _ in range(len(eventos))]
            
            # Tirando os objetos focos para o envio de ingestão
            if 'focos' in eventos.columns:
                eventos = eventos.drop(columns=['focos'])
            
            eventos_pydantic = EventosAdapter.model_validate(eventos.__geo_interface__)

            eventos_dict = eventos_pydantic.model_dump(mode='json', by_alias=True)
            
            return {"status": "sucesso"}, eventos_dict
        else:
            return {"status": "sucesso"}, None

    except Exception as e:
        traceback.print_exc()
        return {"status": "erro", "detalhe": str(e)}, None
