from datetime import datetime
import pandas as pd
import requests


def obter_nivel_rio_blumenau():
    """Coleta o nível do Rio Itajaí-Açu via AlertaBLU / Defesa Civil de Blumenau."""
    url = "https://alertablu.cobmais.com.br/api/v1/monitoramento"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        dados = response.json()

        # Leitura da cota do rio (Ponte Adolfo Konder / Estação Central)
        nivel_m = dados.get("rio", {}).get("nivel")
        tendencia = dados.get("rio", {}).get("tendencia", "Não informada")

        return {
            "fonte": "AlertaBLU",
            "nivel_rio_m": float(nivel_m) if nivel_m else None,
            "tendencia_rio": tendencia,
        }
    except Exception as e:
        print(f"[ERRO] Falha ao coletar nível do rio (AlertaBLU): {e}")
        return {"nivel_rio_m": None, "tendencia_rio": "Erro"}


def obter_dados_wrf_epagri(municipio, variaveis):
    """Mapeia e coleta os dados do modelo WRF disponibilizados pela Epagri/Ciram

    para o município desejado.
    """
    # Mapeamento de coordenadas aproximadas para requisição em ponto fixo
    coords = {
        "blumenau": {"lat": -26.9194, "lon": -49.0661},
        "itajai": {"lat": -26.9078, "lon": -48.6619},
    }

    sub_coords = coords.get(municipio.lower())
    if not sub_coords:
        raise ValueError("Município não cadastrado nas coordenadas.")

    # Endpoint do modelo WRF Epagri (ou API Open-Meteo WRF caso utilize a grade pública)
    url = f"https://ciram.epagri.sc.gov.br/api/v1/previsao/wrf?lat={sub_coords['lat']}&lon={sub_coords['lon']}"

    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        dados = response.json()

        # Organizando a série temporal do modelo (previsão horária)
        previsoes = dados.get("previsoes", [])
        registro_filtrado = {}

        for item in previsoes:
            # Extrai apenas as variáveis solicitadas
            if "chuva" in variaveis:
                registro_filtrado["precipitacao_wrf_mm"] = item.get(
                    "precipitacao"
                )
            if "vento" in variaveis:
                registro_filtrado["vento_velocidade_kmh"] = item.get(
                    "vento_velocidade"
                )
                registro_filtrado["vento_direcao_graus"] = item.get(
                    "vento_direcao"
                )
            if "temperatura" in variaveis:
                registro_filtrado["temperatura_c"] = item.get("temperatura")

        return registro_filtrado
    except Exception as e:
        print(f"[ERRO] Falha ao coletar dados WRF para {municipio}: {e}")
        return {}


def consolidar_relatorio():
    data_consulta = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 1. Coleta do Rio em Blumenau
    dados_rio = obter_nivel_rio_blumenau()

    # 2. Coleta WRF Chuva Blumenau
    wrf_blumenau = obter_dados_wrf_epagri(
        municipio="blumenau", variaveis=["chuva"]
    )

    # 3. Coleta WRF Vento e Temp Itajaí
    wrf_itajai = obter_dados_wrf_epagri(
        municipio="itajai", variaveis=["vento", "temperatura"]
    )

    # Consolidação dos Dados
    relatorio = {
        "data_hora_coleta": data_consulta,
        "blumenau_nivel_rio_m": dados_rio["nivel_rio_m"],
        "blumenau_tendencia_rio": dados_rio["tendencia_rio"],
        "blumenau_wrf_precip_mm": wrf_blumenau.get("precipitacao_wrf_mm"),
        "itajai_wrf_vento_kmh": wrf_itajai.get("vento_velocidade_kmh"),
        "itajai_wrf_vento_dir": wrf_itajai.get("vento_direcao_graus"),
        "itajai_wrf_temp_c": wrf_itajai.get("temperatura_c"),
    }

    df = pd.DataFrame([relatorio])
    return df


# Executa o consolidador
df_relatorio = consolidar_relatorio()
print(df_relatorio.to_string())
