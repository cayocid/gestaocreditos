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
    cursor.execute('''CREATE TABLE IF NOT EXISTS pagamentos (
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
st.set_page_config(page_title="Gestão de Energia", layout="wide")
st.sidebar.title("Menu")
menu = st.sidebar.radio("Navegação", ["Dashboard", "CRM", "Faturamento", "Gestão de UC’s e UG’s", "Configurações"])

if menu == "Dashboard":
    st.title("📊 Dashboard de Gestão")
    conn = sqlite3.connect("usina.db", check_same_thread=False)
    df_vendas = pd.read_sql_query("SELECT * FROM vendas", conn)
    df_pagamentos = pd.read_sql_query("SELECT * FROM pagamentos", conn)
    conn.close()
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Vendas Fechadas")
        st.metric(label="Total de Vendas", value=len(df_vendas))
    with col2:
        st.subheader("Pagamentos Recebidos")
        st.metric(label="Total Faturado", value=df_pagamentos["valor"].sum())

if menu == "CRM":
    st.title("📋 Gestão de Clientes e Leads")
    st.subheader("Cadastro de Novos Clientes")
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
    df_pagamentos = pd.read_sql_query("SELECT * FROM pagamentos", conn)
    conn.close()
    st.dataframe(df_pagamentos)

if menu == "Gestão de UC’s e UG’s":
    st.title("🔧 Gestão de Unidades Consumidoras e Geradoras")
    conn = sqlite3.connect("usina.db", check_same_thread=False)
    df_usinas = pd.read_sql_query("SELECT * FROM usina", conn)
    conn.close()
    st.dataframe(df_usinas)

if menu == "Configurações":
    st.title("⚙️ Configurações Gerais")
    st.write("Configurações do sistema e ajustes avançados")

if st.sidebar.button("Atualizar Dados"):
    st.experimental_rerun()
