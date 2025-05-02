import math
from src.rules.distancia_costa import CalcDistanciaCosta
from tqdm import tqdm

class AISSpoofing:  
    def __init__(self, trajs):
        self.trajs = trajs

    def calc_sog( self, p1, t1, p2, t2 ):
        pass

    def verify_trajectory_on_shore( self, traj ):
        dc = CalcDistanciaCosta( )
        dc.distancia_costa_brasil()


    def verify_spoofing_position_trajs( self ):
        #AFAZER: verifica velocidades e posicoes impossiveis
        cd = CalcDistanciaCosta()
        trajs_spoofing = [] 
        spoofing = False
        cruzou = False
        print("Verifying AIS spoofing trajectories ...")
        for i in tqdm( range( len(self.trajs) ) ):
            traj = self.trajs.trajectories[i]
            spoofing = False
            if (traj.df['speed_nm'] > 50).any():
                spoofing = True
            # for j in range( 1, len(traj.df) ):

            #     row1 = traj.df.reset_index().iloc[j-1]
            #     row2 = traj.df.reset_index().iloc[j]
            #     sog = self.calculate_speed( row1.lat, row1.lon, row1.dh, row2.lat, row2.lon, row2.dh )
            #     # spoofing if > 50 knots and time diference greather than 5 min
            #     if sog > 50 and (row2.dh - row1.dh).total_seconds() > 300:
            #         spoofing = True
            #         break


            cruzou = cd.verifica_trajetoria_cruzou_costa( traj )

            if spoofing or cruzou[0]:
                trajs_spoofing.append( True )
            else:
                trajs_spoofing.append( False )

        return trajs_spoofing




    def verify_spoofing_id_trajs( self ):
        #AFAZER: verficar o mmsi do navio em lugares diferentes ao mesmo tempo
        pass



    def haversine(self, lat1, lon1, lat2, lon2):
        # Converter coordenadas de graus para radianos
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

        # Fórmula Haversine
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        distance = 3440 * c  # Raio da Terra em milhas náuticas
        return distance

    def calculate_speed(self, lat1, lon1, time1, lat2, lon2, time2):
        distance = self.haversine(lat1, lon1, lat2, lon2)
        time_diff = (time2 - time1).total_seconds() / 3600  # Converter tempo para horas
        speed = distance / time_diff  # Velocidade em nós
        return speed

    