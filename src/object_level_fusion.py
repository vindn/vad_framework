# Lida com a correlação e combinação de dados de diferentes fontes para cada objeto (embarcação). (Nivel 1)
# Implementar aqui:
# detecção de comportamento;
# regras dos especialistas;

from src.behaviours.spoofing import AISSpoofing
from src.fusion_base import DataFusionBase
from src.behaviours.fishing_trajectory import FishingTrajectoryDetection
from src.preprocessing import Preprocessing
from src.behaviours.encounter import Encounter
from src.database.metamodel_base import MetamodelDB
from src.behaviours.loitering import LoiteringTrajectoryDetection
from src.behaviours.loitering import create_rnn_model
from src.behaviours.dark_activity import DarkActivity
from src.rules.distancia_costa import CalcDistanciaCosta
from src.rules.anchorage_zones import AnchorageZone
from src.rules.apa import APA
from src.rules.fpso import FPSO
from src.tools.web_crawler import WebCrawler
from src.database.metamodel_base import MetamodelDB
import pandas as pd
import numpy as np
from tqdm import tqdm

class ObjectLevelFusion:
    def __init__(self, preprocessing):
        if not isinstance(preprocessing, Preprocessing):
                    raise TypeError("Parameter is not instance of Preprocessing Class!")

        self.trajs = preprocessing.get_trajs()
        self.trajs_info = preprocessing.get_trajs_info()
        self.trajs_fk = None
        self.gdf = preprocessing.gdf
        self.df_metamodelo = None
        self.da = None
        self.az = None
        self.fpso = None
        self.db = MetamodelDB( )
        # Inicializar o modelo aqui (carregar modelo treinado, definir parâmetros, etc.)


    def detect_fishing_trajectories_gb( self, trajs_info, trajs ):
        ftd = FishingTrajectoryDetection("GB")
        ypred_fishing = ftd.predict_gb( trajs_info )

        # de veloc < 6 knots, se for maior que 5 não é trajetoria de pesca
        for i in range(len(trajs_info)):
            # veloc_mean = trajs_info['sog_mean'].iloc[i]
            speed_mean = trajs.trajectories[i].df['speed_nm'].mean()
            veloc_mean  = trajs.trajectories[i].df['veloc'].mean()
            # veloc_std = trajs.trajectories[i].df['speed_nm'].std()
            # para evitar casos onde o navio anda rapido e derrepente para
            # pescar e depois aumenta a velocidade, utilizaremos a media movel
            # OBS: quando diferença de tempo entre os pontos são segundos, imprecisões no GPS
            # podem ocorrer acarretando em um cálculo de velocidade errado. Para isso,
            # é importante também utilizar o SOG
            mm_speed = trajs.trajectories[i].df['speed_nm'].rolling(window=3).mean()
            mm_veloc = trajs.trajectories[i].df['veloc'].rolling(window=3).mean()
            if ( 
                (  (speed_mean > 7 and (not (mm_speed < 4).any())) or (veloc_mean > 7 and (not (mm_veloc < 4).any())) ) or 
                (  (speed_mean < 1 and (not (mm_speed > 2).any())) or (veloc_mean < 1 and (not (mm_veloc > 2).any())) ) or
                ( len(trajs.trajectories[i].df) < 5 ) or # se tiver menos de 6 pontos
                ( (trajs.trajectories[i].get_duration().total_seconds() / 3600) < 1 and ( len(trajs.trajectories[i].df) <= 6 ) ) # se a traj tiver menos de 2hs

            ):
                ypred_fishing[i, 0] = 0.0
                ypred_fishing[i, 1] = 1.0


        return ypred_fishing[:,0]

    def detect_fishing_trajectories( self, trajs ):
        ftd = FishingTrajectoryDetection("RNN")
        ypred_fishing = ftd.predict_rnn( trajs )

        # de veloc < 6 knots, se for maior que 5 não é trajetoria de pesca
        for i in range(len(trajs)):
            # veloc_mean = trajs.trajectories[i].df['veloc'].mean()
            veloc_mean = trajs.trajectories[i].df['speed_nm'].mean()
            veloc_std = trajs.trajectories[i].df['speed_nm'].std()
            if (veloc_mean > 6 or veloc_mean < 1) and veloc_std > 5:
                ypred_fishing[i, 0] = 0
                ypred_fishing[i, 1] = 1

        return ypred_fishing[:,0]


    def detect_encounters_trajectories( self, trajs ):
        # Detect encounter beteween vessels using h3
        encounter = Encounter( trajs )
        df_encounters = encounter.detect_encouters()
        db = MetamodelDB()
        db.insert_encounters( df_encounters )
        y_pred_encounters = encounter.get_encounters_on_trajs()

        return np.array( y_pred_encounters )

    def detect_loitering_trajectories( self, trajs ):
        # se yp_pred == 1 é loitering
        loitering = LoiteringTrajectoryDetection( )
        y_pred_loitering = loitering.predict_rnn( trajs )

        for i in range(len(trajs)):
            traj = trajs.trajectories[i]
            # Para ser loitering, o navio precisa parar em algum momento da trajetoria.
            # Para isso, calcularemos a media movel da velocidade com w=3, entao se existir pelo
            # menos uma media movel menor que 1, pode ser seja loitering.
            # Senao tiver nenhuma, nao ter como ser loitering
            mm = traj.df['speed_nm'].rolling(window=3).mean()
            if not (mm < 1).any():
                y_pred_loitering[i, 0] = 0
                y_pred_loitering[i, 1] = 1

        return y_pred_loitering[:,0]

    def build_gap_on_trajectories( self, gdf ):
        # verify if a vessel has AIS transmission gap in a trajectory in    anytime
        da = DarkActivity( gdf )
        trajs_da = da.build_trajectories( )        
        da.criar_mapa_historico_multiplo()
        self.da = da
        return trajs_da

    def detect_gap_on_trajectories( self, trajs ):
        # verify if a vessel has AIS transmission gap in a trajectory in anytime
        trajs_gap = self.da.update_gap_on_trajectories(trajs.trajectories, 3)
        tg = []
        for x in trajs_gap:
            if x == True:
                tg.append( 1 )
            else:
                tg.append( 0 )
        return tg

    def detect_spoofing_on_trajectories( self, trajs ):
        aiss = AISSpoofing( trajs )
        aiss_verify = np.array( aiss.verify_spoofing_position_trajs() )
        return aiss_verify.astype(int)

    def rules_calc_distances_to_coast( self, trajs ):
        dist = CalcDistanciaCosta( )
        return dist.distancia_costa_brasil_array( trajs )
    
    def rules_calc_arring_trajs( self, trajs ):
        dist = CalcDistanciaCosta( )
        return dist.detect_arriving( trajs )
    
    def time_stopped_trajs( self, trajs, speed_threshold = 0.5 ):
        # Definir o critério para o navio estar parado
        stopped_trajs = []
        for traj in tqdm(trajs.trajectories[:]):
            # Identificar as linhas onde o navio estava parado
            traj.df['stopped'] = traj.df['speed_nm'] < speed_threshold
            # Calcular o total de horas parado
            time_stopped = traj.df[traj.df['stopped']]['time_diff_h'].sum()
            stopped_trajs.append( time_stopped )

        return stopped_trajs

    def rules_time_stopped_trajs( self, trajs ):
        return self.time_stopped_trajs( trajs )

    def rules_calc_inside_zee( self, trajs ):
        # dentro_zee = ( df_metamodelo["dist_costa"] < 200 ).astype(int)
        dist = CalcDistanciaCosta( )
        inside_eez = dist.calc_trajs_inside_eez( trajs )
        return inside_eez

    def rules_calc_inside_mt( self, df_metamodelo ):
        dentro_mt = ( df_metamodelo["dist_costa"] < 12 ).astype(int)
        return dentro_mt

    def rules_calc_inside_apa( self, trajs ):
        apas = APA()
        return apas.verifica_trajetorias_dentro_apa_binario( trajs )


    def rules_calc_inside_anchorage_zones( self, trajs ):
        trajs_out_of_anchor_zones = self.az.get_trajs_out_achorage_zones( trajs )
        return trajs_out_of_anchor_zones


    def rules_calc_inside_fpso_area( self, trajs ):
        return self.fpso.is_trajs_inside( trajs )


    def rules_get_crawler_vessel_info( self, mmsis ):
        # Update Vessel Info
        # Filtrar linhas onde 'mmsi' tem exatamente 9 dígitos
        wc = WebCrawler()
        wc.baixar_info_navios( mmsis )


    def rules_get_vessel_flag( self, traj_id_col ):
        # Flags
        # 0 Brazil, 1 - Unknow, 2 - Other
        flag_brazil = []
        flag_unknow = []
        flag_other = []
        for i in range( len(traj_id_col) ):
            traj_id = traj_id_col.iloc[i]
            mmsi = traj_id.split("_")[0]
            nome_navio, bandeira, tipo = self.db.get_info_navio(mmsi)
            if bandeira == None or bandeira.lower() == "unknow" or bandeira.lower() == "unknown":
                flag_brazil.append( 0 )
                flag_unknow.append( 1 )
                flag_other.append( 0 )
            else:
                if bandeira.lower( ) == "brazil" or bandeira.lower( ) == "brasil":
                    flag_brazil.append( 1 )
                    flag_unknow.append( 0 )
                    flag_other.append( 0 )
                else:
                    flag_brazil.append( 0 )
                    flag_unknow.append( 0 )
                    flag_other.append( 1 )
        # df_metamodelo["flag_brazil"] = flag_brazil
        # df_metamodelo["flag_unknow"] = flag_unknow
        # df_metamodelo["flag_other"] = flag_other
        return flag_brazil, flag_unknow, flag_other

    def rules_get_vessel_type( self, traj_id_col ):
        # Type of Vessel in metamodel
        # Flags
        # 0 Brazil, 1 - Unknow, 2 - Other
        type_fishing = []
        type_other = []
        type_unknow = []
        type_offshore = []
        type_tug = []
        type_tanker = []
        type_anti_pollution = []
        type_cargo = []
        type_research = []
        type_buoy = []
        for i in range( len(traj_id_col) ):
            traj_id = traj_id_col.iloc[i]
            mmsi = traj_id.split("_")[0]
            nome_navio, bandeira, tipo = self.db.get_info_navio(mmsi)
            if tipo == None or tipo.lower() == "unknow" or tipo.lower() == "unknown":
                type_fishing.append( 0 )
                type_other.append( 0 )
                type_unknow.append( 1 )
                type_offshore.append( 0 )
                type_tug.append( 0 )
                type_tanker.append( 0 )
                type_anti_pollution.append( 0 )
                type_cargo.append( 0 )
                type_research.append( 0 )
                type_buoy.append( 0 )
            else:
                # test if fishing
                if ( 
                    tipo.lower() == "fishing" or 
                    tipo.lower().find("fish") > -1 or 
                    tipo.lower() == "trawler" or 
                    tipo.lower() == "longline" 
                ):
                    type_fishing.append( 1 )
                    type_other.append( 0 )
                    type_unknow.append( 0 )
                    type_offshore.append( 0 )
                    type_tug.append( 0 )
                    type_tanker.append( 0 )
                    type_anti_pollution.append( 0 )
                    type_cargo.append( 0 )
                    type_research.append( 0 )
                    type_buoy.append( 0 )

                # test if offshore
                elif ( 
                        tipo.lower() == "offshore" or 
                        tipo.lower().find("shore") > -1 or 
                        tipo.lower().find("off") > -1 or 
                        tipo.lower().find("stimulation") > -1 or 
                        tipo.lower().find("drill") > -1 or
                        tipo.lower().find("production") > -1 
                ):
                    type_fishing.append( 0 )
                    type_other.append( 0 )
                    type_unknow.append( 0 )
                    type_offshore.append( 1 )
                    type_tug.append( 0 )
                    type_tanker.append( 0 )
                    type_anti_pollution.append( 0 )
                    type_cargo.append( 0 )                    
                    type_research.append( 0 )
                    type_buoy.append( 0 )

                # test if tug                    
                elif (
                    tipo.lower().find("tug") > -1 or 
                    tipo.lower().find("tow") > -1
                ):
                    type_fishing.append( 0 )
                    type_other.append( 0 )
                    type_unknow.append( 0 )
                    type_offshore.append( 0 )
                    type_tug.append( 1 )
                    type_tanker.append( 0 )
                    type_anti_pollution.append( 0 )
                    type_cargo.append( 0 )       
                    type_research.append( 0 )
                    type_buoy.append( 0 )

                # test if tanker
                elif (
                    tipo.lower().find("tanker") > -1
                ):
                    type_fishing.append( 0 )
                    type_other.append( 0 )
                    type_unknow.append( 0 )
                    type_offshore.append( 0 )
                    type_tug.append( 0 )
                    type_tanker.append( 1 )
                    type_anti_pollution.append( 0 )
                    type_cargo.append( 0 )                                     
                    type_research.append( 0 )
                    type_buoy.append( 0 )

                # test if anti pollution
                elif (
                    tipo.lower().find("pollution") > -1 or
                    tipo.lower().find("environ") > -1
                ):
                    type_fishing.append( 0 )
                    type_other.append( 0 )
                    type_unknow.append( 0 )
                    type_offshore.append( 0 )
                    type_tug.append( 0 )
                    type_tanker.append( 0 )
                    type_anti_pollution.append( 1 )
                    type_cargo.append( 0 )                                     
                    type_research.append( 0 )
                    type_buoy.append( 0 )

                # test if cargo                       
                elif (
                    tipo.lower().find("cargo") > -1 or
                    tipo.lower().find("environ") > -1
                ):
                    type_fishing.append( 0 )
                    type_other.append( 0 )
                    type_unknow.append( 0 )
                    type_offshore.append( 0 )
                    type_tug.append( 0 )
                    type_tanker.append( 0 )
                    type_anti_pollution.append( 0 )
                    type_cargo.append( 1 )                                         
                    type_research.append( 0 )
                    type_buoy.append( 0 )

                # test if research                       
                elif (
                    tipo.lower().find("research") > -1 or
                    tipo.lower().find("pesquisa") > -1 or
                    tipo.lower().find("survey") > -1
                ):
                    type_fishing.append( 0 )
                    type_other.append( 0 )
                    type_unknow.append( 0 )
                    type_offshore.append( 0 )
                    type_tug.append( 0 )
                    type_tanker.append( 0 )
                    type_anti_pollution.append( 0 )
                    type_cargo.append( 0 )                                         
                    type_research.append( 1 )
                    type_buoy.append( 0 )

                # test if buoy
                elif (
                    tipo.lower().find("buoy") > -1 or
                    tipo.lower().find("boia") > -1 or
                    tipo.lower().find("bóia") > -1 or
                    tipo.lower().find("aid") > -1 or
                    tipo.lower().find("reference") > -1 or
                    tipo.lower().find("point") > -1 or
                    nome_navio.lower().find("buoy") > -1 or
                    nome_navio.lower().find("boia") > -1 or
                    nome_navio.lower().find("bóia") > -1
                ):
                    type_fishing.append( 0 )
                    type_other.append( 0 )
                    type_unknow.append( 0 )
                    type_offshore.append( 0 )
                    type_tug.append( 0 )
                    type_tanker.append( 0 )
                    type_anti_pollution.append( 0 )
                    type_cargo.append( 0 )                                         
                    type_research.append( 0 )
                    type_buoy.append( 1 )

                else:
                    # other type
                    type_fishing.append( 0 )
                    type_other.append( 1 )
                    type_unknow.append( 0 )
                    type_offshore.append( 0 )
                    type_tug.append( 0 )
                    type_tanker.append( 0 )
                    type_anti_pollution.append( 0 )
                    type_cargo.append( 0 )                    
                    type_research.append( 0 )
                    type_buoy.append( 0 )


        # df_metamodelo["type_fishing"] = type_fishing
        # df_metamodelo["type_other"] = type_other
        # df_metamodelo["type_unknow"] = type_unknow
        return type_fishing, type_other, type_unknow, type_offshore, type_tanker, type_tug, type_anti_pollution, type_cargo, type_research, type_buoy

    def rules_cog_diff( self, trajs ):
        cog_diff_list = []
        for traj in trajs.trajectories:
            cog_diff_mean = traj.df['ang_diff_cog'].mean( )
            cog_diff_list.append( cog_diff_mean )

        return cog_diff_list

    def rules_sog_diff( self, trajs ):
        sog_diff_list = []
        for traj in trajs.trajectories:
            sog_mean = traj.df['speed_nm'].mean( )
            sog_diff_list.append( sog_mean )

        return sog_diff_list
    

    def rules_offshore_vessels( self, trajs ):
        offshore_vessels = []
        for traj in trajs.trajectories:
            sog_mean = traj.df['speed_nm'].mean( )
            sog_diff_list.append( sog_mean )


    ##
    # MID Codes in https://www.vtexplorer.com/mmsi-mid-codes-en/
    # https://www.itu.int/en/ITU-R/terrestrial/fmd/Pages/mid.aspx
    # nacionilidade dos 3 primeiros digitos
    def mmsi_mid_to_county( self, mmsi ):

        mid_to_country = {
            201: "Albania (Republic of)",
            202: "Andorra (Principality of)",
            203: "Austria",
            204: "Azores",
            205: "Belgium",
            206: "Belarus (Republic of)",
            207: "Bulgaria (Republic of)",
            208: "Vatican City State",
            209: "Cyprus (Republic of)",
            210: "Cyprus (Republic of)",
            211: "Germany (Federal Republic of)",
            212: "Cyprus (Republic of)",
            213: "Georgia",
            214: "Moldova (Republic of)",
            215: "Malta",
            216: "Armenia (Republic of)",
            218: "Germany (Federal Republic of)",
            219: "Denmark",
            220: "Denmark",
            224: "Spain",
            225: "Spain",
            226: "France",
            227: "France",
            228: "France",
            215: "Malta",            
            230: "Finland",
            231: "Faroe Islands",
            232: "United Kingdom of Great Britain and Northern Ireland",
            233: "United Kingdom of Great Britain and Northern Ireland",
            234: "United Kingdom of Great Britain and Northern Ireland",
            235: "United Kingdom of Great Britain and Northern Ireland",
            236: "Gibraltar",
            237: "Greece",
            238: "Croatia (Republic of)",
            239: "Greece",
            240: "Greece",
            241: "Greece",
            242: "Morocco (Kingdom of)",
            243: "Hungary (Republic of)",
            244: "Netherlands (Kingdom of the)",
            245: "Netherlands (Kingdom of the)",
            246: "Netherlands (Kingdom of the)",
            247: "Italy",
            248: "Malta",
            249: "Malta",
            250: "Ireland",
            251: "Iceland",
            252: "Liechtenstein (Principality of)",
            253: "Luxembourg",
            254: "Monaco (Principality of)",
            255: "Madeira",
            256: "Malta",
            257: "Norway",
            258: "Norway",
            259: "Norway",
            261: "Poland (Republic of)",
            262: "Montenegro",
            263: "Portugal",
            264: "Romania",
            265: "Sweden",
            266: "Sweden",
            267: "Slovak Republic",
            268: "San Marino (Republic of)",
            269: "Switzerland (Confederation of)",
            270: "Czech Republic",
            271: "Turkey",
            272: "Ukraine",
            273: "Russian Federation",
            274: "The Former Yugoslav Republic of Macedonia",
            275: "Latvia (Republic of)",
            276: "Estonia (Republic of)",
            277: "Lithuania (Republic of)",
            278: "Slovenia (Republic of)",
            279: "Serbia (Republic of)",
            # Europe continued
            280: "Ukraine",
            281: "Belarus (Republic of)",
            282: "Moldova (Republic of)",
            283: "Armenia (Republic of)",
            284: "Georgia",
            285: "Bulgaria (Republic of)",
            286: "Turkey",
            287: "Cyprus (Republic of)",
            288: "Georgia",
            289: "Moldova (Republic of)",
            290: "Belarus (Republic of)",
            291: "Switzerland (Confederation of)",
            292: "Belgium",
            293: "Denmark",
            294: "Ireland",
            295: "Greece",
            296: "Iceland",
            297: "Portugal",
            298: "Malta",
            299: "Denmark",
            300: "United Kingdom of Great Britain and Northern Ireland",
            # North America
            301: "Anguilla",
            303: "Alaska (State of)",
            304: "Antigua and Barbuda",
            305: "Antigua and Barbuda",
            306: "Netherlands Antilles",
            307: "Aruba",
            308: "Bahamas (Commonwealth of)",
            309: "Bahamas (Commonwealth of)",
            310: "Bermuda",
            311: "Bahamas (Commonwealth of)",
            312: "Belize",
            314: "Barbados",
            316: "Canada",
            319: "Cayman Islands",
            321: "Costa Rica",
            323: "Cuba",
            325: "Dominica (Commonwealth of)",
            327: "Dominican Republic",
            329: "Guadeloupe (French Department of)",
            330: "Grenada",
            331: "Greenland",
            332: "Guatemala (Republic of)",
            334: "Honduras (Republic of)",
            336: "Haiti (Republic of)",
            338: "United States of America",
            339: "Jamaica",
            341: "Saint Kitts and Nevis (Federation of)",
            343: "Saint Lucia",
            345: "Mexico",
            347: "Martinique (French Department of)",
            348: "Montserrat",
            350: "Nicaragua",
            351: "Panama (Republic of)",
            352: "Panama (Republic of)",
            353: "Panama (Republic of)",
            354: "Panama (Republic of)",
            355: "Panama (Republic of)",
            356: "Panama (Republic of)",
            357: "Panama (Republic of)",
            355: "United States of America", # No specific allocation
            356: "United States of America", # No specific allocation
            357: "United States of America", # No specific allocation
            358: "Puerto Rico",
            359: "El Salvador (Republic of)",
            361: "Saint Pierre and Miquelon (Territorial Collectivity of)",
            362: "Trinidad and Tobago",
            364: "Turks and Caicos Islands",
            366: "United States of America",
            367: "United States of America",
            368: "United States of America",
            369: "United States of America",
            370: "Panama (Republic of)",
            371: "Panama (Republic of)",
            372: "Panama (Republic of)",
            373: "Panama (Republic of)",            
            374: "Panama (Republic of)",
            375: "Saint Vincent and the Grenadines",
            376: "Saint Vincent and the Grenadines",
            377: "Saint Vincent and the Grenadines",
            378: "British Virgin Islands",
            379: "United States Virgin Islands",
            401: "Afghanistan",
            403: "Saudi Arabia (Kingdom of)",
            405: "Bangladesh (People's Republic of)",
            408: "Bahrain (Kingdom of)",
            410: "Bhutan (Kingdom of)",
            412: "China (People's Republic of)",
            413: "China (People's Republic of)",
            414: "China (People's Republic of)",                    
            416: "Taiwan (Province of China)",
            417: "Sri Lanka (Democratic Socialist Republic of)",
            419: "India (Republic of)",
            422: "Iran (Islamic Republic of)",
            423: "Azerbaijani Republic",
            425: "Iraq (Republic of)",
            428: "Israel (State of)",
            431: "Japan",
            432: "Japan",
            434: "Turkmenistan",
            436: "Kazakhstan (Republic of)",
            437: "Uzbekistan (Republic of)",
            438: "Jordan (Hashemite Kingdom of)",
            440: "Korea (Republic of)",
            441: "Korea (Republic of)",
            443: "Palestine (In accordance with Resolution 99 Rev. Antalya, 2006)",
            445: "Democratic People's Republic of Korea",
            447: "Kuwait (State of)",
            450: "Lebanon",
            451: "Kyrgyz Republic",
            453: "Macao (Special Administrative Region of China)",
            455: "Maldives (Republic of)",
            457: "Mongolia",
            459: "Nepal (Federal Democratic Republic of)",
            461: "Oman (Sultanate of)",
            463: "Pakistan (Islamic Republic of)",
            466: "Qatar (State of)",
            468: "Syrian Arab Republic",
            470: "United Arab Emirates",
            473: "Yemen (Republic of)",
            475: "Yemen (Republic of)",
            477: "Hong Kong (Special Administrative Region of China)",
            478: "Bosnia and Herzegovina",
            # Oceania
            501: "Adelie Land",
            503: "Australia",
            506: "Myanmar (Union of)",
            508: "Brunei Darussalam",
            510: "Micronesia (Federated States of)",
            511: "Palau (Republic of)",
            512: "New Zealand",
            514: "Cambodia (Kingdom of)",
            515: "Cambodia (Kingdom of)",
            516: "Christmas Island (Indian Ocean)",
            518: "Cook Islands",
            520: "Fiji (Republic of)",
            523: "Cocos (Keeling) Islands",
            525: "Indonesia (Republic of)",
            529: "Kiribati (Republic of)",
            531: "Lao People's Democratic Republic",
            533: "Malaysia",
            536: "Northern Mariana Islands (Commonwealth of the)",
            538: "Marshall Islands (Republic of)",
            540: "New Caledonia",
            542: "Niue",
            544: "Nauru (Republic of)",
            546: "French Polynesia",
            548: "Philippines (Republic of)",
            553: "Papua New Guinea",
            555: "Pitcairn Island",
            557: "Solomon Islands",
            559: "American Samoa",
            561: "Samoa (Independent State of)",
            563: "Singapore (Republic of)",
            564: "Singapore (Republic of)",
            565: "Singapore (Republic of)",
            566: "Singapore (Republic of)",                    
            567: "Thailand",
            570: "Tonga (Kingdom of)",
            572: "Tuvalu",
            574: "Viet Nam (Socialist Republic of)",
            576: "Vanuatu (Republic of)",
            577: "Vanuatu (Republic of)",            
            578: "Wallis and Futuna Islands",
            # Africa
            601: "South Africa (Republic of)",
            603: "Angola (Republic of)",
            605: "Algeria (People's Democratic Republic of)",
            607: "Saint Paul and Amsterdam Islands",
            608: "Ascension Island",
            609: "Burundi (Republic of)",
            610: "Benin (Republic of)",
            611: "Botswana (Republic of)",
            612: "Central African Republic",
            613: "Cameroon (Republic of)",
            615: "Congo (Republic of the)",
            616: "Comoros (Union of the)",
            617: "Cape Verde (Republic of)",
            618: "Crozet Archipelago",
            619: "Côte d'Ivoire (Republic of)",
            621: "Djibouti (Republic of)",
            622: "Egypt (Arab Republic of)",
            624: "Ethiopia (Federal Democratic Republic of)",
            625: "Eritrea",
            626: "Gabonese Republic",
            627: "Ghana",
            629: "Gambia (Republic of the)",
            630: "Guinea-Bissau (Republic of)",
            631: "Equatorial Guinea (Republic of)",
            632: "Guinea (Republic of)",
            633: "Burkina Faso",
            634: "Kenya (Republic of)",
            635: "Kerguelen Islands",
            636: "Liberia (Republic of)",
            637: "Liberia (Republic of)",
            642: "Socialist People's Libyan Arab Jamahiriya",
            644: "Lesotho (Kingdom of)",
            645: "Mauritius (Republic of)",
            647: "Madagascar (Republic of)",
            649: "Mali (Republic of)",
            650: "Mozambique (Republic of)",
            654: "Mauritania (Islamic Republic of)",
            655: "Malawi",
            656: "Niger (Republic of)",
            657: "Nigeria (Federal Republic of)",
            659: "Namibia (Republic of)",
            660: "Reunion (French Department of)",
            661: "Rwanda (Republic of)",
            662: "Sudan (Republic of)",
            663: "Senegal (Republic of)",
            664: "Seychelles (Republic of)",
            665: "Saint Helena",
            666: "Somali Democratic Republic",
            667: "Sierra Leone",
            668: "Sao Tome and Principe (Democratic Republic of)",
            669: "Swaziland (Kingdom of)",
            670: "Chad (Republic of)",
            671: "Togolese Republic",
            672: "Tunisia",
            674: "Tanzania (United Republic of)",
            675: "Uganda (Republic of)",
            676: "Democratic Republic of the Congo",
            677: "Tanzania (United Republic of)",
            678: "Zambia (Republic of)",
            679: "Zimbabwe (Republic of)",
            # South America
            701: "Argentine Republic",
            710: "Brazil (Federative Republic of)",
            711: "Brazil (Federative Republic of)",
            712: "Brazil (Federative Republic of)",
            713: "Brazil (Federative Republic of)",
            714: "Brazil (Federative Republic of)",
            715: "Brazil (Federative Republic of)",
            716: "Brazil (Federative Republic of)",
            717: "Brazil (Federative Republic of)",
            718: "Brazil (Federative Republic of)",
            719: "Brazil (Federative Republic of)",
            720: "Bolivia (Plurinational State of)",
            725: "Chile",
            730: "Colombia (Republic of)",
            735: "Ecuador",
            740: "Falkland Islands (Malvinas)",
            745: "Guiana (French Department of)",
            750: "Guyana",
            755: "Paraguay (Republic of)",
            760: "Peru",
            765: "Suriname (Republic of)",
            770: "Uruguay (Eastern Republic of)",
            775: "Venezuela (Bolivarian Republic of)"
        }    

        # Extrai os três primeiros dígitos para verificar o MID
        mid = int(str(mmsi)[:3])

        # Verifica se o MID está no dicionário
        if mid not in mid_to_country:
            return (1, "N/A")

        return (mid, mid_to_country[mid])

    def validate_mmsi(self, mmsi):
        # Valida se um número MMSI é válido
        # 0 invalid
        # 0.5 valid mmsi
        # 1 valid brazil mmsi
        

        # Verifica se o MMSI tem nove dígitos
        if not str(mmsi).isdigit() or len(str(mmsi)) != 9:
            return 0
        
        md_code, country = self.mmsi_mid_to_county( mmsi )
        
        # print("Country: " + str(country))

        # valid and it's brazil
        if country.lower().find( "brazil" ) >= 0:
            return 1
        
        # valid, but it's not brazil
        if md_code > 1:
            return 0.5
        else:
            return 0        

    def is_valid_mmsi( self, mmsi ):
        # Converte o MMSI para string para facilitar a manipulação
        mmsi_str = str(mmsi)
    
        # Verifica se o MMSI tem exatamente nove dígitos
        if len(mmsi_str) == 9 and mmsi_str.isdigit():
            return 1
        else:
            return 0

    def mmsi_valid( self, trajs ):
        mmsis_valid = []
        for traj in tqdm( trajs.trajectories ):
            mmsi = traj.df['mmsi'].iloc[0]
            mmsis_valid.append( self.validate_mmsi( mmsi ) )
        return mmsis_valid

    def is_brazilian_mmsi(self, mmsi):
        """
        Verifica se um número MMSI é brasileiro.
        
        Args:
        mmsi (int ou str): O MMSI a ser verificado.
        
        Returns:
        bool: True se o MMSI é brasileiro, False caso contrário.
        """
        # Converte o MMSI para string para garantir a manipulação correta
        mmsi_str = str(mmsi)
        
        # Verifica se o MMSI tem nove dígitos e começa com um MID do Brasil
        if len(mmsi_str) == 9 and mmsi_str[:3] in ('710', '711', '712', '713', '725'):
            return 1
        else:
            return 0

    # Build meta model df 
    def predict_all_behaviors( self ):
        self.df_metamodelo = pd.DataFrame( )
        trajs = self.trajs
        trajs_info = self.trajs_info

        self.rules_get_crawler_vessel_info( trajs_info[ trajs_info['mmsi'] > 0 ]['mmsi'].values.astype(int) )
        
        self.df_metamodelo["traj_id"] = trajs_info["traj_id"]
        # self.df_metamodelo["ft"]  = self.detect_fishing_trajectories( trajs )
        self.df_metamodelo["ft"]  = self.detect_fishing_trajectories_gb( trajs_info, trajs )
        self.df_metamodelo["enc"] = self.detect_encounters_trajectories( trajs )
        self.df_metamodelo["loi"] = self.detect_loitering_trajectories( trajs )
        self.df_metamodelo["dark_ship"] = self.detect_gap_on_trajectories( trajs )
        self.df_metamodelo["spoofing"] = self.detect_spoofing_on_trajectories( trajs )
        self.df_metamodelo["dist_costa"] = self.rules_calc_distances_to_coast( trajs )
        # self.df_metamodelo["dentro_zee"] = self.rules_calc_inside_zee( trajs )
        # no preprocessamento filtramos por somente pontos dentro da ZEE
        self.df_metamodelo["dentro_zee"] = 1
        self.df_metamodelo["dentro_mt"] = self.rules_calc_inside_mt(self.df_metamodelo)
        self.df_metamodelo["dentro_apa"] = self.rules_calc_inside_apa( trajs )
        self.df_metamodelo["out_of_anchor_zone"] = self.rules_calc_inside_anchorage_zones( trajs )
        self.df_metamodelo["in_fpso_area"] = self.rules_calc_inside_fpso_area( trajs )

        flag_brazil, flag_unknow, flag_other = self.rules_get_vessel_flag( self.df_metamodelo["traj_id"] )
        self.df_metamodelo["flag_brazil"] = flag_brazil
        self.df_metamodelo["flag_unknow"] = flag_unknow
        self.df_metamodelo["flag_other"] = flag_other

        type_fishing, type_other, type_unknow, type_offshore, type_tanker, type_tug, type_anti_pollution, type_cargo, type_research, type_buoy = self.rules_get_vessel_type( self.df_metamodelo["traj_id"] )
        self.df_metamodelo["type_fishing"] = type_fishing
        self.df_metamodelo["type_other"] = type_other
        self.df_metamodelo["type_unknow"] = type_unknow
        self.df_metamodelo["type_offshore"] = type_offshore
        self.df_metamodelo["type_tanker"] = type_tanker
        self.df_metamodelo["type_tug"] = type_tug
        self.df_metamodelo["type_anti_pollution"] = type_anti_pollution
        self.df_metamodelo["type_cargo"] = type_cargo
        self.df_metamodelo["type_research"] = type_research
        self.df_metamodelo["type_buoy"] = type_buoy
        
        self.df_metamodelo["classificacao"] = None
        self.df_metamodelo["predicao"] = None

        self.df_metamodelo["id"] = None
        self.df_metamodelo["traj_fk"] = self.trajs_fk

        self.df_metamodelo["cog_diff"] = self.rules_cog_diff( trajs )
        self.df_metamodelo["sog_diff"] = self.rules_sog_diff( trajs )

        self.df_metamodelo["mmsi_valid"] = self.mmsi_valid( trajs )

        # if the ship is arriving (positive) or leaving the harbor (negative)
        self.df_metamodelo["arriving"] = self.rules_calc_arring_trajs( trajs )
        
        # if the ship has stopped, the time in hours.
        self.df_metamodelo["time_stopped_h"] = self.rules_time_stopped_trajs( trajs )

        return self.df_metamodelo

    def update_trajs_index( self ):
        
        for i in range( len(self.trajs) ):
            traj = self.trajs.trajectories[i]
            # atualiza o fk da trajetoria inserida no banco
            traj.df['traj_fk'] = self.trajs_fk[i]

    def build_all_sources( self ):
        print("Building sources ...")

        # insere trajetorias no db
        # self.db.delete_all_trajs( )
        self.trajs_fk = self.db.insere_trajs( self.trajs )

        self.update_trajs_index( )

        gdf  = self.gdf
        # build transmission geohash map 
        self.build_gap_on_trajectories( gdf )

        # build anchorage zone polygons
        self.az = AnchorageZone( gdf )
        self.az.build_anchorage_zones( resolution=6 )

        # build fpso areas
        self.fpso = FPSO(15000)
        print("Building sources finished.")

    def get_meta_model( self ):
        return self.df_metamodelo


    # def detect_behavior(self):
    #     # Aplicar o modelo aos dados
    #     # Detectar comportamentos específicos
    #     behavior_output = self.model.predict(self.data)
    #     return behavior_output

# Exemplo de uso
# data = # Dados processados relevantes
# behavior_model = BehaviorDetectionModel(data)
# detected_behavior = behavior_model.detect_behavior()