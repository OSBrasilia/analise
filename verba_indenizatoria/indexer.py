#!/usr/bin/env python3

from pathlib import Path
import pandas as pd
from espandas import Espandas
import re

DEP = 'Deputado (a)'
IMOV = 'Imóvel'
MAQ = 'Máquina e equipamento'
VEI = 'Veículo',
COMB = 'Combustível e lubrificante'
ASS = 'Assosoria ou consultoria'
DIV = 'Divulgação da atividade parlamentar'
OUT = 'Outros'

RUB = 'Rubrica'

PEND = 'pendente'

def read_df(filepath):
    df = pd.read_csv(filepath, sep=';', thousands='.', decimal=',').fillna(0.0)
    df = df.set_index([DEP, 'date'])
    pieces = []
    for col in [IMOV, MAQ, VEI, COMB, ASS, DIV, OUT]:
        piece = df[df[col] > 0][col]
        piece = piece.unstack()
        piece[RUB] = col
        pieces.append(piece)
    df = pd.concat(
    df['indexId'] = df.apply(lambda row: '%d_%d_%d' % (row['year'], row['month'], row.name), axis=1)
    return df


if __name__ == '__main__':
    esp = Espandas()
    pieces = []
    for f in Path('files').glob('*.df.csv'):
        df = read_df(f)
        pieces.append(df)
    df = pd.concat(pieces)
    esp.es_write(df, 'verba-indenizatoria', 'verba_doc')

