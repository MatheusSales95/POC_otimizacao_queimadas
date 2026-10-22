from fastapi import FastAPI, HTTPException, Response, Query
import os
import traceback
from services.estado import reconstrutor_de_estado
from repository.regiao_repository import RegiaoRepository
from datetime import datetime
from services.process_service import ProcessService
import shapely


app = FastAPI(
    title="Api de processamento de eventos.",
    version="0.2"
)

@app.get("/api/process", tags=["Processamento do evento."])
def rotas_processar( 
    nome_db: str = Query(default="", description="Nome do banco de dados."),
    data_inicio: str = Query(default="", description="Data inicial do processamento."),
    data_fim: str = Query(default="", description="Data final do processamento."),
    satelite: list[int] = Query(None, description= "Lista de IDs dos satélites"),
    regioes: list[int] = Query(None, description="Lista de IDs das regiões de interesse.")
):
    try:
        
        repo_regiao = RegiaoRepository(nome_db)
        servico = ProcessService(repo_regiao, nome_db)
        
        resultados = servico.executar_processamento(data_inicio, data_fim, satelite, regioes)
        
        return {"status": "sucesso", "detalhes": resultados}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/metadata", tags=["Metadadata"])
def metadata():
    path_root = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(path_root, 'data', 'metadado.json')
    
    try:
        with open(path, 'r', encoding='utf-8') as content:
            import json
            content_json = json.load(content)
            
        # Busca metadados extras (regiões e satélites) do Service_access
        import requests
        try:
            # URL_BASE_FOCOS = http://service_access:9000/api/focos -> tira /api/focos e põe /api/access/metadata
            from config import URL_BASE_FOCOS
            url_meta = URL_BASE_FOCOS.replace("/api/focos", "/api/access/metadata")
            resp = requests.get(url_meta, timeout=5)
            if resp.status_code == 200:
                access_meta = resp.json()
                content_json['Available Regions'] = access_meta.get('Available Regions', {})
                content_json['Available Satellites'] = access_meta.get('Available Satellites', [])
        except Exception as e:
            content_json['Available Regions'] = {"erro": f"Não foi possível obter do Service_access: {e}"}
            content_json['Available Satellites'] = {"erro": f"Não foi possível obter do Service_access: {e}"}

        return Response(
            content=json.dumps(content_json, ensure_ascii=False),
            media_type="application/json; charset=utf-8",
            headers={
                "Content-Disposition": 'inline; filename="meta.dados"'
            }
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Arquivo de metadados não encontrado.")
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Falha ao ler arquivo de metadados: {str(e)}")
