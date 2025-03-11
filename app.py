import streamlit as st
import sqlite3
import pandas as pd
import requests
import stripe
import mercadopago
from docusign_esign import ApiClient, EnvelopesApi, EnvelopeDefinition, Signer, Document, Tabs, SignHere
import plotly.express as px

# Configuração das APIs
stripe.api_key = "SUA_CHAVE_STRIPE"
mp = mercadopago.SDK("SUA_CHAVE_MERCADO_PAGO")
DOCUSIGN_BASE_URL = "https://demo.docusign.net/restapi"
DOCUSIGN_ACCESS_TOKEN = "SEU_TOKEN_DOCUSIGN"
DOCUSIGN_ACCOUNT_ID = "SEU_ACCOUNT_ID"

def init_db():
    conn = sqlite3.connect("usina.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS usina (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nome TEXT,
                        localizacao TEXT,
                        capacidade REAL
                    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS clientes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nome TEXT,
                        cpf_cnpj TEXT,
                        contato TEXT,
                        endereco TEXT,
                        usina_id INTEGER,
                        saldo_creditos REAL DEFAULT 0,
                        FOREIGN KEY(usina_id) REFERENCES usina(id)
                    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS vendas (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        usina_id INTEGER,
                        cliente_id INTEGER,
                        status TEXT DEFAULT 'LEAD',
                        potencia_alocada REAL,
                        FOREIGN KEY(usina_id) REFERENCES usina(id),
                        FOREIGN KEY(cliente_id) REFERENCES clientes(id)
                    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS faturamento (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        cliente_id INTEGER,
                        usina_id INTEGER,
                        mes TEXT,
                        valor REAL,
                        status TEXT DEFAULT 'PENDENTE',
                        metodo TEXT,
                        FOREIGN KEY(cliente_id) REFERENCES clientes(id),
                        FOREIGN KEY(usina_id) REFERENCES usina(id)
                    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS contratos (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        cliente_id INTEGER,
                        usina_id INTEGER,
                        contrato_url TEXT,
                        status TEXT DEFAULT 'PENDENTE',
                        FOREIGN KEY(cliente_id) REFERENCES clientes(id),
                        FOREIGN KEY(usina_id) REFERENCES usina(id)
                    )''')
    conn.commit()
    conn.close()

init_db()

# Interface com menu lateral fixo
st.set_page_config(page_title="Sunne Gestão e Vendas", layout="wide")
st.sidebar.title("Sunne Gestão e Vendas")
menu = st.sidebar.radio("Navegação", ["Dashboard", "Gestão Comercial", "Faturamento", "Rateio de Energia", "Gestão de Contratos", "Configurações"])

if menu == "Dashboard":
    st.title("📊 Dashboard de Gestão")
    conn = sqlite3.connect("usina.db", check_same_thread=False)
    df_vendas = pd.read_sql_query("SELECT * FROM vendas", conn)
    df_faturamento = pd.read_sql_query("SELECT * FROM faturamento", conn)
    conn.close()
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Vendas Concluídas")
        st.metric(label="Total de Vendas", value=len(df_vendas))
    with col2:
        st.subheader("Faturamento Total")
        st.metric(label="Total Recebido", value=df_faturamento["valor"].sum())

if menu == "Gestão Comercial":
    st.title("📋 Gestão Comercial e CRM")
    st.subheader("Cadastro de Clientes e Leads")
    nome = st.text_input("Nome do Cliente")
    cpf_cnpj = st.text_input("CPF/CNPJ")
    contato = st.text_input("Contato")
    endereco = st.text_input("Endereço")
    usina_id = st.selectbox("Selecione a Usina", pd.read_sql_query("SELECT id, nome FROM usina", sqlite3.connect("usina.db", check_same_thread=False)))
    if st.button("Cadastrar Cliente"):
        conn = sqlite3.connect("usina.db", check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO clientes (nome, cpf_cnpj, contato, endereco, usina_id) VALUES (?, ?, ?, ?, ?)",
                       (nome, cpf_cnpj, contato, endereco, usina_id))
        conn.commit()
        conn.close()
        st.success("Cliente cadastrado com sucesso!")

if menu == "Faturamento":
    st.title("💰 Gestão de Faturamento e Cobrança")
    conn = sqlite3.connect("usina.db", check_same_thread=False)
    df_faturamento = pd.read_sql_query("SELECT * FROM faturamento", conn)
    conn.close()
    st.dataframe(df_faturamento)

if menu == "Rateio de Energia":
    st.title("🔧 Rateio de Energia e Auditoria de Créditos")
    st.write("Aqui será implementada a distribuição de créditos de energia conforme a participação dos clientes na usina.")

if menu == "Gestão de Contratos":
    st.title("📄 Gestão de Contratos")
    conn = sqlite3.connect("usina.db", check_same_thread=False)
    df_contratos = pd.read_sql_query("SELECT * FROM contratos", conn)
    conn.close()
    st.dataframe(df_contratos)

if menu == "Configurações":
    st.title("⚙️ Configurações Gerais")
    st.write("Configurações do sistema e ajustes avançados")

if st.sidebar.button("Atualizar Dados"):
    st.experimental_rerun()
