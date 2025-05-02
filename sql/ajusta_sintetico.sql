UPDATE metamodelo  
   SET type_fishing=1, type_unknow=0, type_other=0
where dentro_apa = 1
  and type_unknow = 1
  and ft > 0.5
  and classificacao is NULL
  and dist_costa > 5 and dist_costa < 6


-- Dentro APA, Type fishing (pesca ilegal) 20
SELECT count(*)
from metamodelo m
where m.dentro_apa = 1
  and m.ft > 0.5
  and m.type_fishing = 1

-- Dentro APA, Type unknow (suspeito) 430
SELECT count(*)
from metamodelo m
where m.dentro_apa = 1
  and m.type_unknow = 1
  and m.ft > 0.5
  
-- Dentro ZEE, tipo Pesca, flag outro 73
SELECT count(*)
from metamodelo m
where m.dentro_zee = 1
  and m.type_fishing  = 1
  and m.flag_other = 1
  and m.ft > 0.5
  
-- Dentro ZEE, tipo Pesca, flag brazil 259
SELECT count(*)
from metamodelo m
where m.dentro_zee = 1
  and m.type_fishing  = 1
  and m.flag_brazil = 1
  and m.ft > 0.5

  
-- Dentro ZEE, tipo Pesca, flag desconhecido 150
 SELECT count(*)
from metamodelo m
where m.dentro_zee = 1
  and m.type_fishing  = 1
  and m.flag_unknow = 1
  and m.ft > 0.5

--- UPDATES  
  SELECT count(*)
from metamodelo m
where m.dentro_zee = 1
  and m.type_fishing  = 1
  and m.flag_other = 1
  and m.ft > 0.5
