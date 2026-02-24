import os
import re
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="Índices de Inflação (Ipeadata)", layout="wide")


@st.cache_data(show_spinner=False)
def carregar_csv(uploaded_file: object | None, caminho_padrao: str = "dados.csv") -> pd.DataFrame:
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file, sep=";", decimal=",", encoding="utf-8")
    else:
        df = pd.read_csv(caminho_padrao, sep=";", decimal=",", encoding="utf-8")

    # Normaliza nome da coluna de data
    if "DATE" not in df.columns:
        raise ValueError("Coluna 'DATE' não encontrada.")

    df["DATE"] = pd.to_datetime(df["DATE"], errors="coerce")
    df = df.dropna(subset=["DATE"]).sort_values("DATE")

    # Garante numéricos (caso alguma coluna venha como string)
    for c in df.columns:
        if c == "DATE":
            continue
        df[c] = pd.to_numeric(df[c], errors="coerce")

    return df


def inferir_indices_e_tipos(colunas: list[str]) -> tuple[list[str], list[str]]:
    """
    Extrai:
      - índice: prefixo antes de "Variacao (%)", "Fator", "Fator Acumulado", etc.
      - tipo: sufixo padronizado (Variação (%), Fator, Fator Acumulado, Fator Correção Legal)
    """
    tipos_canon = {
        "Variacao (%)": "Variação (%)",
        "Fator": "Fator",
        "Fator Acumulado": "Fator Acumulado",
        "Fator Correção Legal": "Fator Correção Legal",
    }

    indices = set()
    tipos = set()

    padrao = re.compile(r"^(?P<idx>.+?)\s+(?P<tipo>Variacao \(%\)|Fator Correção Legal|Fator Acumulado|Fator)$")

    for c in colunas:
        if c == "DATE":
            continue
        m = padrao.match(c)
        if m:
            indices.add(m.group("idx").strip())
            tipos.add(tipos_canon[m.group("tipo")])

    return sorted(indices), sorted(tipos, key=lambda x: ["Variação (%)","Fator","Fator Acumulado","Fator Correção Legal"].index(x)
                                  if x in ["Variação (%)","Fator","Fator Acumulado","Fator Correção Legal"] else 99)


def coluna_do_indice(indice: str, tipo: str) -> str:
    # Mapeia tipo exibido -> padrão de coluna
    tipo_para_col = {
        "Variação (%)": "Variacao (%)",
        "Fator": "Fator",
        "Fator Acumulado": "Fator Acumulado",
        "Fator Correção Legal": "Fator Correção Legal",
    }
    return f"{indice} {tipo_para_col[tipo]}"


def para_formato_longo(df: pd.DataFrame, indices: list[str], tipos: list[str]) -> pd.DataFrame:
    linhas = []
    for idx in indices:
        for t in tipos:
            col = coluna_do_indice(idx, t)
            if col in df.columns:
                tmp = df[["DATE", col]].rename(columns={col: "valor"})
                tmp["indice"] = idx
                tmp["tipo"] = t
                linhas.append(tmp)
    if not linhas:
        return pd.DataFrame(columns=["DATE","indice","tipo","valor"])
    out = pd.concat(linhas, ignore_index=True)
    return out


st.title("Índices de inflação (Ipeadata) — visualização e download")

with st.sidebar:
    st.header("Fonte de dados")
    up = st.file_uploader("Carregar CSV (sep=';')", type=["csv"])
    st.caption("Se não enviar, o app tenta ler `dados.csv` na pasta do projeto.")

df = carregar_csv(up)

# Inferência de índices/tipos a partir das colunas
indices, tipos = inferir_indices_e_tipos(df.columns.tolist())
if not indices:
    st.error("Não consegui inferir os índices a partir dos nomes das colunas. Verifique o padrão: 'IPCA Variacao (%)', 'IPCA Fator', etc.")
    st.stop()

# Controles
colA, colB, colC, colD = st.columns([2, 2, 2, 2])

with colA:
    indice_sel = st.selectbox("Índice", indices, index=0)

with colB:
    tipo_sel = st.selectbox("Série", tipos, index=0)

with colC:
    data_min = df["DATE"].min()
    data_max = df["DATE"].max()
    intervalo = st.date_input(
        "Período",
        value=(data_min.date(), data_max.date()),
        min_value=data_min.date(),
        max_value=data_max.date(),
    )

with colD:
    modo = st.radio("Visualização", ["Linha (tempo)", "Tabela"], horizontal=True)

inicio, fim = pd.to_datetime(intervalo[0]), pd.to_datetime(intervalo[1])
df_f = df[(df["DATE"] >= inicio) & (df["DATE"] <= fim)].copy()

col_escolhida = coluna_do_indice(indice_sel, tipo_sel)
if col_escolhida not in df.columns:
    st.warning(f"Coluna não encontrada: {col_escolhida}")
    st.stop()

serie = df_f[["DATE", col_escolhida]].rename(columns={col_escolhida: "valor"})

# Métricas rápidas
m1, m2, m3, m4 = st.columns(4)
m1.metric("Observações", f"{serie['valor'].notna().sum():,}".replace(",", "."))
m2.metric("Primeira data", serie["DATE"].min().date().isoformat())
m3.metric("Última data", serie["DATE"].max().date().isoformat())

# Último valor (com fallback)
ultimo_val = serie.dropna().iloc[-1]["valor"] if serie["valor"].notna().any() else np.nan
m4.metric("Último valor", f"{ultimo_val:,.6f}".replace(",", "X").replace(".", ",").replace("X", "."))

# Gráfico / Tabela
if modo == "Linha (tempo)":
    fig = px.line(serie, x="DATE", y="valor", title=f"{indice_sel} — {tipo_sel}")
    fig.update_layout(hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.dataframe(serie, use_container_width=True)

st.divider()
st.subheader("Downloads")

c1, c2 = st.columns(2)

with c1:
    csv_filtrado = serie.to_csv(index=False, sep=";", decimal=",")
    st.download_button(
        label="Baixar CSV filtrado (só a série selecionada)",
        data=csv_filtrado,
        file_name=f"{indice_sel}_{tipo_sel.replace(' ', '_')}_{inicio.date()}_{fim.date()}.csv",
        mime="text/csv",
    )

with c2:
    df_long = para_formato_longo(df_f, indices, tipos)
    csv_long = df_long.to_csv(index=False, sep=";", decimal=",")
    st.download_button(
        label="Baixar CSV em formato longo (DATE, indice, tipo, valor)",
        data=csv_long,
        file_name=f"indices_formato_longo_{inicio.date()}_{fim.date()}.csv",
        mime="text/csv",
    )

with st.expander("Ver tabela completa (período filtrado)"):
    st.dataframe(df_f, use_container_width=True)
