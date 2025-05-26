import pandas as pd
import requests
import time

# Arquivos
arquivo_entrada = "sua_planilha.xlsx"
arquivo_saida = "planilha_com_detalhes_meterid.xlsx"

# Carrega a planilha
df = pd.read_excel(arquivo_entrada)

# Inicializa colunas para resultados
precos_unitarios = []
precos_finais = []
sku_names = []
service_names = []
azure_regions = []

# Cache interno
cache_precos = {}

# Função para buscar dados do MeterId na API da Azure, priorizando regiões específicas
def buscar_detalhes_por_meter_id(meter_id):
    if meter_id in cache_precos:
        return cache_precos[meter_id]

    regioes = [
        "brazilsouth",
        "eastus2",
        "Global",
        "Intercontinental",
        "Zone 1",
        "Zone 3"
    ]

    for regiao in regioes:
        url = f"https://prices.azure.com/api/retail/prices?$filter=meterId eq '{meter_id}' and armRegionName eq '{regiao}'"
        try:
            response = requests.get(url)
            if response.status_code == 200:
                items = response.json().get("Items", [])
                if items:
                    item = items[0]
                    resultado = {
                        "unitPrice": float(item.get("unitPrice", 0.0)),
                        "skuName": item.get("skuName", ""),
                        "serviceName": item.get("serviceName", ""),
                        "armRegionName": item.get("armRegionName", "")
                    }
                    cache_precos[meter_id] = resultado
                    return resultado
        except Exception as e:
            print(f"Erro ao buscar dados para meterId '{meter_id}' na região '{regiao}': {e}")

    # Se nenhuma região retornar dados
    cache_precos[meter_id] = None
    return None

# Loop principal
for i, row in df.iterrows():
    meter_id = str(row.get("MeterId", "")).strip()
    quantidade = row.get("Quantity", 0)

    dados = buscar_detalhes_por_meter_id(meter_id)

    if dados:
        preco_unitario = dados["unitPrice"]
        sku_name = dados["skuName"]

        # Ajuste: se SKU contém "100 TB", dividir o preço por 102400
        if "100 TB" in sku_name:
            preco_unitario = preco_unitario / 102400

        preco_total = preco_unitario * quantidade

        precos_unitarios.append(round(preco_unitario, 6))
        precos_finais.append(round(preco_total, 4))
        sku_names.append(sku_name)
        service_names.append(dados["serviceName"])
        azure_regions.append(dados["armRegionName"])
    else:
        precos_unitarios.append(None)
        precos_finais.append(None)
        sku_names.append(None)
        service_names.append(None)
        azure_regions.append(None)

    print(f"[{i+1}/{len(df)}] MeterId: {meter_id} → Custo: {preco_total if dados else 'N/A'}")
    time.sleep(0.3)

# Adiciona colunas na planilha
df["Custo_Unitario_USD"] = precos_unitarios
df["Preco_Final_USD"] = precos_finais
df["SKU_Name"] = sku_names
df["Service_Name"] = service_names
df["Azure_Region"] = azure_regions

# Salva o resultado
df.to_excel(arquivo_saida, index=False)
print(f"\n✅ Planilha salva como '{arquivo_saida}' com os dados da Azure Retail API.")
