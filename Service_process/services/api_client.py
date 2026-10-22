import requests
import traceback
import shapely
import shapely.geometry
from fastapi import HTTPException
from datetime import datetime, timedelta
from config import URL_BASE_EVENTOS, URL_BASE_FOCOS, URL_BASE_EVENTOS, URL_INJECT
from shared.models import Eventos, Focos
from shared.schemas import EventosAdapter, FocosAdapter
from shared.config import config_keys

col_geo_even = config_keys["geojson"]["evento"]
col_reg = config_keys["columns"]["regiao"]
col_ev = config_keys["columns"]["evento"]

class EstadoApiClient:
    """ Cliente para abstrair chamadas HTTP à API de Eventos. Faz Get Eventos e Focos via id_evento. """

    @staticmethod
    def get_evento(nome_db, id_evento) -> Eventos:
        """ Retorna o evento via ID. """
        try:
            url_eventos = f"{URL_BASE_EVENTOS}/evento?nome_db={nome_db}&id={id_evento}&include_regiao=true&include_satelites=false"
            response = requests.get(url_eventos)
           
            if response.status_code == 200:
                evento_json = response.json()
                
                evento_validado = EventosAdapter.model_validate(evento_json)

                props = evento_validado.features[0].properties
                geom = evento_validado.features[0].geometry
                
                evento_kwargs = {
                    "id_evento": props.id_evento,
                    "status": props.status,
                    "data_inicio": props.data_inicio,
                    "data_fim": props.data_fim,
                    "data_ultima_observacao": props.data_ultima_observacao,
                    "area_inicio": props.area_inicio,
                    "area_fim": props.area_fim,
                    "recorrencia": props.recorrencia,
                    "persistencia": props.persistencia,
                    "duracao": props.duracao,
                    "qnt_focos": props.quantidade_focos,
                    "id_evento_absorvedor": props.id_evento_absorvedor,
                    "geometria": shapely.geometry.shape(geom.model_dump()).wkt if geom else None
                }

                evento_obj = Eventos(**evento_kwargs)
                evento_obj._raw_predecessores = getattr(props, 'predecessores', [])

                # Busca as regiões do campo "regiao" que o Service_access exporta
                chave_historico = config_keys.get("geojson", {}).get("evento", {}).get("historico_regioes", "historico_regioes")
                dict_regioes = getattr(props, 'regiao', {}) or {}
                historico_regiao = dict_regioes.get(chave_historico, [])
                
                evento_obj.injetar_historico_regioes(historico_regiao)

                return evento_obj
            else:
                raise HTTPException(status_code=response.status_code, detail=f"Erro ao obter evento: {response.text}")
        except HTTPException as http_exc:
            raise http_exc
        except Exception as e:
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Falha ao obter evento: {str(e)}")

    @staticmethod
    def get_focos(nome_db, id_evento) -> list[Focos]:
        """ Retorna os focos de um evento específico. """
        try:
            url_eventos = f"{URL_BASE_EVENTOS}/focos?nome_db={nome_db}&id={id_evento}"
            response = requests.get(url_eventos)
            if response.status_code == 200:
                focos_json = response.json()
                focos_validado = FocosAdapter.model_validate(focos_json)
                focos_obj=[]
                
                for feature in focos_validado.features:
                    props = feature.properties
                    geom = feature.geometry
                    
                    foco_kwargs = {
                        "id_foco": str(props.id),
                        "data": props.data,
                        "dias_sem_chuva": props.dias_sem_chuva,
                        "frp": props.frp,
                        "id_satelite": props.satelite,
                        "ponto": shapely.geometry.shape(geom.model_dump()).wkt if geom else None
                    }
                    
                    focos_obj.append(Focos(**foco_kwargs))
                return focos_obj
            else:
                raise HTTPException(status_code=response.status_code, detail=f"Erro ao obter focos: {response.text}")
        except HTTPException as http_exc:
            raise http_exc
        except Exception as e:
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Falha ao obter focos: {str(e)}")

class ProcessApiClient:
    """"""
    @staticmethod
    def request_get_focos(nome_db:str, data_inicio: datetime, data_fim: datetime, satelite: list[int] = None, regioes: list[int] = None):
        """Pega os focos no banco de dados."""
    
        url_focos = f"{URL_BASE_FOCOS}/?nome_db={nome_db}&data_inicio={data_inicio}&data_fim={data_fim}"

        if satelite is not None:
            for s in satelite:
                url_focos += f"&satelite={s}"
        if regioes is not None:
            for r in regioes:
                url_focos += f"&regioes={r}"
        response = requests.get(url_focos)

        if response.status_code == 200:
            focos_file = response.json()
            return focos_file
        else:
            if "Nenhum foco encontrado" in response.text:
                return {"type": "FeatureCollection", "features": []}
            if response.status_code == 404 and response.json().get("detail", {}).get("codigo") == "DB_NOT_FOUND":
                raise HTTPException(status_code=404, detail="DB_NOT_FOUND")
            raise HTTPException(status_code=response.status_code, detail=f"Erro ao obter focos: {response.text}")
   
    @staticmethod
    def request_get_eventos(nome_db:str, data_loop: str):
        """Pega os eventos no banco de dados, buscando um histórico de 7 dias anteriores ao dia do loop."""
        data_fim = str(datetime.fromisoformat(data_loop) - timedelta(days=1))
        data_inicio_busca = str(datetime.fromisoformat(data_loop) - timedelta(days=7)) # PEQUENA DUVIDA AQUI

        url_eventos = f"{URL_BASE_EVENTOS}/?nome_db={nome_db}&data_inicio={data_inicio_busca}&data_fim={data_fim}"

        response = requests.get(url_eventos)

        if response.status_code == 200:
            eventos_file = response.json()
            return eventos_file
        else:
            if "Nenhum evento encontrado" in response.text:
                return {"type": "FeatureCollection", "features": []}
            if response.status_code == 404 and response.json().get("detail", {}).get("codigo") == "DB_NOT_FOUND":
                raise HTTPException(status_code=404, detail="DB_NOT_FOUND")
            raise HTTPException(status_code=response.status_code, detail=f"Erro ao obter eventos: {response.text}")

    @staticmethod
    def inject_db(eventos, nome_db):
        try:
            response = requests.post(f"{URL_INJECT}?nome_banco={nome_db}", json=eventos)
            if response.status_code != 200:
                print(f"DEBUG 422: Falha na injeção. Detalhes: {response.text}")
                raise HTTPException(status_code=response.status_code, detail=f"Erro ao injetar eventos: {response.text}")
            
            resp_json = response.json()
            if resp_json.get("status") == "erro":
                raise HTTPException(status_code=500, detail=resp_json.get("detalhe", "Erro desconhecido na injeção"))
            
            return {"status": "sucesso", "detalhe": f"Sucesso! {resp_json.get('detalhe', '')}"}
        except Exception as e:
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Erro ao injetar eventos: {str(e)}")

    @staticmethod
    def provisionar_banco(nome_db: str, satelite: list[int] = None):
        """Aciona a rota de setup do Service_inject para criar o banco de dados"""
        
        url_setup = URL_INJECT.replace("/inject", "/api/setup")
        url_with_params = f"{url_setup}?nome_db={nome_db}"
        
        if satelite:
            for sat in satelite:
                url_with_params += f"&satelites={sat}"
                
        response = requests.post(url_with_params)
        if response.status_code != 200:
            raise Exception(f"Falha ao criar banco: {response.text}")
        return response.json()

    @staticmethod
    def request_eventos_recorrencia(nome_db:str, data_inicio:str, data_fim:str):
        """Pega os eventos no banco de dados em no máximo dois anos e minimo um ano."""
        
        url_eventos_recorrencia = f"{URL_BASE_EVENTOS}/region/?nome_db={nome_db}&data_inicio={data_inicio}&data_fim={data_fim}&include_regiao=false&include_satelites=false"
        
        response = requests.get(url_eventos_recorrencia)

        if response.status_code == 200:
            eventos_file = response.json()
            return eventos_file
        else:
            if "Nenhum evento encontrado" in response.text:
                return {"type": "FeatureCollection", "features": []}
            if response.status_code == 404 and response.json().get("detail", {}).get("codigo") == "DB_NOT_FOUND":
                raise HTTPException(status_code=404, detail="DB_NOT_FOUND")
            raise HTTPException(status_code=response.status_code, detail=f"Erro ao obter eventos: {response.text}")

    @staticmethod
    def validar_min_recorrencia(nome_db: str) -> bool:
        """Chama a rota para validar se há eventos o suficiente (mínimo de 1 ano) para a análise de recorrência."""
        url_validacao = f"{URL_BASE_EVENTOS}/validar_min_recorrencia?nome_db={nome_db}"
        
        response = requests.get(url_validacao)
        if response.status_code == 200:
            return response.json().get("valido", False)
        raise HTTPException(status_code=response.status_code, detail=f"Erro ao validar período mínimo: {response.text}")

    @staticmethod
    def update_recorrencia_db(eventos_atualizados: list[dict], nome_db: str):
        """Envia os dados atualizados de recorrência e predecessores para o banco de dados via rota PUT."""
        url_update = URL_INJECT.replace("/inject", "/api/inject/update_recorrencia")
        url_update = f"{url_update}?nome_db={nome_db}"
        
        response = requests.put(url_update, json=eventos_atualizados)
        
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=f"Erro ao atualizar eventos no banco: {response.text}")
        
        return response.json()