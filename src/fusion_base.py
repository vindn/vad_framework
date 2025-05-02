# Uma classe abstrata ou base que define a interface comum e/ou funcionalidades compartilhadas por todas as classes de fusão de dados.

class DataFusionBase:
    # Métodos e atributos comuns às classes de fusão de dados
    def __init__(self, gdf):
        self.gdf = gdf