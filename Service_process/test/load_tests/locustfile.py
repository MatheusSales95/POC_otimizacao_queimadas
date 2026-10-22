from locust import HttpUser, task, between, events
import os
import shutil

# Carregar os arquivos em memória no início do teste (para todos os workers)
PAYLOADS = {}

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Carrega os GeoJSONs para a memória antes do teste começar"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    for size in ['small', 'medium', 'large']:
        path = os.path.join(base_dir, 'data', f'{size}.geojson')
        if os.path.exists(path):
            with open(path, 'rb') as f:
                PAYLOADS[size] = f.read()
        else:
            print(f"AVISO: Arquivo {path} não encontrado. Execute gerar_massa.py antes.")

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Esvazia a pasta temp do Service_inject ao final dos testes"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
    # Caminho onde app_pro.py salva os arquivos: Service_inject/data/temp
    file_path = os.path.join(project_root, '..', 'Service_inject', 'data', 'temp')
    
    if os.path.exists(file_path):
        print(f"Limpeza de Locust: Esvaziando diretório {file_path}")
        for filename in os.listdir(file_path):
            file_path_full = os.path.join(file_path, filename)
            try:
                if os.path.isfile(file_path_full) or os.path.islink(file_path_full):
                    os.unlink(file_path_full)
                elif os.path.isdir(file_path_full):
                    shutil.rmtree(file_path_full)
            except Exception as e:
                print(f"Falha ao apagar {file_path_full}. Motivo: {e}")

class ProcessUser(HttpUser):
    # Usuários aguardam de 1 a 3 segundos entre tarefas
    wait_time = between(1, 3)

    def _send_payload(self, size_name):
        if size_name not in PAYLOADS:
            return
            
        file_bytes = PAYLOADS[size_name]
        
        # files= espera (filename, file_object_or_bytes, content_type)
        files = {
            "focos_file": (f"{size_name}.geojson", file_bytes, "application/geo+json")
        }
        
        # Passando query params que a rota precisa
        url = "/api/process?raio=1300&lag_day=7"
        
        # catch_response=True nos permite validar o conteúdo do JSON retornado
        with self.client.post(url, files=files, catch_response=True) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get("status") == "sucesso":
                        response.success()
                    else:
                        response.failure(f"Erro de validação API: {data}")
                except Exception as e:
                    response.failure(f"Não retornou JSON válido: {e}")
            else:
                response.failure(f"HTTP {response.status_code}: {response.text}")

    @task(3)
    def test_small_payload(self):
        """Maior parte do tráfego envia payload pequeno"""
        self._send_payload('small')

    @task(2)
    def test_medium_payload(self):
        """Volume mediano de tráfego manda payloads médios"""
        self._send_payload('medium')

    @task(1)
    def test_large_payload(self):
        """Esporadicamente tenta processar um arquivo grande"""
        self._send_payload('large')
