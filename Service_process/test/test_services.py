from pluggy import _result
import pytest
from services import processar
from unittest.mock import patch, MagicMock
from shapely.geometry import Point
from shapely.geometry import Polygon
import geopandas as gpd
import pandas as pd
from config import DB_URL
import tempfile
import os

def test_processar_arquivo_caminho_vazio():
    """Teste para exception quando o arquivo enviado é vazio"""
    # A função espera uma tupla (dict, GeoDataFrame), então desempacotamos o retorno
    retorno_dict, retorno_gdf = processar.process_to_dataframe_ev(None, raio=1300, lag_day=7)

    assert retorno_dict["status"] == "erro"
    assert "Entrada ou caminho vazio" in retorno_dict["detalhe"]

@patch('services.processar.gpd.read_file')
def test_processar_falha_leitura_arquivo_corrompido(mock_read_file):
    """
    Testa o cenário de falha na leitura do arquivo, onde gpd.read_file levanta uma exceção.
    Isso simula um arquivo corrompido ou em formato inválido.
    """
    mock_read_file.side_effect = Exception("Erro de driver: formato de arquivo não reconhecido.")

    retorno_dict, _ = processar.process_to_dataframe_ev("caminho/para/arquivo_corrompido.geojson", 1300, 7)

    assert retorno_dict["status"] == "erro"
    assert "Erro de driver" in retorno_dict["detalhe"]

@pytest.fixture
def mock_gdf_foco_sem_data():
    df = pd.DataFrame({
        'id_foco': ['123-abc'],
    })
    point = Point(-48.8, -20.4)
    gdf = gpd.GeoDataFrame(df, geometry=[point], crs="EPSG:4326")
    return gdf
@patch('services.processar.gpd.read_file')
def test_processar_ausencia_colunas_data(mock_read_file, mock_gdf_foco_sem_data):
    mock_read_file.return_value = mock_gdf_foco_sem_data

    # esse caminho é só para garantir a chamada correta da função, na realidade 
    # a leitura de arquivo está em modo mock
    retorno_dict, retorno_gdf = processar.process_to_dataframe_ev("caminho_ficticio.geojson", raio=1300, lag_day=7)
    
    assert isinstance(retorno_dict, dict)
    assert retorno_dict["status"] == "erro"
    assert "Campo 'data' é obrigatório" in retorno_dict["detalhe"]

@pytest.fixture
def mock_gdf_foco_bom():
    df = pd.DataFrame({
        'id_foco': ['123-abc'],
        'data': [pd.to_datetime('2024-08-02')],
    })
    point = Point(-48.8, -20.4)
    gdf = gpd.GeoDataFrame(df, geometry=[point], crs="EPSG:4326")
    return gdf
@patch('services.processar.gpd.read_file')
def test_processar_output_dataframe(mock_read_file, mock_gdf_foco_bom):
        mock_read_file.return_value=mock_gdf_foco_bom
        # Mock para a função de integração, que é o coração da lógica de negócio
        with patch('services.processar.gerareventos.integrar_eventos_com_focos_geojson') as mock_integrar:
            # Simula um retorno bem-sucedido da função de integração
            mock_integrar.return_value = gpd.GeoDataFrame({
                'data_inicio': [pd.to_datetime('2024-08-02')],
                'data_fim': [pd.to_datetime('2024-08-02')],
                'id_evento': ['123-abc'],
                'area_inicio': 6760000.0, 
                'area_fim': 6760000.0, 
                'ids_focos': [["be4e6869-66f2-3096-bd5d-2d2b7f504b15"]], # Lista dupla para garantir o tipo lista na célula
                'data_ultima_observacao': [pd.to_datetime('2024-08-01 00:00:00')], # Padronizado como datetime
                'geometry': [Polygon([ 
                                      [ -48.161803923190291, -21.916376419159128 ], 
                                      [ -48.160847883873608, -21.939735142539202 ], 
                                      [ -48.185997865548792, -21.940623134794759 ], 
                                      [ -48.186949843733416, -21.91726337034396 ], 
                                      [ -48.161803923190291, -21.916376419159128 ] ])]
            })

            retorno_dict, retorno_gdf = processar.process_to_dataframe_ev("caminho_fake.geojson", raio=1300, lag_day=7)

            assert isinstance(retorno_dict, dict)
            assert retorno_dict["status"] == "sucesso"

@pytest.mark.parametrize("test_case_gdf, expected_detail", [
    (gpd.GeoDataFrame(), "GeoDataFrame vazio."),
    (gpd.GeoDataFrame({'geometry': [Point(1, 1)], 'data': [None]}), "Há valores nulos em 'data'"),
    (gpd.GeoDataFrame({'geometry': [Point(1, 1)], 'data': ['texto-invalido']}), "Valores inválidos na coluna 'data'."),
    (gpd.GeoDataFrame({'geometry': [None], 'data': ['2024-01-01']}), "Há geometrias nulas no GeoDataFrame."),
    (gpd.GeoDataFrame({'geometry': [Point()]}), "Há geometrias vazias (sem coordenadas) no GeoDataFrame."),
    (gpd.GeoDataFrame({'geometry': [Polygon([(0,0), (1,1), (1,0)])], 'data': ['2024-01-01']}), "As geometrias devem ser do tipo Point."),
    (gpd.GeoDataFrame({'geometry': [Point(1, 1)]}), "Campo 'data' é obrigatório."),
])
def test_validate_gdf_focos_cenarios_de_erro(test_case_gdf, expected_detail):
    """Testa vários cenários de falha para a função de validação."""
    result = processar.validate_gdf_focos(test_case_gdf)
    assert result["status"] == "erro"
    assert result["detalhe"] == expected_detail

def test_validate_gdf_focos_sucesso():

    """Testa o cenário de sucesso para a função de validação."""
    gdf = gpd.GeoDataFrame({'geometry': [Point(1, 1)], 'data': [pd.to_datetime('2024-01-01')]})
    result = processar.validate_gdf_focos(gdf)
    assert result["status"] == "sucesso"

@pytest.fixture
def mock_gdf_evento_vazio():
    """GeoDataFrame de eventos vazio (sem linhas)."""
    return gpd.GeoDataFrame({
        'data_inicio': pd.Series([], dtype='datetime64[ns]'),
        'data_fim': pd.Series([], dtype='datetime64[ns]'),
        'id_evento': pd.Series([], dtype='str'),
        'area_inicio': pd.Series([], dtype='float64'),
        'area_fim': pd.Series([], dtype='float64'),
        'ids_focos': pd.Series([], dtype='object'),
        'data_ultima_observacao': pd.Series([], dtype='datetime64[ns]'),
    }, geometry=gpd.GeoSeries([], crs="EPSG:4326"))
@patch('services.processar.gerareventos.integrar_eventos_com_focos_geojson')
def test_processar_retorno_evento_vazio(mock_retorno_eventos, mock_gdf_evento_vazio):
    mock_retorno_eventos.return_value = mock_gdf_evento_vazio
    with patch('services.processar.gerareventos.integrar_eventos_com_focos_geojson') as mock_integrar:
        mock_integrar.return_value = gpd.GeoDataFrame({
            'data_inicio': pd.Series([], dtype='datetime64[ns]'),
            'data_fim': pd.Series([], dtype='datetime64[ns]'),
        })
        retorno_dict, retorno_gdf = processar.process_to_dataframe_ev( "caminho_fake.geojson", raio=1300, lag_day=7)
       
        assert retorno_dict["status"] == "erro"

@patch('services.processar.gpd.read_file')
def test_processar_raio_negativo(mock_read_file, mock_gdf_foco_bom):
    """Testa comportamento com raio negativo chamando a função diretamente."""
    mock_read_file.return_value = mock_gdf_foco_bom
    
    with patch('services.processar.gerareventos.integrar_eventos_com_focos_geojson') as mock_integrar:
        mock_integrar.side_effect = ValueError("Raio deve ser positivo")
        retorno_dict, _ = processar.process_to_dataframe_ev( "caminho_fake.geojson", raio=-100, lag_day=7)
        assert retorno_dict["status"] == "erro"
      
def test_savegeojson_sucesso(tmp_path):
    """Testa se savegeojson salva um GeoJSON válido."""
    gdf = gpd.GeoDataFrame(
        {'data': ['2024-01-01']},
        geometry=[Point(1, 1)],
        crs="EPSG:4326"
    )
    path = str(tmp_path / "output.geojson")
    result = processar.savegeojson(gdf, path)
    
    assert result["status"] == "sucesso"
    assert os.path.exists(path)
    # Verifica se o conteúdo é legível como GeoJSON
    gdf_lido = gpd.read_file(path)
    assert len(gdf_lido) == 1

def test_savegeojson_caminho_invalido():
    """Testa se savegeojson levanta exceção ao tentar salvar em caminho inválido."""
    gdf = gpd.GeoDataFrame(
        {'data': ['2024-01-01']},
        geometry=[Point(1, 1)],
        crs="EPSG:4326"
    )
    result = processar.savegeojson(gdf, "/caminho/que/nao/existe/output.geojson")
    
    assert result["status"] == "erro"
    assert result["detalhe"] == "Erro ao salvar GeoDataFrame em formato GeoJSON"


