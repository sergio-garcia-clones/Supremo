import difflib
from collections import defaultdict
import re
import json
#from sqlalchemy.ext.sqlsoup import SqlSoup
from BeautifulSoup import BeautifulSoup
#db = SqlSoup('mysql://root:password@emapserv/Supremo')
#print db.t_decisoes.all()
import MySQLdb
from salva import *

#Configura conexoes
db=MySQLdb.connect(host="E04324", user="root", passwd="password",db="Supremo")

cur=db.cursor()


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
        return json.dumps(dict(d))
        
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
        rawstr = r""">*\s*([A-Z]{2,3}\s*-\s*[A-Z,0-9]*)|(CF)|("CAPUT")\s+"""
        compile_obj = re.compile(rawstr)
        for p in pieces:
            match_obj = compile_obj.findall(p)
            matches = []
            for m in match_obj:
                matches.append([i for i in m if i][0])
            if matches:
                if 'FED' in matches[0]:# == 'LEG-FED':
                    self.data['LEG-FED'].append(matches)
                elif 'EST' in matches[0]:# == 'LEG-EST':
#                    print p
                    self.data['LEG-EST'].append(matches)
                elif matches[0] == 'LEG-MUN':
#                    print p
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
    cursor.execute('select decisao,tipo,data_publicacao,data_decisao from t_decisoes limit %s,%s'%(inicio, num))
    dados = cursor.fetchmany(num)
    UFs = []
    legs = BuscaLeis()
    for d in dados:
        sopa = BeautifulSoup(d[0].strip('[]'),  fromEncoding='IBM855')
#        print sopa.originalEncoding
        # Tag contendo informacao de UF
        tipo  = d[1]
        data_p = d[2]
        data_d = d[3]
        c = sopa.strong
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
            print legs.analisa(l.contents[0])
            
    print "Falhas em Extracao de UFs: ",  num-len(UFs)
#        print unicode(c),  type(c)
    
if __name__ == "__main__":
    pass
#    print conta_campos(cur)
    extrai_dados(cur,  5000, 1000)
