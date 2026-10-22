from shared.models import Eventos, Focos
from shared.schemas import FocosAdapter
from config import date_process, URL_BASE_EVENTOS
from datetime import datetime
import requests
import shapely


# buscar os eventos 7 dias após a última data de processamento para testar a intersecção
def get_eventos_reprocessar(nome_db: str, date_process: str) -> list[Eventos]:
    # toma os eventos em memória e faz o intersecção com os eventos do dia (último dia processado) e retorna os eventos que intersecionam
    
    pass

# listar os focos dos eventos que intersecionam com os eventos do dia (último dia processado)
def get_focos_reprocessar(nome_db: str, lista_eventos: list[Eventos]) -> list[Focos]:
    """ Tendo em vista a lista de eventos que estão incorretos visto que deveriam ter intersectado outros eventos que nao existiam no banco é preciso tomar a lista de focos a ser reprocessado"""
    list_id_focos = []
    URL_REQUEST_FOCOS_ID = f"{URL_BASE_EVENTOS}/focos/?nome_db={nome_db}"
    for evento in lista_eventos:
        list_id_focos.append(evento.focos)

    if list_id_focos:
        for id_foco in list_id_focos:
            URL_REQUEST_FOCOS_ID +="&id="+str(id_foco)
        
        response = requests.get(URL_REQUEST_FOCOS_ID)    
        if response.status_code == 200:
            focos = FocosAdapter.model_validate(response.json())
            list_obj_focos=[]

            for feature in focos.features:
                props = feature.properties
                geom = feature.geometry
                foco_kwargs = {
                    "id_foco": props.id,
                    "data": props.data,
                    "dias_sem_chuva": props.dias_sem_chuva,
                    "frp": props.frp,
                    "id_satelite": props.satelite,
                    "ponto": shapely.geometry.shape(geom.model_dump()).wkt if geom else None
                }
                list_obj_focos.append(Focos(**foco_kwargs))
            return list_obj_focos
        else:
            raise Exception(f"Erro ao obter focos: {response.text}")
    else:
        return None


# teste de intersecção, amazena em memoria e deleta no banco estes eventos





def get_list_focos(list_id_focos: list[Focos.id_foco]) -> list[Focos]:
    """Pega a lista de id_focos e retorna uma lista objetos de Focos."""

    focos = db.session.query(Focos).filter(Focos.id.in_(list_id_focos)).all()
    
    list_obj_focos=[]
    for foco in focos:
        list_obj_focos.append(foco)
    return list_obj_focos

def get_eventos(date_process: datetime, eventos_processados: list["Eventos"]):
    # lógica... Na prática isso não funciona.
    """
        Verificar se há eventos no banco com inicio no dia que acabou de ser preocessando ou com data de inicio < data de hoje < data de fim
    """
    list_obj_eventos=[]

    eventos_continuos=db.session.query(Eventos).filter(date_process.between(Eventos.data_inicio, Eventos.data_fim)).all()
    eventos_inicio=db.session.query(Eventos).filter(Eventos.data_inicio == date_process).all()

    if eventos_continuos:
        eventos_continuos = eventos_continuos.intersect(eventos_processados.geometry)
        for eventos in eventos_continuos:
            list_obj_eventos.append(eventos)
    if eventos_inicio:
        eventos_inicio = eventos_inicio.intersect(eventos_processados.geometry)
        for eventos in eventos_inicio:
            list_obj_eventos.append(eventos)
    
    if list_obj_eventos:
        return list_obj_eventos
    else: 
        return None

def get_list_eventos_fusionados (list_obj_eventos: list["Eventos"]):
    """Pega a lista de eventos e retorna uma lista de id_evento e focos que compoem o evento"""
    list_eventos_fusionados = []
    list_focos_eventos_fusionados = []
    eventos = db.session.query(Eventos).filter(Eventos.id_evento_absorvedor.isnot(None), Eventos.id_evento_absorvedor.in_(list_obj_eventos)).all()
    for evento in eventos:
        list_eventos_fusionados.append(evento.id_evento)
        list_focos_eventos_fusionados.append(evento.focos)
    return list_eventos_fusionados, list_focos_eventos_fusionados

def reconstruction_initial_conditions():
    """  Função que irá orquestrar a reconstrução das condições iniciais do modelo de eventos de fogo."""

    verify = verify_date_process(date_process)
    print("DEBUG INICIAL: Rota chamada! Baixando focos do access...", flush=True)

    if not verify:
        
    return {"status": "sucesso", "detalhe": "Nenhum processamento necessário"}


