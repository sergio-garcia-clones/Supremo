# -*- coding:utf-8 -*-
import difflib
import re
import locale
import json
from collections import defaultdict
#from sqlalchemy.ext.sqlsoup import SqlSoup
from BeautifulSoup import BeautifulSoup
import MySQLdb
from MySQLdb.cursors import CursorUseResultMixIn,  SSCursor
#inicializa tabelas analiticas
from salva import *
setup_all(True)
create_all()



#from sqlalchemy.ext.sqlsoup import SqlSoup
#db = SqlSoup('mysql://root:password@emapserv/Supremo')
#print db.t_decisoes.all()
#Configura conexoes
#db = SqlSoup('mysql://root:password@emapserv/Supremo')
#print db.t_decisoes.all()

db=MySQLdb.connect(host="E04324", user="root", passwd="password",db="Supremo")
cur=db.cursor(cursorclass=SSCursor) #SSCursor mantem os resultados no servidor trazendo um resultados por vez. Essencial para que a consulta caiba na memoria.


def busca_UF(texto):
    """
    localiza e extrai referencias a unidade federal 
    que originou o processo
    """
    rawstr =r"\s/\s([A-Z]{2})\s+-"
    compile_obj = re.compile(rawstr)
    match_obj = compile_obj.search(texto)
#    print texto
    if match_obj:
#        print match_obj.groups()
        return match_obj.groups()[0]
        
class BuscaLeis:
    def __init__(self):
        self.data = defaultdict(lambda:[])

    def analisa(self, texto):
        """
        Recebe texto da secao legislacao de uma decisao
        e as analisa.
        """
        pieces = self.split_leis(texto)
        self.parse_leis(pieces)
        return self.dump_to_json()
        
    def dump_to_json(self):
        """
        Retorna informacoes coletadas por esta instancia
        como uma string em formato JSON
        """
        d = self.data
        self.data = defaultdict(lambda:[])
        return json.dumps(dict(d), ensure_ascii=False)
        
    def split_leis(self, texto):
        """
        separa texto em leis individuais
        """
        if not isinstance(texto,  str):
            texto = str(texto)
        pieces = []
        rawstr = r"""LEG-"""
        compile_obj = re.compile(rawstr, re.MULTILINE| re.UNICODE)
        pstart = [m.start() for m in compile_obj.finditer(texto) if m.start() !=-1]
        for i in range(len(pstart)):
            if i == len(pstart)-1:
                pieces.append(texto[pstart[i]:])
                break
            pieces.append(texto[pstart[i]:pstart[i+1]])
        return pieces
        
    def parse_leis(self, pieces):
        """
        Parseia cada lei classificando em Lei Federal, Estadual e Municipal 
        """
        locale.setlocale(locale.LC_ALL, 'pt_BR.ISO-8859-1') 
        rawstr = r""">*\s*([A-Z]{2,3}\s*-\s*.[A-Z0-9]*)|(CF)|("CAPUT")\s+"""
        compile_obj = re.compile(rawstr, re.LOCALE)
        for p in pieces:
            match_obj = compile_obj.findall(p)
            matches = []
            for m in match_obj:
                matches.append([i for i in m if i][0])
            if 'PAR-' in matches:
                print p
            if matches:
                if 'FED' in matches[0]:# == 'LEG-FED':
                    matches[0] = 'LEG-FED'
                    self.data['LEG-FED'].append(matches)
                elif 'EST' in matches[0]:# == 'LEG-EST':
#                    print p
                    matches[0] = 'LEG-EST'
                    self.data['LEG-EST'].append(matches)
                elif matches[0] == 'LEG-MUN':
#                    print p
                    self.data['LEG-MUN'].append(matches)
                elif matches[0] == 'LEG-MUM':
#                    print p
                    matches[0] = 'LEG-MUN'
                    self.data['LEG-MUN'].append(matches)
                elif matches[0] == 'LEG-DIS':
#                    print p
                    self.data['LEG-DIS'].append(matches)
                elif matches[0] == 'LEG-INT':
#                    print p
                    self.data['LEG-INT'].append(matches)
                else:
#                    print p,  matches[0]
                    self.data['outras'].append(matches)
#        print "texto: ", p
#        print "matches: ", matches
    
def conta_campos(cursor):
    cursor.execute('select decisao from t_decisoes limit 10000')
    decisoes = cursor.fetchmany(10000)
#    print decisoes
    campos = set([])
    for d in decisoes:
        s = BeautifulSoup(d[0].strip('[]'))#,  fromEncoding='IBM855')
        print s.originalEncoding
        h = [i.contents[0] for i in s.findAll('strong') if  len(i.contents)==1 and len(i.contents[0]) <16]
#        print h
        cs = set(h)
#        print cs
#TODO: contar ocorrencias usando defaultdict
        campos.update(cs)
    return campos


def extrai_dados(cursor,  inicio,  num):
    """
    Constroi nova tabela com Datas, Estado e leis referenciadas
    cursor ...
    """
    cursor.execute('select decisao,tipo,data_publicacao,data_decisao, id_processo from t_decisoes limit %s,%s'%(inicio, num))
#    dados = cursor.fetchmany(num)
    UFs = []
    legs = BuscaLeis()
    salva = SalvaNoBanco()
    n=0;
    d=cursor.fetchone() # usando Fetchone para economizar memoria
    while d != None:
        tipo  = d[1] #tipo da decisao: acordao, etc.
        data_p = d[2] #data de publicacao
        data_d = d[3] #data da decisao
        processo = d[4] # id do processo
        
        sopa = BeautifulSoup(d[0].strip('[]'),  fromEncoding='ISO8859-1')
#        print sopa.originalEncoding
        c = sopa.strong
        # Tag contendo informacao de UF
        uf = busca_UF(c.contents[0])
#        print uf
        if uf:
            UFs.append(uf)
        else:
            UFs.append('NA')

        # Tag contendo legislacao
        rs  = sopa.findAll('strong', text=re.compile('^Legisla'))
        if rs:
            l = rs[0].next.nextSibling
#            print len(l.contents)
            ljson = legs.analisa(l.contents[0])
            salva.salvar(data_d, data_p, tipo, processo, uf, ljson)
            if not n%500:
                print "Foram processadas %s decisoes"%n
                salva.commit_data()
        d = cursor.fetchone()
        n +=1
    salva.commit_data()
    print "Leis Diferentes: ",  salva.outrasleis
    print "Falhas em Extracao de UFs: ",  num-len(UFs)
    cursor.close()
#        print unicode(c),  type(c)
    
if __name__ == "__main__":
    pass
#    print conta_campos(cur)
    extrai_dados(cur,  0, 1000000)
    db.close()
