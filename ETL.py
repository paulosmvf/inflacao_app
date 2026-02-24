# ================================================================================================================================
# Coletando e tratando dados dos principais índices de inflação
# Autor: Paulo Mourão
# ================================================================================================================================

# Importando funções e bibliotecas
from utils import *

# Importando bases pela API do IPEA

# Definindo ano inicial (a série começará em t+1)
ano_inicial = 1993

# Séries de interesse
codigos_series = {
    'IPCA': 'PRECOS12_IPCAG12',
    'IPCA-15': 'PRECOS12_IPCA15G12',
    'IPC-Fipe': 'FIPE12_FIPE0001',
    'INPC': 'PRECOS12_INPCBR12',
    'IGPM': 'IGP12_IGPMG12',
    'SELIC': 'BM12_TJOVER12'
}

# Consultando séries
series = importar_series_temporais(codigos_series, ano_inicial)

# Motando base final

# Calculando as taxas de variação e fatores mensais a partir dos número-índices
series = calcular_fatores_a_partir_variacao(series)

# Inicializando o DataFrame final com o primeiro DataFrame do dicionário
merged_df = list(series.values())[0]

# Realizando o merge sucessivo dos DataFrames restantes
for key, df in list(series.items())[1:]:
    merged_df = pd.merge(merged_df, df, on='DATE', how='outer')

# Formatando o dataframe final
merged_df[merged_df.columns[1:]] = merged_df[merged_df.columns[1:]]
merged_df = merged_df.astype('str').apply(lambda x: x.str.replace('.',','))
merged_df = merged_df.apply(lambda x: x.str.replace('nan',''))

# Salvando o resultado
merged_df.to_csv('dataset.csv', sep=';', index=False)

# Visualizando
merged_df