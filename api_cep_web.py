import streamlit as st
import requests
import pandas as pd
import urllib3
from io import BytesIO

# Desativa avisos de SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def buscar_dados_cep(cep):
    """Consulta a API do ViaCEP para um único CEP."""
    cep_limpo = ''.join(filter(str.isdigit, str(cep))).zfill(8)

    if len(cep_limpo) != 8:
        return {"CEP_Original": cep, "Status": "CEP Inválido"}

    url = f"https://viacep.com.br/ws/{cep_limpo}/json/"

    try:
        response = requests.get(url, verify=False, timeout=10)
        response.raise_for_status()
        dados = response.json()

        if "erro" in dados:
            return {"CEP": cep_limpo, "Status": "CEP Não Encontrado"}

        return {
            "CEP": dados.get("cep", ""),
            "Logradouro": dados.get("logradouro", ""),
            "Complemento": dados.get("complemento", ""),
            "Bairro": dados.get("bairro", ""),
            "Cidade": dados.get("localidade", ""),
            "UF": dados.get("uf", ""),
            "Estado": dados.get("estado", ""),
            "Região": dados.get("regiao", ""),
            "DDD": dados.get("ddd", ""),
            "Status": "Sucesso"
        }

    except requests.exceptions.RequestException as e:
        return {"CEP": cep_limpo, "Status": f"Erro de Conexão: {e}"}

# --- INTERFACE WEB (Streamlit) ---
st.set_page_config(page_title="📍 Consulta de CEP's", layout="centered")

st.title("📍 Consulta de CEPs")
st.write("Carrega uma planilha Excel (`.xlsx` ou `.xls`) e retorna o endereço completo.")

# Chave dinâmica para resetar o uploader via session_state
if "uploader_key" not in st.session_state:
    st.session_state["uploader_key"] = 0

def limpar_pesquisa():
    st.session_state["uploader_key"] += 1
    st.rerun()

# 1. Botão para Selecionar/Upload do Arquivo
arquivo_enviado = st.file_uploader(
    "📤 Localizar planilha de CEPs", 
    type=["xlsx", "xls"],
    key=f"file_uploader_{st.session_state['uploader_key']}",
    help="O arquivo precisa ter uma coluna com o cabeçalho exatamente com o nome 'CEP'."
)

arquivo_valido = False
df_entrada = None

# Validação do arquivo exibida logo abaixo do uploader (acima dos botões)
if arquivo_enviado is not None:
    try:
        df_entrada = pd.read_excel(arquivo_enviado, dtype={"CEP": str})

        if "CEP" not in df_entrada.columns:
            st.error("Erro: A planilha informada não contém a coluna 'CEP'. Verifique o arquivo.")
        else:
            st.success("📁 Arquivo carregado com sucesso!")
            arquivo_valido = True
    except Exception as e:
        st.error(f"Erro ao processar o arquivo: {e}")

# Botões de Ação (ficam posicionados abaixo da mensagem de status do arquivo)
col1, col2 = st.columns([1, 1])

with col1:
    executar = st.button("🚀 Executar Consulta", disabled=not arquivo_valido, use_container_width=True)
with col2:
    st.button("🗑️ Limpar / Nova Pesquisa", on_click=limpar_pesquisa, use_container_width=True)

# 2. Executa a Consulta ao clicar no botão habilitado
if arquivo_valido and executar:
    try:
        ceps = df_entrada["CEP"].dropna().tolist()
        total_ceps = len(ceps)

        resultados = []
        
        # Barra de progresso e texto indicativo
        barra_progresso = st.progress(0)
        status_texto = st.empty()

        for index, cep in enumerate(ceps, start=1):
            status_texto.text(f"Consultando CEP {index} de {total_ceps}: {cep}")
            
            dados_endereco = buscar_dados_cep(cep)
            resultados.append(dados_endereco)
            
            # Atualiza a barra de progresso
            barra_progresso.progress(index / total_ceps)

        status_texto.success("✅ Consulta concluída com sucesso!")

        # Converte o resultado para DataFrame
        df_resultados = pd.DataFrame(resultados)

        st.subheader("Resultado das Consultas:")
        st.dataframe(df_resultados, use_container_width=True)

        # Prepara o arquivo Excel para download direto pelo navegador
        buffer_excel = BytesIO()
        with pd.ExcelWriter(buffer_excel, engine='openpyxl') as writer:
            df_resultados.to_excel(writer, index=False)
        buffer_excel.seek(0)

        # Botão para baixar a planilha processada
        st.download_button(
            label="📥 Baixar Planilha Resultado (.xlsx)",
            data=buffer_excel,
            file_name="resultado_ceps.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    except Exception as e:
        st.error(f"Erro ao processar a consulta: {e}")