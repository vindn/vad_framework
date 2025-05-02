import pandas as pd

class ClassificadorTrajetorias:
    def __init__(self):
        pass
    
    def classificar(self, row):
        """
        Classifica uma trajetória com base nos critérios predefinidos.
        row: pandas.Series - uma linha do DataFrame contendo os dados da trajetória.
        
        Retorna: uma string com a classe da trajetória.
        """
        
        # Critérios para "Pesca Ilegal"
        if self.criterio_pesca_ilegal(row):
            return "pesca_ilegal"
        
        # Critérios para "Atividade Suspeita"
        elif self.criterio_atividade_suspeita(row):
            return "atividade_suspeita"
        
        # Critérios para "Atividade Anômala"
        elif self.criterio_atividade_anomala(row):
            return "atividade_anomala"
        
        # Se nenhum dos critérios anteriores for atendido, a trajetória é "Atividade Normal"
        else:
            return "atividade_normal"
    
    # Critérios para "Pesca Ilegal"
    def criterio_pesca_ilegal(self, row):
        if (
            # Embarcações de pesca dentro de APAs com comportamento de pesca
            (row['dentro_apa'] == 1 and row['type_fishing'] == 1 and row['ft'] > 0.5 and row['dist_costa'] > 5) or
            # Embarcações de pesca de bandeira estrangeira na ZEE ou MT
            ((row['dentro_zee'] == 1 or row['dentro_mt'] == 1) and row['dist_costa'] > 5 and row['type_fishing'] == 1 and row['ft'] > 0.5 and row['flag_other'] == 1)
        ):
            return True
        return False
    
    # Critérios para "Atividade Suspeita"
    def criterio_atividade_suspeita(self, row):
        if (
            # Encontros a mais de 12 MN fora da área de FPSO
            (row['dentro_zee'] == 1 and row['dist_costa'] > 12 and row['in_fpso_area'] == 0 and row['enc'] == 1) or
            # Encontros dentro do MT fora de FPSO (excluindo rebocadores)
            (row['dentro_mt'] == 1 and row['type_tug'] != 1 and row['dist_costa'] > 5 and row['type_fishing'] != 1 and row['in_fpso_area'] == 0 and row['enc'] == 1) or
            # Pesca com loitering ou fundeadas dentro de APAs
            (row['dentro_apa'] == 1 and row['type_fishing'] == 1 and (row['loi'] > 0.5 or row['time_stopped_h'] > 2)) or
            # Embarcações de pesca sem identificação dentro de APAs
            (row['dentro_apa'] == 1 and row['type_unknow'] == 1 and row['ft'] > 0.5) or
            # Pesca estrangeira com gaps, spoofing ou loitering dentro da ZEE ou MT
            ((row['dentro_mt'] == 1 or row['dentro_zee'] == 1) and row['type_fishing'] == 1 and row['flag_other'] == 1 and (row['dark_ship'] > 0 or row['spoofing'] > 0 or row['loi'] > 0.5)) or
            # Pesca estrangeira fundeada na ZEE por mais de 2 horas
            (row['dentro_zee'] == 1 and row['type_fishing'] == 1 and row['flag_other'] == 1 and row['time_stopped_h'] > 2)
        ):
            return True
        return False
    
    # Critérios para "Atividade Anômala"
    def criterio_atividade_anomala(self, row):
        if (
            # Sem identificação no MT com comportamento anômalo
            (row['dentro_mt'] == 1 and row['mmsi_valid'] == 0 and row['flag_unknow'] == 1 and row['dist_costa'] > 5 and row['ft'] > 0.5 and row['loi'] > 0.5 and row['enc'] == 0) or
            # Fundeadas em locais próximos à costa
            (row['dentro_mt'] == 1 and row['time_stopped_h'] > 96 and row['dist_costa'] > 5 and row['dist_costa'] < 8 and row['out_of_anchor_zone'] == 1 and row['enc'] == 0) or
            # Embarcações inconsistentes com seu tipo
            ((row['type_tanker'] == 1 or row['type_offshore'] == 1 or row['type_cargo'] == 1) and row['ft'] > 0.5 and row['loi'] > 0.5 and row['sog_diff'] > 1 and row['cog_diff'] > 50 and row['dist_costa'] > 20 and row['in_fpso_area'] == 0 and row['time_stopped_h'] > 2 and row['enc'] == 0) or
            # Sem identificação com comportamento de pesca no MT ou ZEE
            (row['type_unknow'] == 1 and row['mmsi_valid'] == 0 and row['ft'] > 0.5 and row['sog_diff'] > 1 and row['cog_diff'] > 50 and row['dist_costa'] > 5 and row['enc'] == 0) or
            # Sem identificação com loitering dentro de APAs
            (row['type_unknow'] == 1 and row['mmsi_valid'] == 0 and row['loi'] > 0.5 and row['dist_costa'] > 5 and row['enc'] == 0 and row['dentro_apa'] == 1) or
            # Embarcações de pesca sem bandeira próximo à costa
            (row['type_fishing'] == 1 and row['flag_unknow'] == 1 and row['dist_costa'] > 5 and row['dist_costa'] < 12 and row['ft'] > 0.5 and row['cog_diff'] > 50) or
            # Embarcações sem identificação fundeadas dentro de APAs por mais de 2 horas
            ((row['type_unknow'] == 1 or row['mmsi_valid'] == 0) and row['dentro_apa'] == 1 and row['dist_costa'] > 5 and row['loi'] > 0.5 and row['time_stopped_h'] > 2 and row['out_of_anchor_zone'] == 1) or
            # Embarcações sem identificação com spoofing e gaps dentro do MT
            ((row['type_unknow'] == 1 or row['mmsi_valid'] == 0) and row['dentro_mt'] == 1 and row['dist_costa'] > 5 and row['dark_ship'] > 0 and row['spoofing'] > 0) or
            # Contatos do tipo boia com velocidade média acima de 2 nós.
            (row['type_buoy'] == 1 and row['sog_diff'] > 2)
        ):
            return True
        return False
    
    # Critérios para "Atividade Normal"
    def criterio_atividade_normal(self, row):
        if (
            # Embarcações com comportamento normal
            (row['mmsi_valid'] > 0 and row['ft'] < 0.5 and row['enc'] == 0 and row['loi'] < 0.5 and row['dark_ship'] == 0 and row['spoofing'] == 0 and row['sog_diff'] > 2 and row['time_stopped_h'] < 1 and row['dist_costa'] > 2) or
            # Offshore realizando encontros em áreas de FPSO
            (row['in_fpso_area'] == 1 and row['enc'] == 1) or
            # Boias com velocidade média abaixo de 2 nós
            (row['type_buoy'] == 1 and row['sog_diff'] < 2) or
            # Rebocadores realizando encontros próximo à costa
            (row['type_tug'] == 1 and row['enc'] == 1 and row['dist_costa'] < 100) or
            # Embarcações de pesca brasileiras na ZEE ou MT
            (row['type_fishing'] == 1 and (row['flag_brazil'] == 1 or row['mmsi_valid'] == 1) and row['ft'] > 0.5) or
            # Tankers, offshore e cargo fazendo loitering no MT
            ((row['type_tanker'] == 1 or row['type_offshore'] == 1 or row['type_cargo'] == 1) and (row['ft'] > 0.5 or row['loi'] > 0.5) and row['cog_diff'] > 50 and row['dist_costa'] > 12 and row['dist_costa'] < 100 and row['in_fpso_area'] == 0 and row['time_stopped_h'] > 1 and row['enc'] == 0) or
            # Embarcações de pesca estrangeiras com velocidade média acima de 8 nós
            (row['type_fishing'] == 1 and row['ft'] < 0.5 and row['sog_diff'] > 8 and row['time_stopped_h'] < 1 and row['enc'] == 0) or
            # Embarcações de pesca saindo de portos apresentando comportamento de pesca
            (row['type_fishing'] == 1 and row['ft'] > 0.5 and row['dist_costa'] < 5) or
            # Embarcações de pesca fundeadas em portos
            (row['type_fishing'] == 1 and row['time_stopped_h'] > 1 and row['dist_costa'] < 3)
        ):
            return True
        return False
