select * from metamodelo m ;


select *
 from classificacao c 



select *
from info_navio in2 
where in2.mmsi  = 8602309


select count(*)
from encounters e 

select *
from dbscan d 

SELECT * FROM dbscan

select * from kmeans

SELECT classificacao FROM kmeans WHERE cluster = 0


SELECT count(*)
from metamodelo m
where m.dentro_apa = 1
  and m.type_fishing = 1;
  

where classificacao is not NULL


update metamodelo set classificacao = NULL 
where in_fpso_area = 1


UPDATE metamodelo
SET classificacao = NULL
WHERE traj_id not in (
	SELECT traj_id 
	from metamodelo
	where classificacao is not NULL
	LIMIT 100
);


SELECT *
from metamodelo m
where m.id = 1105464;

SELECT *
from metamodelo m
where m.dentro_apa = 1
  and m.type_unknow = 1
  and m.ft > 0.5
  and m.classificacao is NULL
  and m.dist_costa > 5 and m.dist_costa < 6


UPDATE metamodelo  
   SET type_fishing=1, type_unknow=0, type_other=0
where dentro_apa = 1
  and type_unknow = 1
  and ft > 0.5
  and classificacao is NULL
  and dist_costa > 5 and dist_costa < 6
  
select *
from info_navio in2 
where in2.mmsi = 982570046;


SELECT count(*)
from metamodelo m
where m.synthetic = 1;

-- stellar banner
select *
from metamodelo m
where traj_id like '538006941%';



--where m.classificacao = 'atividade_suspeita'
where m.classificacao = 'atividade_anomala'



SELECT *
from metamodelo m
where m.flag_other = 1
  and m.ft > 0.5
  and m.type_fishing = 1

  
 SELECT count(*) as c
from metamodelo m
where m.synthetic = 1
--group by m.synthetic 

--where m.synthetic is NULL 

--update metamodelo 
--set synthetic = 7
--where synthetic is NULL;



where classificacao is not NULL

select *
from metamodelo m;

select * 
from metamodelo m 
where m.id = 947739;

SELECT * FROM metamodelo WHERE classificacao is NULL and synthetic = 1;


select *
from encounters e
where e.traj_id_2 = '710801725_20'

select *
from trajetorias t
where t.id = 52990

SELECT t.*
from metamodelo m, trajetorias t 
where m.traj_fk = t.id 
  and m.id = 22714


  select count(*)
  from classificacao c
  
select *
from encounters e
where traj_id_1 like "636013630%"


select count(*)
from trajetorias;
  
  
update metamodelo set synthetic = NULL;
 
delete from metamodelo; 
delete from anchor_zone; 
delete from dbscan; 
delete from kmeans; 
delete from encounters; 
delete from historico_transmissoes_ais; 
delete from trajetorias; 
delete from classificacao; 


INSERT INTO metamodelo (traj_id, ft, enc, loi, dark_ship, spoofing, dist_costa, dentro_zee, dentro_mt, dentro_apa, out_of_anchor_zone, in_fpso_area, flag_brazil, flag_unknow, flag_other, type_fishing, type_other, type_unknow, classificacao, predicao) 
VALUES ('3660524_1',
 5.443539066618541e-06,
 0,
 0.0005374746397137642,
 0,
 0,
 87.6980224396038,
 1,
 1,
 0,
 1,
 0,
 0,
 1,
 0,
 0,
 0,
 1,
 NULL,
 NULL)
