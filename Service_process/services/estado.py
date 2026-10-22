from .api_client import EstadoApiClient
from repository.regiao_repository import RegiaoRepository

_cache_regioes = {}


def reconstrutor_de_estado(nome_db, id_evento, data_obs):
    """ Reconstrói o estado do evento na data de observação."""
    evento = EstadoApiClient.get_evento(nome_db, id_evento)

    if not evento or evento.data_inicio.date() > data_obs.date():
        return None, None, None, None

    focos = EstadoApiClient.get_focos(nome_db, id_evento)
    
    # Injetamos e filtramos os focos no objeto Evento
    evento.injetar_focos_ate_data(focos, data_obs)

    # Reverte o estado de fim se a data de observação for anterior à extinção
    evento.reverter_extincao_se_necessario(data_obs)

    # O evento atualiza a si mesmo baseado no que tem dentro dele!
    # Atualiza a última observação com os focos injetados até a data_obs
    evento.atualizar_ultima_observacao_state()

    # Atualiza o status (pode declarar extinção e setar data_fim se passou 7 dias)
    evento.atualizar_status_state(data_obs)

    # Atualiza a duração (depende do data_fim correto)
    evento.atualizar_duracao_state(data_obs)
    
    # Outros cálculos de estado
    area = evento.calcular_area_do_dia_state(data_obs)
    evento.calcular_persistencia_state()
    evento.atualizar_satelites_por_focos_state()
    evento.qnt_focos_state(data_obs)
    
    # Carrega ou busca as regiões cacheadas para o intersect espacial
    if nome_db not in _cache_regioes:
        repo_regiao = RegiaoRepository(nome_db)
        _cache_regioes[nome_db] = repo_regiao.carregar_regioes_gdf()
    gdf_regioes = _cache_regioes[nome_db]
    
    # Filtra regiões com processamento espacial
    list_regioes_day = evento.filtrar_regioes_ate_data(data_obs, gdf_regioes)

    # Verifica o fusionamento e limpa a propriedade se necessário
    evento.reverter_fusionamento_se_necessario(data_obs)

    # Obtém apenas os IDs dos focos que ocorreram no dia analisado (ou todos, se o evento já encerrou)
    list_focos_day = evento.obter_ids_focos_do_dia(data_obs)

    return evento, area, list_focos_day, list_regioes_day

    