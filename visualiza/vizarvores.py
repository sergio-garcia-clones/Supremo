# -*- coding:utf-8 -*-
"""
Visualizações usando o módulo arvore
"""

__author__="flavio"
__date__ ="$02/05/2011 15:40:23$"

from sqlalchemy.ext.sqlsoup import SqlSoup
from matplotlib.colors import rgb2hex
from matplotlib import cm
from collections import defaultdict
from arvore import *
import numpy as np

MySQLServer = "mysql://root:password@E04324"

def decisoes_por_classe():
    Q = dbdec.execute("SELECT relator,tipo,proc_classe, count(*) FROM decisao WHERE DATE_FORMAT(data_dec,'%Y%')=1998 GROUP BY relator,tipo")
    arvores = {}
    decs = Q.fetchall()
    #cria Bosque
    bosque = Bosque('bosque1')
    bosque.scene.select()
    #cria arvores
    alts = np.array([d[3] for d in decs], 'float64')
    alts  = alts/alts.max()+0.8 #alturas das árvores.

    for d,a in zip(decs,alts):
        if d[0] in arvores or not d[0]:
            continue
        r=random()*10
        ang = random()*2*pi
        arvores[d[0]]=Arvore(frm=bosque.frame,nome=d[0],altura=a,pos=vector(r*cos(ang),0,r*sin(ang)))
    
    #cria primeiro nível de ramos
    for d in decs:
        if not d[0]: continue
        ramo1 = d[1] if d[1] else 'outros'
        r1 = arvores[d[0]].add_ramo(ramo1,'tronco', (0.7,0.3,0.05), 0.5, 0.6, pi/3.0)
        #Cria segundo nivel de ramos e folhas
        classes_min = defaultdict(lambda:defaultdict(lambda:set()))
        for d in decs:
            if not d[0]: continue
            if d[1] !=r1.nome: continue # cria só os ramos secundários de r1
#            ramo1 = d[1] if d[1] else 'outros'
            if d[2] in classes_min[d[0]][ramo1]:
                continue
            else:
                r2 = arvores[d[0]].add_ramo(d[2],r1,(0.7,0.3,0.05), 0.45, 0.5, pi/3.0)
                r2.add_folhas(d[3])

    bosque.scene.visible=1

if __name__ == "__main__":
    dbgrafo = SqlSoup("%s/SEN_Grafo" % MySQLServer)
    dbsupremo =  SqlSoup("%s/Supremo_new" % MySQLServer)
    dbdec = SqlSoup("%s/STF_Analise_Decisao" % MySQLServer)
    decisoes_por_classe()
