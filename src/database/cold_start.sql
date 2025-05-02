-- Zera tudo

UPDATE metamodelo 
SET classificacao = NULL;

DELETE FROM classificacao ;

--------------------------------------------------------
--Pesca Ilegal (250)
--------------------------------------------------------
-- Embarcações de pesca apresentando comportamento de pesca dentro de APAs; 
SELECT *
from metamodelo m
where m.dentro_apa = 1
  and m.type_fishing = 1
  and m.ft > 0.5
  and m.dist_costa > 5
  and m.synthetic = 1
  and m.classificacao is null 
ORDER BY RANDOM()
LIMIT 10

UPDATE metamodelo 
SET classificacao = 'pesca_ilegal'
where rowid in (
	SELECT rowid
	from metamodelo m
	where m.dentro_apa = 1
	  and m.type_fishing = 1
	  and m.ft > 0.5
	  and m.dist_costa > 5
	  and m.synthetic = 1
	  and m.classificacao is null 	  
	ORDER BY RANDOM()
	LIMIT 10
);

  
-- Embarcações de pesca de bandeira estrangeira apresentando comportamento de pesca dentro da ZEE ou MT
 SELECT count(*)
from metamodelo m
where (m.dentro_zee = 1 or m.dentro_mt = 1)
  and m.dist_costa > 5
  and m.type_fishing = 1
  and m.ft > 0.5
  and m.flag_other = 1
  and m.synthetic = 1
  and m.classificacao is null 
ORDER BY RANDOM()
LIMIT 125;

UPDATE metamodelo 
SET classificacao = 'pesca_ilegal'
where rowid in (
	 SELECT rowid
	from metamodelo m
	where (m.dentro_zee = 1 or m.dentro_mt = 1)
	  and m.dist_costa > 5
	  and m.type_fishing = 1
	  and m.ft > 0.5
	  and m.flag_other = 1
	  and m.synthetic = 1
	  and m.classificacao is null 
	ORDER BY RANDOM()
	LIMIT 10
);
------------------------------------------------------------
-- Atividade Suspeita (250)
------------------------------------------------------------
-- Embarcações realizando encontros a mais de 12 MN fora da área de FPSO; 
 SELECT count(*)
from metamodelo m
where m.dentro_zee = 1
  and m.dist_costa > 12
  and m.in_fpso_area = 0
  and m.enc = 1
  and m.synthetic = 1
  and m.classificacao is null 
ORDER BY RANDOM()
LIMIT 50;

UPDATE metamodelo 
SET classificacao = 'atividade_suspeita'
where rowid in (
	 SELECT rowid
	from metamodelo m
	where m.dentro_zee = 1
	  and m.dist_costa > 12
	  and m.in_fpso_area = 0
	  and m.enc = 1
	  and m.synthetic = 1
	  and m.classificacao is null 
	ORDER BY RANDOM()
	LIMIT 10
);

-- Embarcações que não sejam rebocadores, realizando encontros dentro do MT em áreas fora de FPSO ; 
 SELECT count(*)
from metamodelo m
where m.dentro_mt = 1
  and m.type_tug <> 1
  and m.dist_costa > 5
  and m.type_fishing <> 1
  and m.in_fpso_area = 0
  and m.enc = 1
  and m.classificacao is null 
ORDER BY RANDOM()
LIMIT 50;

UPDATE metamodelo 
SET classificacao = 'atividade_suspeita'
where rowid in (
	 SELECT rowid
	from metamodelo m
	where m.dentro_mt = 1
	  and m.type_tug <> 1
	  and m.dist_costa > 5
	  and m.type_fishing <> 1
	  and m.in_fpso_area = 0
	  and m.enc = 1
	  and m.classificacao is null 
	ORDER BY RANDOM()
	LIMIT 10
);

-- Embarcações de pesca apresentando comportamento de loitering ou fundeadas dentro de APAs; 
 SELECT count(*)
from metamodelo m
where m.dentro_apa = 1
  and m.type_fishing = 1
  and (m.loi > 0.5  or m.time_stopped_h > 2)
  and m.synthetic = 1
  and m.classificacao is null 
ORDER BY RANDOM()
LIMIT 50;

UPDATE metamodelo 
SET classificacao = 'atividade_suspeita'
where rowid in (
	 SELECT rowid
	from metamodelo m
	where m.dentro_apa = 1
	  and m.type_fishing = 1
	  and (m.loi > 0.5  or m.time_stopped_h > 2)
	  and m.synthetic = 1
	  and m.classificacao is null 
	ORDER BY RANDOM()
	LIMIT 10
);

-- Embarcações sem identificação apresentando comportamentos de pesca dentro de APAs; 
 SELECT count(*)
from metamodelo m
where m.dentro_apa = 1
  and m.type_unknow = 1
  and m.ft > 0.5
  and m.synthetic = 1
  and m.classificacao is null 
ORDER BY RANDOM()
LIMIT 50;

UPDATE metamodelo 
SET classificacao = 'atividade_suspeita'
where rowid in (
	 SELECT rowid
	from metamodelo m
	where m.dentro_apa = 1
	  and m.type_unknow = 1
	  and m.ft > 0.5
	  and m.synthetic = 1
	  and m.classificacao is null 
	ORDER BY RANDOM()
	LIMIT 10
);

-- Embarcações de pesca estrangeiras apresentando comportamentos de gaps em trajetórias, spoofing ou loitering dentro da ZEE ou MT; 
 SELECT count(*)
from metamodelo m
where (m.dentro_mt = 1 or m.dentro_zee = 1)
  and m.type_fishing = 1
  and m.flag_other = 1
  and (m.dark_ship > 0 or m.spoofing > 0 or m.loi > 0.5)
  and m.classificacao is null 
ORDER BY RANDOM()
LIMIT 25;

--UPDATE metamodelo 
--SET classificacao = 'atividade_suspeita'
--where rowid in (
--	 SELECT rowid
--	from metamodelo m
--	where (m.dentro_mt = 1 or m.dentro_zee = 1)
--	  and m.type_fishing = 1
--	  and m.flag_other = 1
--	  and (m.dark_ship > 0 or m.spoofing > 0 or m.loi > 0.5)
--	  and m.classificacao is null 
--	ORDER BY RANDOM()
--	LIMIT 10
--);

-- Embarcações estrangeiras de pesca fundeadas dentro da ZEE por mais de 2 horas.
 SELECT count(*)
from metamodelo m
where m.dentro_zee = 1
  and m.type_fishing = 1
  and m.flag_other = 1
  and m.time_stopped_h > 2
  and m.classificacao is null 
ORDER BY RANDOM()
LIMIT 25;

UPDATE metamodelo 
SET classificacao = 'atividade_suspeita'
where rowid in (
	 SELECT rowid
	from metamodelo m
	where m.dentro_zee = 1
	  and m.type_fishing = 1
	  and m.flag_other = 1
	  and m.time_stopped_h > 2
	  and m.classificacao is null 
	ORDER BY RANDOM()
	LIMIT 10
);

--------------------------------------
-- Atividades Anomalas
--------------------------------------
-- Embarcações sem identificação dentro do MT apresentando algum comportamento anômalo; 
 SELECT count(*)
from metamodelo m
where m.dentro_mt = 1
  and m.mmsi_valid = 0
  and m.flag_unknow = 1
  and m.dist_costa > 5
  and ( m.ft > 0.5 and m.loi > 0.5 )
  and m.enc = 0
  and m.classificacao is null 
ORDER BY RANDOM()
LIMIT 30;

UPDATE metamodelo 
SET classificacao = 'atividade_anomala'
where rowid in (
	 SELECT rowid
	from metamodelo m
	where m.dentro_mt = 1
	  and m.mmsi_valid = 0
	  and m.flag_unknow = 1
	  and m.dist_costa > 5
	  and ( m.ft > 0.5 and m.loi > 0.5 )
	  and m.enc = 0
	  and m.classificacao is null 
	ORDER BY RANDOM()
	LIMIT 10
);

-- Embarcações dentro do MT fundeadas em locais próximos à costa e afastadas de portos; 
 SELECT count(*)
from metamodelo m
where m.dentro_mt = 1
  and m.time_stopped_h > 96
  and m.dist_costa > 5
  and m.dist_costa < 8
  and m.out_of_anchor_zone = 1
  and m.enc = 0
  and m.classificacao is null 
ORDER BY RANDOM()
LIMIT 32;

UPDATE metamodelo 
SET classificacao = 'atividade_anomala'
where rowid in (
	 SELECT rowid
	from metamodelo m
	where m.dentro_mt = 1
	  and m.time_stopped_h > 96
	  and m.dist_costa > 5
	  and m.dist_costa < 8
	  and m.out_of_anchor_zone = 1
	  and m.enc = 0
	  and m.classificacao is null 
	ORDER BY RANDOM()
	LIMIT 10
);


-- Comportamento de embarcações inconsistentes com seu tipo (ex.: navios de carga em trajetórias sinuosas); 
SELECT count(*)
from metamodelo m
where ( m.type_tanker = 1 or m.type_offshore = 1 or m.type_cargo = 1 )
  and (m.ft > 0.5 )
  and m.sog_diff > 1
  and m.cog_diff > 50
  and m.dist_costa > 20
  and m.in_fpso_area = 0
  and m.time_stopped_h < 1
  and m.enc = 0
  and m.synthetic = 1
  and m.classificacao is null 
ORDER BY RANDOM()
LIMIT 30;


UPDATE metamodelo 
SET classificacao = 'atividade_anomala'
where rowid in (
	SELECT rowid
	from metamodelo m
	where ( m.type_tanker = 1 or m.type_offshore = 1 or m.type_cargo = 1 )
	  and (m.ft > 0.5 )
	  and m.sog_diff > 1
	  and m.cog_diff > 50
	  and m.dist_costa > 5
	  and m.in_fpso_area = 0
	  and m.time_stopped_h < 1
	  and m.enc = 0
	  and m.synthetic = 1
	  and m.classificacao is null 
	ORDER BY RANDOM()
	LIMIT 10
);

-- Embarcações sem identificação apresentando comportamento de pesca dentro do MT ou ZEE; 
 SELECT count(*)
from metamodelo m
where m.type_unknow = 1
  and m.mmsi_valid = 0
  and m.ft > 0.5
  and m.sog_diff > 1
  and m.cog_diff > 50
  and m.dist_costa > 5
  and m.enc = 0
  and m.synthetic = 1
  and m.classificacao is null 
ORDER BY RANDOM()
LIMIT 30;

UPDATE metamodelo 
SET classificacao = 'atividade_anomala'
where rowid in (
	 SELECT rowid
	from metamodelo m
	where m.type_unknow = 1
	  and m.mmsi_valid = 0
	  and m.ft > 0.5
	  and m.sog_diff > 1
	  and m.cog_diff > 50
	  and m.dist_costa > 5
	  and m.enc = 0
	  and m.synthetic = 1
	  and m.classificacao is null 
	ORDER BY RANDOM()
	LIMIT 10
)

-- Embarcações sem identificação apresentando comportamento de loitering dentro de APAs;
 SELECT count(*)
from metamodelo m
where m.type_unknow = 1
  and m.mmsi_valid = 0
  and m.loi > 0.5
  and m.dist_costa > 5
  and m.enc = 0
  and m.dentro_apa = 1
  and synthetic = 1
  and m.classificacao is null 
ORDER BY RANDOM()
LIMIT 30;

UPDATE metamodelo 
SET classificacao = 'atividade_anomala'
where rowid in (
	 SELECT rowid
	from metamodelo m
	where m.type_unknow = 1
	  and m.mmsi_valid = 0
	  and m.loi > 0.5
	  and m.dist_costa > 5
	  and m.enc = 0
	  and m.dentro_apa = 1
	  and synthetic = 1
	  and m.classificacao is null 
	ORDER BY RANDOM()
	LIMIT 10
);


-- Embarcações de pesca com nome em português, sem bandeira e próximo a costa;
SELECT count(*)
from metamodelo m
where m.type_fishing = 1
  and m.flag_unknow = 1
  and m.dist_costa > 5 
  and m.dist_costa < 12
  and m.ft > 0.5
  and m.cog_diff > 50
  and m.synthetic = 1
  and m.classificacao is null 
ORDER BY RANDOM()
LIMIT 30;

UPDATE metamodelo 
SET classificacao = 'atividade_anomala'
where rowid in (
	SELECT rowid
	from metamodelo m
	where m.type_fishing = 1
	  and m.flag_unknow = 1
	  and m.dist_costa > 5 
	  and m.dist_costa < 12
	  and m.ft > 0.5
	  and m.cog_diff > 50
	  and m.synthetic = 1
	  and m.classificacao is null 
	ORDER BY RANDOM()
	LIMIT 10
);


-- Embarcações de tipo diferente de pesca ou sem identificação apresentando comportamento de loitering ou fundeadas dentro de APAs por mais de 2 horas; 
 SELECT *
from metamodelo m
where (m.type_unknow = 1 or m.mmsi_valid = 0)
  and m.dentro_apa = 1
  and m.dist_costa > 5 
  and m.loi > 0.5 
  and m.time_stopped_h > 2
  and m.classificacao is null 
  and m.out_of_anchor_zone = 1
ORDER BY RANDOM()
LIMIT 1;

--UPDATE metamodelo 
--SET classificacao = 'atividade_anomala'
--where rowid in (
--	 SELECT rowid
--	from metamodelo m
--	where (m.type_unknow = 1 or m.mmsi_valid = 0)
--	  and m.dentro_apa = 1
--	  and m.dist_costa > 5 
--	  and m.loi > 0.5 
--	  and m.time_stopped_h > 2
--	  and m.classificacao is null 
--	  and m.out_of_anchor_zone = 1
--	ORDER BY RANDOM()
--	LIMIT 1
--);


-- Embarcações sem identificação apresentando comportamentos de spoofing e gaps em trajetórias dentro do MT;
 SELECT *
from metamodelo m
where (m.type_unknow = 1 or m.mmsi_valid = 0)
  and m.dentro_mt = 1
  and m.dist_costa > 5 
  and m.dark_ship > 0 
  and m.spoofing > 0
  and m.classificacao is null 
ORDER BY RANDOM()
LIMIT 3;

--UPDATE metamodelo 
--SET classificacao = 'atividade_anomala'
--where rowid in (
--	 SELECT rowid
--	from metamodelo m
--	where (m.type_unknow = 1 or m.mmsi_valid = 0)
--	  and m.dentro_mt = 1
--	  and m.dist_costa > 5 
--	  and m.dark_ship > 0 
--	  and m.spoofing > 0
--	  and m.classificacao is null 
--	ORDER BY RANDOM()
--	LIMIT 3
--);

-- Contatos do tipo boia com velocidade média acima de 2 nós.
 SELECT *
from metamodelo m
where m.type_buoy = 1
  and m.sog_diff > 2 
  and m.classificacao is null 
ORDER BY RANDOM()
LIMIT 66;


UPDATE metamodelo 
SET classificacao = 'atividade_anomala'
where rowid in (
	 SELECT rowid
	from metamodelo m
	where m.type_buoy = 1
	  and m.sog_diff > 2 
	  and m.classificacao is null 
	ORDER BY RANDOM()
	LIMIT 10
);

---------------------------------
-- Atividade Normal
---------------------------------
-- Embarcações em rotas normais, com dados completos (MMSI, nome, bandeira, etc.) que não apresentem comportamentos atípicos para a localidade;
 SELECT count(*)
from metamodelo m
where m.mmsi_valid > 0
  and m.ft < 0.5 
  and m.enc = 0
  and m.loi < 0.5
  and m.dark_ship = 0
  and m.spoofing = 0
  and m.synthetic = 1
  and m.classificacao is null 
ORDER BY RANDOM()
LIMIT 80;

UPDATE metamodelo 
SET classificacao = 'atividade_normal'
where rowid in (
	 SELECT rowid
	from metamodelo m
	where m.mmsi_valid > 0
	  and m.ft < 0.5 
	  and m.enc = 0
	  and m.loi < 0.5
	  and m.dark_ship = 0
	  and m.spoofing = 0
	  and m.synthetic = 1
	  and m.classificacao is null 
	ORDER BY RANDOM()
	LIMIT 10
);

-- Embarcações do tipo offshore realizando encontros dentro de áreas de FPSO;
 SELECT *
from metamodelo m
where m.in_fpso_area = 1
  and m.enc = 1 
  and m.synthetic = 1
  and m.classificacao is null 
ORDER BY RANDOM()
LIMIT 70;

UPDATE metamodelo 
SET classificacao = 'atividade_normal'
where rowid in (
	 SELECT rowid
	from metamodelo m
	where m.in_fpso_area = 1
	  and m.enc = 1 
	  and m.synthetic = 1
	  and m.classificacao is null 
	ORDER BY RANDOM()
	LIMIT 10
);

-- Contatos do tipo boia com velocidade média abaixo de 2 nós.
 SELECT count(*)
from metamodelo m
where m.type_buoy = 1
  and m.sog_diff < 2 
  and m.classificacao is null 
ORDER BY RANDOM()
LIMIT 50;

UPDATE metamodelo 
SET classificacao = 'atividade_normal'
where rowid in (
	 SELECT rowid
	from metamodelo m
	where m.type_buoy = 1
	  and m.sog_diff < 2 
	  and m.classificacao is null 
	ORDER BY RANDOM()
	LIMIT 10
);

-- Embarcações do tipo rebocador realizando encontros próximo a costa.
 SELECT count(*)
from metamodelo m
where m.type_tug = 1
  and m.enc = 1
  and m.dist_costa < 100
  and m.synthetic = 1
  and m.classificacao is null 
ORDER BY RANDOM()
LIMIT 50;

UPDATE metamodelo 
SET classificacao = 'atividade_normal'
where rowid in (
	 SELECT rowid
	from metamodelo m
	where m.type_tug = 1
	  and m.enc = 1
	  and m.dist_costa < 100
	  and m.synthetic = 1
	  and m.classificacao is null 
	ORDER BY RANDOM()
	LIMIT 10
);

-- Embarcações de pesca de bandeira brasileira pescando dentro da ZEE e MT.
 SELECT count(*)
from metamodelo m
where m.type_fishing = 1
  and (m.flag_brazil = 1 or m.mmsi_valid == 1)
  and m.ft > 0.5
  and m.classificacao is null 
ORDER BY RANDOM()
LIMIT 50;

UPDATE metamodelo 
SET classificacao = 'atividade_normal'
where rowid in (
	 SELECT rowid
	from metamodelo m
	where m.type_fishing = 1
	  and (m.flag_brazil = 1 or m.mmsi_valid == 1)
	  and m.ft > 0.5
	  and m.classificacao is null 
	ORDER BY RANDOM()
	LIMIT 10
);

-- Embarcações do tipo tanker, offshore e cargo realizando loitering ao chegar no MT;
SELECT count(*)
from metamodelo m
where ( m.type_tanker = 1 or m.type_offshore = 1 or m.type_cargo = 1 )
  and (m.ft > 0.5 or m.loi > 0.5 )
  and m.cog_diff > 50
  and m.dist_costa > 12
  and m.dist_costa < 100
  and m.in_fpso_area = 0
  and m.time_stopped_h > 1
  and m.enc = 0
  and m.synthetic = 1
  and m.classificacao is null 
ORDER BY RANDOM()
LIMIT 30;

UPDATE metamodelo 
SET classificacao = 'atividade_normal'
where rowid in (
	SELECT rowid
	from metamodelo m
	where ( m.type_tanker = 1 or m.type_offshore = 1 or m.type_cargo = 1 )
	  and (m.ft > 0.5 or m.loi > 0.5 )
	  and m.cog_diff > 50
	  and m.dist_costa > 12
	  and m.dist_costa < 100
	  and m.in_fpso_area = 0
	  and m.time_stopped_h > 1
	  and m.enc = 0
	  and m.synthetic = 1
	  and m.classificacao is null 
	ORDER BY RANDOM()
	LIMIT 10
);

-- Embarcações de pesca estrangeira com velocidade média acima de 8 knots.
SELECT count(*)
from metamodelo m
where m.type_fishing = 1
  and m.ft < 0.5
  and m.sog_diff > 8
  and m.time_stopped_h < 1
  and m.enc = 0
  and m.classificacao is null 
ORDER BY RANDOM()
LIMIT 30;

UPDATE metamodelo 
SET classificacao = 'atividade_normal'
where rowid in (
	SELECT rowid
	from metamodelo m
	where m.type_fishing = 1
	  and m.ft < 0.5
	  and m.sog_diff > 8
	  and m.time_stopped_h < 1
	  and m.enc = 0
	  and m.classificacao is null 
	ORDER BY RANDOM()
	LIMIT 10
);

-- Embarcações com comportamentos normais, velocidade acima de 2 knots e distância maior que 2MN da costa.
SELECT count(*)
from metamodelo m
where m.enc = 0 
  and m.ft < 0.5
  and m.loi < 0.5
  and m.dark_ship = 0
  and m.spoofing = 0
  and m.sog_diff > 2
  and m.time_stopped_h < 1
  and m.dist_costa > 2
  and m.synthetic = 1
  and m.classificacao is null 
ORDER BY RANDOM()
LIMIT 30;


UPDATE metamodelo 
SET classificacao = 'atividade_normal'
where rowid in (
	SELECT rowid
	from metamodelo m
	where m.enc = 0 
	  and m.ft < 0.5
	  and m.loi < 0.5
	  and m.dark_ship = 0
	  and m.spoofing = 0
	  and m.sog_diff > 2
	  and m.time_stopped_h < 1
	  and m.dist_costa > 2
	  and m.synthetic = 1
	  and m.classificacao is null 
	ORDER BY RANDOM()
	LIMIT 10
);