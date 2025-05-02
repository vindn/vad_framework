from src.preprocessing import Preprocessing
from src.object_level_fusion import ObjectLevelFusion
# Importações adicionais conforme necessário
# tratar as classes como processos inpendentes
from multiprocessing import Process, Queue
import multiprocessing
import geopandas as gpd
import pickle

def read_pickle_obj(file_name):
    try:
        with open(file_name, 'rb') as data_file:
            data = pickle.load(data_file)
            return data
    except Exception as e:
        print(e, "File not Found!")


# wrapper function for preprocessing class (enter point)
def preprocess_data(data_queue, result_queue):
    while True:
        data = data_queue.get()
        if data is None:  # Um sinal para terminar o processo
            break
        preprocessing = Preprocessing(data)
        result = preprocessing.run()
        result_queue.put(result)        


if __name__ == "__main__":
    data_queue = multiprocessing.Queue()
    result_queue = multiprocessing.Queue()

    # Criar o processo
    preprocess_process = multiprocessing.Process(target=preprocess_data, args=(data_queue, result_queue))
    
    # Iniciar o processo
    preprocess_process.start()

    # Enviar dados1 para o processo
    gdf_sistram = read_pickle_obj("data/sistram/gdf_sistram_1dn_ais_ihs.pkl")    
    data_queue.put(gdf_sistram)  # manda gdf para ser processado

    # Receber resultados
    trajectories = result_queue.get()
    print(trajectories)

    # Sinalizar o processo para terminar e esperar que ele termine
    data_queue.put(None)
    preprocess_process.join()