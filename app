from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import sqlite3
import pandas as pd
import stripe
import mercadopago
import requests
from datetime import datetime
from docusign_esign import ApiClient, EnvelopesApi, EnvelopeDefinition, Signer, Document, Tabs, SignHere
import plotly.express as px

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# Configuração das APIs
stripe.api_key = "SUA_CHAVE_STRIPE"
mp = mercadopago.SDK("SUA_CHAVE_MERCADO_PAGO")
DOCUSIGN_BASE_URL = "https://demo.docusign.net/restapi"
DOCUSIGN_ACCESS_TOKEN = "SEU_TOKEN_DOCUSIGN"
DOCUSIGN_ACCOUNT_ID = "SEU_ACCOUNT_ID"

def init_db():
    conn = sqlite3.connect("usina.db")
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

@app.route('/cadastrar_cliente', methods=['POST'])
def cadastrar_cliente():
    nome = request.form['nome']
    cpf_cnpj = request.form['cpf_cnpj']
    contato = request.form['contato']
    endereco = request.form['endereco']
    usina_id = int(request.form['usina_id'])
    
    conn = sqlite3.connect("usina.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO clientes (nome, cpf_cnpj, contato, endereco, usina_id) VALUES (?, ?, ?, ?, ?)",
                   (nome, cpf_cnpj, contato, endereco, usina_id))
    conn.commit()
    conn.close()
    
    return "Cliente cadastrado com sucesso!"

@app.route('/gerar_contrato', methods=['POST'])
def gerar_contrato():
    cliente_id = request.form['cliente_id']
    usina_id = request.form['usina_id']
    cliente_email = request.form['cliente_email']
    contrato_pdf = "contrato.pdf"
    
    api_client = ApiClient()
    api_client.host = DOCUSIGN_BASE_URL
    api_client.set_default_header("Authorization", f"Bearer {DOCUSIGN_ACCESS_TOKEN}")
    
    envelope_api = EnvelopesApi(api_client)
    
    envelope_definition = EnvelopeDefinition(
        email_subject="Assine seu contrato",
        documents=[Document(
            document_base64=open(contrato_pdf, "rb").read().encode("base64"),
            name="Contrato Solar",
            file_extension="pdf",
            document_id="1"
        )],
        recipients={
            "signers": [Signer(
                email=cliente_email,
                name="Cliente",
                recipient_id="1",
                tabs=Tabs(sign_here_tabs=[SignHere(document_id="1", page_number="1", x_position="100", y_position="150")])
            )]
        },
        status="sent"
    )
    
    envelope = envelope_api.create_envelope(DOCUSIGN_ACCOUNT_ID, envelope_definition=envelope_definition)
    contrato_url = f"https://demo.docusign.net/Signing/?envelopeId={envelope.envelope_id}"
    
    conn = sqlite3.connect("usina.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO contratos (cliente_id, usina_id, contrato_url) VALUES (?, ?, ?)", (cliente_id, usina_id, contrato_url))
    conn.commit()
    conn.close()
    
    return jsonify({"contrato_url": contrato_url})

@app.route('/dashboard', methods=['GET'])
def dashboard():
    conn = sqlite3.connect("usina.db")
    df_usinas = pd.read_sql_query("SELECT * FROM usina", conn)
    df_vendas = pd.read_sql_query("SELECT usina_id, SUM(potencia_alocada) as potencia_vendida FROM vendas WHERE status = 'CONTRATO ASSINADO' GROUP BY usina_id", conn)
    conn.close()
    
    df_usinas = df_usinas.merge(df_vendas, on="usina_id", how="left").fillna(0)
    df_usinas["potencia_disponivel"] = df_usinas["capacidade"] - df_usinas["potencia_vendida"]
    
    fig = px.bar(df_usinas, x="nome", y=["potencia_vendida", "potencia_disponivel"], title="Progresso das Vendas por Usina")
    fig.write_html("templates/dashboard.html")
    return render_template("dashboard.html")

if __name__ == '__main__':
    app.run(debug=True)
