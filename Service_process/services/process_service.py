from services.api_client import ProcessApiClient
from datetime import datetime, timedelta
import time
from fastapi import HTTPException
import services.processar as processar
from shared.models.evento import Eventos
from shapely.geometry import shape
from shared.schemas import EventosAdapter
from shared.config import config_keys

col_ev = config_keys['columns']['evento']

from modelo_evento_fogo_OO.src.evento_fogo.processamento.analisar_recorrencia import analisar_recorrencia


class ProcessService:
    def __init__(self, repo_regiao, nome_db: str):
        self.repo_regiao = repo_regiao
        self.nome_db = nome_db
        self.gdf_regioes = None

    def executar_processamento(self, data_inicio: str, data_fim: str, satelite: list[int], regioes: list[int]):
        """Orquestra o processamento dos eventos"""
        
        data_ini = datetime.fromisoformat(data_inicio).date() 
        data_end = datetime.fromisoformat(data_fim).date()
        
        delta = data_end - data_ini
        list_days = [data_ini + timedelta(days=i) for i in range(delta.days + 1)]
        
        resultados_processamento = []
        soma_tempo = 0

        for data in list_days:
            data_start = data_end = str(data)
            try:
                focos_file = ProcessApiClient.request_get_focos(self.nome_db, data_start, data_end, satelite, regioes)
                eventos_file = ProcessApiClient.request_get_eventos(self.nome_db, data_start)
                
                if self.gdf_regioes is None:
                    self.gdf_regioes = self.repo_regiao.carregar_regioes_gdf()
                    
            except HTTPException as e:
                if e.status_code == 404 and e.detail == "DB_NOT_FOUND":
                    print(f"DEBUG: Banco '{self.nome_db}' não existe. Solicitando criaçao...", flush=True)
                    max_retries = 3
                    provisionamento_sucesso = False
                    ultima_ex = None
                    for attempt in range(max_retries):
                        try:
                            ProcessApiClient.provisionar_banco(self.nome_db, satelite)
                            time.sleep(3)
                            self.gdf_regioes = self.repo_regiao.carregar_regioes_gdf()
                            focos_file = ProcessApiClient.request_get_focos(self.nome_db, data_start, data_end, satelite, regioes)
                            eventos_file = ProcessApiClient.request_get_eventos(self.nome_db, data_start)
                            provisionamento_sucesso = True
                            break
                        except Exception as ex:
                            print(f"DEBUG: Falha no provisionamento (tentativa {attempt + 1}/{max_retries}): {ex}", flush=True)
                            ultima_ex = ex
                            time.sleep(10)
                            
                    if not provisionamento_sucesso:
                        raise HTTPException(status_code=500, detail=f"Falha crítica no provisionamento no dia {data}: {str(ultima_ex)}")
                else:
                    resultados_processamento.append(f"Dia {data}: Pulado - Erro ao buscar dados: {str(e)}")
                    continue

            start_time = time.perf_counter() 

            try:
                dicteventos, eventos = processar.process(focos_file, eventos_file, self.gdf_regioes)
                
                if dicteventos.get("status") == "erro":
                    resultados_processamento.append(f"Dia {data}: Pulado - {dicteventos.get('detalhe')}")
                    continue
                
                ProcessApiClient.inject_db(eventos, self.nome_db)

                process_time = time.perf_counter() - start_time
                soma_tempo += process_time

                resultados_processamento.append(f"Dia {data}: Sucesso em {process_time:0.4f} segundos. Tempo total de processamento: {soma_tempo:0.4f} s.")

                # Chamada para recorrencia
                if data.day == 25:# Uma vez no mes! Teste no dia 25 hoje!
                    valido = ProcessApiClient.validar_min_recorrencia(self.nome_db)
                    if valido:
                        print("DEBUG: Período suficiente para análise de recorrência (mínimo de 1 ano).", flush=True)
                        self.executar_recorrencia(data) 
                    else: 
                        print("DEBUG: Período insuficiente para análise de recorrência (mínimo de 1 ano).", flush=True)
            
            except HTTPException:
                raise 
            except Exception as e:
                import traceback
                traceback.print_exc()
                raise HTTPException(status_code=500, detail=f"Falha no processamento do dia {data}: {str(e)}")

        return resultados_processamento

    def carregar_eventos_json(self, eventos_json):
        
        adapter = EventosAdapter.model_validate(eventos_json)
        
        eventos_por_id = {}
        # pass
        for feature in adapter.features:
            props = feature.properties
            
            # Pydantic já converteu as datas para objetos datetime
            def clean_tz(dt):
                return dt.replace(tzinfo=None) if dt else None
            
            evento = Eventos(
                id_evento=int(getattr(props, col_ev.get('id_evento', 'id_evento'))),
                focos=[], # Por conveniência passando sem os foco pois o processamento de recorrência precisa do id_evento e geometrias apenas
                geometria=shape(feature.geometry.model_dump()) if feature.geometry else None,
                data_inicio=clean_tz(getattr(props, col_ev.get('data_inicio', 'data_inicio'))),
                data_ultima_observacao=clean_tz(getattr(props, col_ev.get('data_ultima_observacao', 'data_ultima_observacao'))),
                data_fim=clean_tz(getattr(props, col_ev.get('data_fim', 'data_fim'))),
                area_inicio=getattr(props, col_ev.get('area_inicio', 'area_inicio')),
                area_fim=getattr(props, col_ev.get('area_fim', 'area_fim')),
                status=getattr(props, col_ev.get('status', 'status')),
                id_evento_absorvedor=getattr(props, col_ev.get('id_evento_absorvedor', 'id_evento_absorvedor')),
                persistencia=getattr(props, col_ev.get('persistencia', 'persistencia')),
                recorrencia=int(props.recorrencia) if props.recorrencia is not None else 0,
                qnt_focos=int(props.quantidade_focos) if props.quantidade_focos is not None else 0
            )
            eventos_por_id[evento.id_evento] = evento
            
            # Atributo emporário para gearar a relação de predecessores e eventos!!
            evento._raw_predecessores = getattr(props, col_ev.get('predecessores', 'predecessores')) or []
            
        # Atribuindo predecessores em memoria!!!
        for evento in eventos_por_id.values():
            lista_preds = [
                eventos_por_id[int(pred_id)]
                for pred_id in evento._raw_predecessores
                if int(pred_id) in eventos_por_id
            ]
            if lista_preds:
                evento.incorporar_predecessores_recorrencia(lista_preds)
            
        return list(eventos_por_id.values())

    def executar_recorrencia(self, data_process: datetime):
        from dateutil.relativedelta import relativedelta
        from shared.config import config_keys
        col_ev = config_keys['columns']['evento']
       
        data_inicio = data_process - relativedelta(years=2)
        data_fim = data_process

        # Converter para string para o request HTTP
        data_inicio_str = data_inicio.strftime('%Y-%m-%d')
        data_fim_str = data_fim.strftime('%Y-%m-%d')

        eventos_json = ProcessApiClient.request_eventos_recorrencia(self.nome_db, data_inicio_str, data_fim_str)
        if not eventos_json.get("features"):
            print("DEBUG: Nenhum evento retornado para o período")
            return {"status": "sucesso", "detalhe": "Nenhum evento retornado para o período."}
        
        print("DEBUG: Eventos retornados recorrencia")    
        # REVER Instanciar manualmente
        eventos = self.carregar_eventos_json(eventos_json)
        
        analisar_recorrencia(
            eventos=eventos,
            data_analise=data_process.strftime('%Y-%m-%d'),
            janela_operacional_dias=7,
            horizonte_anos=2
        )

        # Build lista de atualizacoes
        lista_atualizacoes = []
        for ev in eventos:
            lista_atualizacoes.append({
                col_ev['id_evento']: ev.id_evento,
                col_ev['predecessores']: [p.id_evento for p in ev.predecessores]
            })
            
        # Atualizar no banco
        ProcessApiClient.update_recorrencia_db(lista_atualizacoes, self.nome_db)
        print("DEBUG: Recorrência executada e salva")
        return {"status": "sucesso", "detalhe": f"Recorrência executada e salva para {len(lista_atualizacoes)} eventos."}
