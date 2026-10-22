import pytest
import uuid
import json
import io
from datetime import datetime
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

import sys
import os
# Adiciona a pasta raiz do projeto ao sys.path para que o Python encontre o 'PackageEventos'
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from app_pro import app

client = TestClient(app)

def test_processar_200_sucesso():
    """Testa o endpoint de processamento com um arquivo GeoJSON válido e espera um status 200 e resposta de sucesso."""
    id_foco_sintetico = str(uuid.uuid4())
    data_sintetica = datetime.now().strftime("%Y-%m-%d")

    geojson_content = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [-46.6333, -23.5505] # Exemplo: São Paulo
                },
                "properties": {
                    "data": data_sintetica,
                    "id": id_foco_sintetico
                }
            }
        ]
    }
   
    content = json.dumps(geojson_content).encode('utf-8')

    response = client.post("/api/process", 
        files={"focos_file": ('test.geojson', io.BytesIO(content), 'application/geo+json')})
    assert response.status_code == 200
    assert response.json()["status"] == "sucesso"

def test_metadata_200_sucesso():
    """Testa o endpoint de metadados e espera um status 200 e o conteúdo do arquivo JSON de metadados."""
    response = client.get("/api/metadata")
    assert response.status_code == 200
    assert response.headers["Content-Disposition"] == 'inline; filename="meta.dados"'
    assert response.headers["Content-Type"] == "application/json"

    # Carrega o arquivo de metadados original para comparar o conteúdo
    path_root = os.path.dirname(os.path.abspath(__file__))
    # Navega para o diretório correto do metadado.json
    path_metadata = os.path.join(path_root, '..', 'data', 'metadado.json')
    with open(path_metadata, 'r') as f:
        expected_json = json.load(f)

    assert response.json() == expected_json

def test_metadata_404_arquivo_ausente():
    """Testa o endpoint de metadados quando o arquivo não existe."""
    with patch("builtins.open", side_effect=FileNotFoundError("Arquivo não encontrado")):
        response = client.get("/api/metadata")
        assert response.status_code == 404
        assert response.json() == {"detail": "Arquivo de metadados não encontrado."}

def test_processar_422_requisicao_incompleta():
    """Testa o endpoint de processamento sem enviar o arquivo obrigatório e espera um status 422 indicando que a requisição é inválida."""
    response = client.post("/api/process")
    assert response.status_code == 422
    assert "focos_file" in response.text

def test_processar_400_tipo_invalido():
    """Testa o endpoint de processamento enviando um arquivo com tipo inválido e espera um status 400 indicando que o tipo de arquivo é inválido."""
    files = {"focos_file": ("imagem.png", b"conteudo", "image/png")}
    response = client.post("/api/process", files=files)
    
    assert response.status_code == 400
    assert "Tipo de arquivo inválido" in response.json()["detail"]

def test_processar_500_falha_interna():
    """Testa o endpoint de processamento simulando uma falha interna (exceção) e espera um status 500 indicando erro no servidor."""
    content = b'{"data": "fake"}'
    with patch("services.processar.process_to_dataframe_ev") as mock_proc:
        mock_proc.side_effect = Exception("Erro inesperado")
        
        response = client.post(
            "/api/process",
            files={"focos_file": ("test.geojson", io.BytesIO(content), "application/geo+json")}
        )
        
        assert response.status_code == 500
        assert "Falha no processamento" in response.json()["detail"]

def test_processar_400_sem_data():
    """ Teste esperando erro 400 para entrada sem data"""
    id_foco_sintetico = str(uuid.uuid4())
   
    geojson_content = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [-46.6333, -23.5505] # Exemplo: São Paulo
                },
                "properties": {
                    "id": id_foco_sintetico
                    
                }
            }
        ]
    }

    #tornando json binário
    content = json.dumps(geojson_content).encode('utf-8')
    response = client.post("/api/process", files={"focos_file": ('test.geojson', io.BytesIO(content), 'application/geo+json')})

    assert response.status_code == 400
    assert response.json()["detail"] == "Erro ao processar focos: Campo 'data' é obrigatório."

def test_processar_400_feature_vazia():
    """Testa um erro 400 quando o GeoJSON tem uma lista de 'features' vazia."""

    geojson_content = {
        "type": "FeatureCollection",
        "features": []
    }

    #tornando json binário
    content = json.dumps(geojson_content).encode('utf-8')
    response = client.post("/api/process", files={"focos_file": ('test.geojson', io.BytesIO(content), 'application/geo+json')})

    assert response.status_code == 400
    assert response.json()["detail"] == "Erro ao processar focos: GeoDataFrame vazio."

def test_processar_400_geometria_nula():

    """Testa um erro 400 quando o GeoJSON tem uma geometria nula."""

    id_foco_sintetico = str(uuid.uuid4())
    data_sintetica = datetime.now().strftime("%Y-%m-%d")
    geojson_content = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [None, None] # Exemplo: Vazio
                },
                "properties": {
                    "id": id_foco_sintetico,
                    "data": data_sintetica
                }
            }
        ]
    }

    #tornando json binário
    content = json.dumps(geojson_content).encode('utf-8')
    response = client.post("/api/process", files={"focos_file": ('test.geojson', io.BytesIO(content), 'application/geo+json')})

    assert response.status_code == 400
    assert response.json()["detail"] == "Erro ao processar focos: Há geometrias nulas no GeoDataFrame."

def teste_processar_400_geometria_vazia():
    """Testa um erro 400 quando o GeoJSON tem uma geometria vazia. Vazio vira None quendo o geopandas processa"""
    id_foco_sintetico = str(uuid.uuid4())
    data_sintetica = datetime.now().strftime("%Y-%m-%d")
    geojson_content = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [] 
                },
                "properties": {
                    "id": id_foco_sintetico,
                    "data": data_sintetica
                }
            }
        ]
    }

    #tornando json binário
    content = json.dumps(geojson_content).encode('utf-8')
    response = client.post("/api/process", files={"focos_file": ('test.geojson', io.BytesIO(content), 'application/geo+json')})

    assert response.status_code == 400
    assert response.json()["detail"] == "Erro ao processar focos: Há geometrias nulas no GeoDataFrame."

def test_processar_400_geometria_corrompida():
    """Testa um erro 400 quando o GeoJSON tem um tipo de geometria inválida."""
    id_foco_sintetico = str(uuid.uuid4())
    data_sintetica = datetime.now().strftime("%Y-%m-%d")
    geojson_content = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Poto",
                    "coordinates": [ -47.74, -22.55 ]
                    },
                "properties": {
                    "id": id_foco_sintetico,
                    "data": data_sintetica
                }
            }
        ]
    }

    #tornando json binário
    content = json.dumps(geojson_content).encode('utf-8')
    response = client.post("/api/process", files={"focos_file": ('test.geojson', io.BytesIO(content), 'application/geo+json')})
    assert response.status_code == 400
    assert response.json()["detail"] == "Erro ao processar focos: Há geometrias nulas no GeoDataFrame."

def test_processar_400_type_geometria_invalida():
    """Testa um erro 400 quando o GeoJSON tem um tipo de geometria inválida."""
    id_foco_sintetico = str(uuid.uuid4())
    data_sintetica = datetime.now().strftime("%Y-%m-%d")
    geojson_content = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [ [ [ -47.743099645823698, -22.551241737387556 ], [ -47.742042417036544, -22.574580619878471 ], [ -47.767302195202284, -22.575557826581239 ], [ -47.768355223977956, -22.552217825082753 ], [ -47.743099645823698, -22.551241737387556 ] ] ]
                    },
                "properties": {
                    "id": id_foco_sintetico,
                    "data": data_sintetica
                }
            }
        ]
    }

    #tornando json binário
    content = json.dumps(geojson_content).encode('utf-8')
    response = client.post("/api/process", files={"focos_file": ('test.geojson', io.BytesIO(content), 'application/geo+json')})
    assert response.status_code == 400
    assert response.json()["detail"] == "Erro ao processar focos: As geometrias devem ser do tipo Point."

def test_processar_raio_zero():
    """Teste para raio = 0 erro antes de entrar nas funções do processar"""
    geojson_content = {"type": "FeatureCollection", "features": []}
    content = json.dumps(geojson_content).encode('utf-8')

    response = client.post(
        "/api/process?raio=0&lag_day=7", 
        files={"focos_file": ('test.geojson', io.BytesIO(content), 'application/geo+json')}
    )
    
    assert response.status_code == 422
    assert "Input should be greater than 0" in response.text

def test_processar_lag_zero():
    """Teste para lag_day = 0 erro antes de entrar nas funções do processar"""
    geojson_content = {"type": "FeatureCollection", "features": []}
    content = json.dumps(geojson_content).encode('utf-8')

    response = client.post(
        "/api/process?raio=1300&lag_day=0", 
        files={"focos_file": ('test.geojson', io.BytesIO(content), 'application/geo+json')}
    )
    
    assert response.status_code == 422
    assert "Input should be greater than 0" in response.text

def test_exclusao_arquivo_temporario_sucesso():
    """Teste exclusão de GeoJson temporário para caso de sucesso no processamento"""
    id_foco_sintetico = str(uuid.uuid4())
    data_sintetica = datetime.now().strftime("%Y-%m-%d")
    geojson_content = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [ -47.74, -22.55 ]
                    },
                "properties": {
                    "id": id_foco_sintetico,
                    "data": data_sintetica
                }
            }
        ]
    }

    #tornando json binário
    content = json.dumps(geojson_content).encode('utf-8') # type: ignore
    with patch("app_pro.os.remove") as mock_remove:
        response = client.post("/api/process", files={"focos_file": ("teste.geojson", io.BytesIO(content), "application/geo+json")})
        assert response.status_code == 200
        mock_remove.assert_called_once()

def test_exclusao_arquivo_temporario_falha():
    """Teste exclusão de GeoJson temporário para caso de falha no processamento"""
    content = b'{"data": "fake"}'
    with patch("app_pro.os.remove") as mock_remove, \
         patch("services.processar.process_to_dataframe_ev") as mock_proc:
        mock_proc.side_effect = Exception("Erro inesperado")

        response = client.post(
            "/api/process",
            files={"focos_file": ("test.geojson", io.BytesIO(content), "application/geo+json")}
        )
        
        assert response.status_code == 500
        assert "Falha no processamento" in response.json()["detail"]

        mock_remove.assert_called_once()

def test_salvar_temporario():
    """Teste de salvar processamento de eventos."""
    id_foco_sintetico = str(uuid.uuid4())
    data_sintetica = datetime.now().strftime("%Y-%m-%d")
    geojson_content = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [ -47.74, -22.55 ]
                    },
                "properties": {
                    "id": id_foco_sintetico,
                    "data": data_sintetica
                }
            }
        ]
    }
    content = json.dumps(geojson_content).encode('utf-8') # type: ignore
    
    # Mockamos a função que salva o arquivo e a que gera os eventos para isolar o teste
    with patch("app_pro.processar.savegeojson") as mock_save, \
         patch("app_pro.processar.process_to_dataframe_ev") as mock_process:
        # Configuramos os mocks para simular um retorno de sucesso
        mock_process.return_value = ({"status": "sucesso", "data_inicio": "2024-01-01", "data_fim": "2024-01-01"}, MagicMock())
        mock_save.return_value = {"status": "sucesso", "detalhe": "Arquivo salvo com sucesso"}
        
        response = client.post("/api/process", files={"focos_file": ("teste.geojson", io.BytesIO(content), "application/geo+json")})

        assert response.status_code == 200
        assert response.json()["status"] == "sucesso"
        mock_save.assert_called_once() # Verificamos se a função de salvar foi chamada exatamente uma vez.   
    
def test_processar_500_falha_permissao_diretorio():
    """Testa se a API lida corretamente com falha de permissão ao criar diretório."""
    geojson_content = {
        "type": "FeatureCollection",
        "features": [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [-46.6333, -23.5505]}, "properties": {"data": "2024-01-01", "id": "123"}}]
    }
    content = json.dumps(geojson_content).encode('utf-8')
    with patch("app_pro.os.makedirs") as mock_makedirs:
        mock_makedirs.side_effect = PermissionError("Sem permissão para criar pasta")
        response = client.post("/api/process", files={"focos_file": ('test.geojson', io.BytesIO(content), 'application/geo+json')})
        assert response.status_code == 500
        assert "Falha no processamento" in response.json()["detail"]

def test_processar_integracao_real():
    """Teste sem mock do PackageEventos, passando por todo o fluxo com um pequeno GeoJSON"""
    geojson_content = {
        "type": "FeatureCollection",
        "features": [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [-46.6333, -23.5505]}, "properties": {"data": "2024-01-01", "id": "abc-123"}}]
    }
    content = json.dumps(geojson_content).encode('utf-8')
    response = client.post("/api/process", files={"focos_file": ('test.geojson', io.BytesIO(content), 'application/geo+json')})
    
    assert response.status_code == 200
    assert response.json()["status"] == "sucesso"
