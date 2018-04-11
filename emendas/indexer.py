import pandas as pd
from espandas import Espandas
import re

location_re = re.compile(r'.*-\s+(plano piloto|gama|taguatinga|brazlândia|sobradinho|planaltina|paranoá|núcleo bandeirante|ceilândia|guará|cruzeiro|samambaia|santa maria|são sebastião|recanto das emas|lago sul|riacho fundo|lago norte|candangolândia|águas claras|sudoeste|varjão|park way|scia|jardim botânico|itapoã|sia|vicente pires|fercal)\b.*', re.IGNORECASE)
df_re = re.compile(r'.*-\s+distrito federal$', re.IGNORECASE)

def extract_location(val):
    """Extracts a location from the field."""
    m = location_re.match(val)
    if m is not None:
        return m.group(1).upper()
    elif df_re.match(val) is not None:
        return 'DF'
    else:
        return 'Outro'

def open(year):
    df = pd.read_csv('files/%d.csv' % year, sep=';', header=1, thousands='.', decimal=',')
    df = df[[c for c in df.columns if not c.startswith('Unnamed')]]
    df['indexId'] = pd.Series(('%d_%d' % (year, v) for v in df.index))
    df['Local'] = df['Subtítulo'].apply(extract_location)
    df['Ano'] = year
    return df


def index_year(esp, year, df):
    esp.es_write(df, 'emendas-%d' % year, 'emendas_doc')

if __name__ == '__main__':
    esp = Espandas()
    df = open(2018)
    index_year(esp, 2018, df)


