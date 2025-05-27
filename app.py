import streamlit as st
import pandas as pd
import requests
import time
from io import BytesIO
from datetime import datetime

st.set_page_config(page_title="Estimativa Azure", layout="centered")

st.title("📊 Estimativa de Custos Azure via MeterId")
st.write("Faça o upload da planilha com os MeterIds e quantidades para obter uma estimativa de custo usando a Azure Retail API.")

uploaded_file = st.file_uploader("📁 Envie um arquivo .xlsx com colunas 'MeterId' e 'Quantity'", type="xlsx")

# Função de busca na Azure API
@st.cache_data(show_spinner=False)
def buscar_detalhes_por_meter_id(meter_id, regioes):
    for regiao in regioes:
        url = f"https://prices.azure.com/api/retail/prices?$filter=meterId eq '{meter_id}' and armRegionName eq '{regiao}'"
        try:
            response = requests.get(url)
            if response.status_code == 200:
                items = response.json().get("Items", [])
                if items:
                    item = items[0]
                    return {
                        "unitPrice": float(item.get("unitPrice", 0.0)),
                        "skuName": item.get("skuName", ""),
                        "serviceName": item.get("serviceName", ""),
                        "armRegionName": item.get("armRegionName", "")
                    }
        except:
            pass
    return None

if uploaded_file:
    df = pd.read_excel(uploaded_file)

    if "MeterId" not in df.columns or "Quantity" not in df.columns:
        st.error("❌ A planilha deve conter as colunas 'MeterId' e 'Quantity'.")
        st.stop()

    regioes_preferidas = ["brazilsouth", "eastus2", "Global", "Intercontinental", "Zone 1", "Zone 3"]

    # Colunas para preencher
    precos_unitarios = []
    precos_finais = []
    sku_names = []
    service_names = []
    azure_regions = []

    total = len(df)

    progresso = st.progress(0, text="Iniciando...")

    for i, row in df.iterrows():
        meter_id = str(row["MeterId"]).strip()
        quantidade = float(row["Quantity"])

        dados = buscar_detalhes_por_meter_id(meter_id, regioes_preferidas)

        if dados:
            preco_unitario = dados["unitPrice"]
            sku_name = dados["skuName"]

            # Ajuste para SKU baseado em 100 TB
            if "100 TB" in sku_name:
                preco_unitario /= 102400

            preco_final = preco_unitario * quantidade

            precos_unitarios.append(round(preco_unitario, 6))
            precos_finais.append(round(preco_final, 4))
            sku_names.append(sku_name)
            service_names.append(dados["serviceName"])
            azure_regions.append(dados["armRegionName"])
        else:
            precos_unitarios.append(None)
            precos_finais.append(None)
            sku_names.append(None)
            service_names.append(None)
            azure_regions.append(None)

        progresso.progress((i + 1) / total, text=f"Processando linha {i+1} de {total} ({int((i+1)/total*100)}%)")
        time.sleep(0.1)  # Pequeno delay para evitar throttling

    df["Custo_Unitario_USD"] = precos_unitarios
    df["Preco_Final_USD"] = precos_finais
    df["SKU_Name"] = sku_names
    df["Service_Name"] = service_names
    df["Azure_Region"] = azure_regions

    # Gera arquivo de saída
    buffer = BytesIO()
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    nome_arquivo = f"Estimativa_Azure_{timestamp}.xlsx"
    df.to_excel(buffer, index=False, engine="openpyxl")
    buffer.seek(0)

    st.success("✅ Processamento concluído!")
    st.download_button(
        label="📥 Baixar planilha com estimativas",
        data=buffer,
        file_name=nome_arquivo,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
