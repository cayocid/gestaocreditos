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

st.title("Gerenciamento de Usinas Fotovoltaicas")

# Seção de Cadastro de Usina
st.subheader("Cadastrar Nova Usina")
nome_usina = st.text_input("Nome da Usina")
localizacao_usina = st.text_input("Localização")
capacidade_usina = st.number_input("Capacidade (kW)", min_value=1.0, format="%.2f")
if st.button("Cadastrar Usina"):
    conn = sqlite3.connect("usina.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO usina (nome, localizacao, capacidade) VALUES (?, ?, ?)",
                   (nome_usina, localizacao_usina, capacidade_usina))
    conn.commit()
    conn.close()
    st.success("Usina cadastrada com sucesso!")

# Seção de Cadastro de Clientes
st.subheader("Cadastrar Cliente")
nome_cliente = st.text_input("Nome do Cliente")
cpf_cnpj = st.text_input("CPF/CNPJ")
contato = st.text_input("Contato")
endereco = st.text_input("Endereço")
usina_id = st.selectbox("Selecione a Usina", pd.read_sql_query("SELECT id, nome FROM usina", sqlite3.connect("usina.db", check_same_thread=False)))
if st.button("Cadastrar Cliente"):
    conn = sqlite3.connect("usina.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO clientes (nome, cpf_cnpj, contato, endereco, usina_id) VALUES (?, ?, ?, ?, ?)",
                   (nome_cliente, cpf_cnpj, contato, endereco, usina_id))
    conn.commit()
    conn.close()
    st.success("Cliente cadastrado com sucesso!")

# Visualizar progresso das vendas por usina
st.subheader("Progresso das Vendas por Usina")
conn = sqlite3.connect("usina.db", check_same_thread=False)
df_usinas = pd.read_sql_query("SELECT * FROM usina", conn)
df_vendas = pd.read_sql_query("SELECT usina_id, SUM(potencia_alocada) as potencia_vendida FROM vendas WHERE status = 'CONTRATO ASSINADO' GROUP BY usina_id", conn)
conn.close()

df_usinas = df_usinas.merge(df_vendas, left_on="id", right_on="usina_id", how="left").fillna(0)
df_usinas["potencia_disponivel"] = df_usinas["capacidade"] - df_usinas["potencia_vendida"]

fig = px.bar(df_usinas, x="nome", y=["potencia_vendida", "potencia_disponivel"], title="Progresso das Vendas por Usina")
st.plotly_chart(fig)

# Exibir lista de contratos
st.subheader("Contratos Assinados")
conn = sqlite3.connect("usina.db", check_same_thread=False)
df_contratos = pd.read_sql_query("SELECT clientes.nome, contratos.contrato_url, contratos.status FROM contratos JOIN clientes ON contratos.cliente_id = clientes.id", conn)
conn.close()
st.dataframe(df_contratos)

if st.button("Atualizar Dados"):
    st.experimental_rerun()
