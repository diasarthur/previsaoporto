import os
from datetime import datetime
import pandas as pd
import requests


def obter_nivel_rio_blumenau():
    url = "https://alertablu.cobmais.com.br/api/v1/monitoramento"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        dados = response.json()
        nivel_m = dados.get("rio", {}).get("nivel")
        tendencia = dados.get("rio", {}).get("tendencia", "Não informada")
        return {
            "nivel_rio_m": float(nivel_m) if nivel_m else None,
            "tendencia_rio": tendencia,
        }
    except Exception as e:
        print(f"Erro AlertaBLU: {e}")
        return {"nivel_rio_m": None, "tendencia_rio": "Erro"}


def obter_dados_wrf_epagri(municipio, variaveis):
    coords = {
        "blumenau": {"lat": -26.9194, "lon": -49.0661},
        "itajai": {"lat": -26.9078, "lon": -48.6619},
    }
    sub = coords.get(municipio.lower(), {})
    url = f"https://ciram.epagri.sc.gov.br/api/v1/previsao/wrf?lat={sub.get('lat')}&lon={sub.get('lon')}"
    try:
        response = requests.get(url, timeout=15)
        dados = response.json()
        previsoes = dados.get("previsoes", [])
        res = {}
        for item in previsoes:
            if "chuva" in variaveis:
                res["precipitacao_wrf_mm"] = item.get("precipitacao")
            if "vento" in variaveis:
                res["vento_velocidade_kmh"] = item.get("vento_velocidade")
                res["vento_direcao_graus"] = item.get("vento_direcao")
            if "temperatura" in variaveis:
                res["temperatura_c"] = item.get("temperatura")
        return res
    except Exception as e:
        print(f"Erro WRF {municipio}: {e}")
        return {}


def consolidar():
    data_consulta = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    dados_rio = obter_nivel_rio_blumenau()
    wrf_blu = obter_dados_wrf_epagri("blumenau", ["chuva"])
    wrf_itj = obter_dados_wrf_epagri("itajai", ["vento", "temperatura"])

    relatorio = {
        "data_hora_coleta": data_consulta,
        "blumenau_nivel_rio_m": dados_rio["nivel_rio_m"],
        "blumenau_tendencia_rio": dados_rio["tendencia_rio"],
        "blumenau_wrf_precip_mm": wrf_blu.get("precipitacao_wrf_mm"),
        "itajai_wrf_vento_kmh": wrf_itj.get("vento_velocidade_kmh"),
        "itajai_wrf_vento_dir": wrf_itj.get("vento_direcao_graus"),
        "itajai_wrf_temp_c": wrf_itj.get("temperatura_c"),
    }
    return pd.DataFrame([relatorio])


if __name__ == "__main__":
    df = consolidar()
    nome_arquivo = "relatorio_hidrometeo.xlsx"

    # Se o arquivo já existir no repositório, adiciona uma nova linha mantendo o histórico
    if os.path.exists(nome_arquivo):
        df_existente = pd.read_excel(nome_arquivo)
        df = pd.concat([df_existente, df], ignore_index=True)

    # Força a gravação do arquivo Excel
    df.to_excel(nome_arquivo, index=False)
    print(f"Planilha '{nome_arquivo}' gerada e gravada com sucesso!")
