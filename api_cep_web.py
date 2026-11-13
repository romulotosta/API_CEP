import streamlit as st
import requests
import pandas as pd
import urllib3
import plotly.express as px
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

# Interface
st.set_page_config(page_title="📍 Consulta de CEPs", layout="centered")

st.title("📍 Consulta de CEPs")
st.write("Carregue sua planilha Excel (`.xlsx` ou `.xls`) para consultar os endereços e visualizar o dashboard.")

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

# Mensagem de status logo abaixo do uploader e acima dos botões
if arquivo_enviado is not None:
    try:
        df_entrada = pd.read_excel(arquivo_enviado, dtype={"CEP": str})

        if "CEP" not in df_entrada.columns:
            st.error("❌ Erro: A planilha informada não contém a coluna 'CEP'. Verifique o arquivo.")
        else:
            st.success("📁 Arquivo carregado com sucesso!")
            arquivo_valido = True
    except Exception as e:
        st.error(f"Erro ao processar o arquivo: {e}")

# Botões de Ação
col_btn1, col_btn2 = st.columns([1, 1])

with col_btn1:
    executar = st.button("🚀 Executar Consulta", disabled=not arquivo_valido, use_container_width=True)
with col_btn2:
    st.button("🔄 Limpar / Nova Pesquisa", on_click=limpar_pesquisa, use_container_width=True)

# 2. Executa a Consulta e Exibe o Dashboard
if arquivo_valido and executar:
    try:
        ceps = df_entrada["CEP"].dropna().tolist()
        total_ceps = len(ceps)

        resultados = []
        
        barra_progresso = st.progress(0)
        status_texto = st.empty()

        for index, cep in enumerate(ceps, start=1):
            status_texto.text(f"Consultando CEP {index} de {total_ceps}: {cep}")
            dados_endereco = buscar_dados_cep(cep)
            resultados.append(dados_endereco)
            barra_progresso.progress(index / total_ceps)

        status_texto.success("✅ Consulta concluída com sucesso!")
        df_resultados = pd.DataFrame(resultados)

        # Resultados
        st.markdown("---")
        st.header("📈 Indicadores")

        df_sucesso = df_resultados[df_resultados["Status"] == "Sucesso"]

        total_sucesso = len(df_sucesso)
        total_falha = total_ceps - total_sucesso
        total_cidades = df_sucesso["Cidade"].nunique() if not df_sucesso.empty else 0

        # Cartões de Métricas
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        col_m1.metric("Total", total_ceps)
        col_m2.metric("Sucesso", total_sucesso)
        col_m3.metric("Erros", total_falha)
        col_m4.metric("Cidades", total_cidades)

        st.markdown("")

        if total_sucesso > 0:
            # Gráfico de Colunas: Quantidade por Cidade
            st.subheader("🏙️ Quantidade por Cidade")
            df_cidade = df_sucesso["Cidade"].value_counts().reset_index()
            df_cidade.columns = ["Cidade", "Quantidade"]
            fig_cidade = px.bar(df_cidade, x="Cidade", y="Quantidade", text_auto=True)
            st.plotly_chart(fig_cidade, use_container_width=True)

            # Gráfico de Barras: Top 10 Bairros
            st.subheader("🏘️ Top 10 Bairros")
            df_bairro = df_sucesso["Bairro"].replace("", "Não Informado").value_counts().head(10).reset_index()
            df_bairro.columns = ["Bairro", "Quantidade"]
            fig_bairro = px.bar(df_bairro, x="Quantidade", y="Bairro", orientation="h", text_auto=True)
            fig_bairro.update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_bairro, use_container_width=True)

            # Gráfico de Rosca: Status das Consultas
            st.subheader("📒 Distribuição de Status")
            df_status = df_resultados["Status"].value_counts().reset_index()
            df_status.columns = ["Status", "Quantidade"]
            fig_status = px.pie(df_status, names="Status", values="Quantidade", hole=0.4)
            st.plotly_chart(fig_status, use_container_width=True)

        st.markdown("---")
        st.subheader("📋 Dados Detalhados por Status")

        # Abas para cada Status encontrado + Aba "Todos"
        status_unicos = df_resultados["Status"].unique().tolist()
        nomes_abas = ["📋 Todos"] + [f"📌 {s}" for s in status_unicos]
        abas = st.tabs(nomes_abas)

        # Conteúdo da Aba "Todos"
        with abas[0]:
            st.write(f"Exibindo todos os **{len(df_resultados)}** registros:")
            st.dataframe(df_resultados, use_container_width=True)

            buffer_excel = BytesIO()
            with pd.ExcelWriter(buffer_excel, engine='openpyxl') as writer:
                df_resultados.to_excel(writer, index=False)
            buffer_excel.seek(0)

            st.download_button(
                label="💾 Baixar Planilha Completa (.xlsx)",
                data=buffer_excel,
                file_name="resultado_ceps_completo.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                key="btn_down_todos"
            )

        # Conteúdo das Abas Individuais por Status
        for i, status in enumerate(status_unicos):
            with abas[i+1]:
                df_status = df_resultados[df_resultados["Status"] == status]
                st.write(f"Exibindo registros com status **{status}** (**{len(df_status)}** itens):")
                st.dataframe(df_status, use_container_width=True)

                buffer_excel = BytesIO()
                with pd.ExcelWriter(buffer_excel, engine='openpyxl') as writer:
                    df_status.to_excel(writer, index=False)
                buffer_excel.seek(0)

                status_key_safe = "".join(c for c in status if c.isalnum())
                st.download_button(
                    label=f"📥 Baixar Filtrado ({status}) (.xlsx)",
                    data=buffer_excel,
                    file_name=f"resultado_ceps_{status_key_safe.lower()}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    key=f"btn_down_{status_key_safe}"
                )

    except Exception as e:
        st.error(f"Erro ao processar a consulta: {e}")