import requests
from bs4 import BeautifulSoup
from src.database.metamodel_base import MetamodelDB
from tqdm import tqdm
import traceback

class WebCrawler:
    def __init__( self ):
        self.db = MetamodelDB()

    def is_valid_mmsi(self, mmsi):
        # Verifica se é um número e tem 9 dígitos
        if isinstance(mmsi, int) and len(str(mmsi)) in (9, 8, 7, 6, 5, 4):
            return True
        else:
            return False

    def obter_info_navio(self, mmsi):
        # Construir a URL com o MMSI fornecido
        url = f'https://www.myshiptracking.com/vessels/{mmsi}'
        
        try:
            if not self.is_valid_mmsi( mmsi ):
                print("mmsi " + str(mmsi) + " nao valido.")
                return "N/A", "N/A", "N/A"    

            nome_navio, bandeira, tipo = self.db.get_info_navio(mmsi)                     
            if nome_navio != None:
                # print(str(mmsi) + " " + nome_navio)
                return nome_navio, bandeira, tipo
            else:
                print("Navio " + str(mmsi) + " nao encontrado na base de dados.")
        except ValueError:
            print(f"MMSI não encontrado na lista.")
            pass

        try:
            # Fazer a requisição para a URL
            resposta = requests.get(url)
            soup = BeautifulSoup(resposta.content, 'html.parser')

            # Extrair o nome do navio
            nome_navio_h1 = soup.find('h1')
            nome_navio = nome_navio_h1.get_text(strip=True) if nome_navio_h1 else "Nome não encontrado"

            # Extrair a bandeira do navio
            bandeira_div = soup.find('div', class_='pflag')
            bandeira = bandeira_div.get_text(strip=True) if bandeira_div else "Bandeira não encontrada"

            # Extrair o tipo do navio
            tipo_navio_h2 = soup.find('h2', class_='mb-0')
            tipo_navio = tipo_navio_h2.get_text(strip=True) if tipo_navio_h2 else "Tipo não encontrado"

            if bandeira != "Bandeira não encontrada":
                self.db.insere_info_navio(mmsi, nome_navio, bandeira, tipo_navio)

            return nome_navio, bandeira, tipo_navio
        except requests.RequestException as e:
            print(f"Erro ao fazer a requisição: {e}")
            return "N/A", "N/A", "N/A"    
        except Exception as e1:
            traceback_str = traceback.format_exc()
            print("webcrawler error: \n" + traceback_str ) 
            return "N/A", "N/A", "N/A"

    def baixar_info_navios(self, mmsis ):
        import time
        print("Updating vessel info ...")
        for mmsi in tqdm( mmsis ):
            self.obter_info_navio( int(mmsi) )
            # time.sleep(1)

