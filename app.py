import streamlit as st
import cv2
import numpy as np
import pandas as pd
from pillow_heif import register_heif_opener
import io
import os
from PIL import Image
from fpdf import FPDF
import plotly.graph_objects as go

# Registra o suporte a arquivos HEIC/HEIF do iPhone
register_heif_opener()

st.set_page_config(page_title="Gota Inteligente - IAC & Aplique Bem", page_icon="💧", layout="wide")

# ==============================================================================
# 🖼️ CONFIGURAÇÃO DOS LOGOTIPOS LOCAIS
# ==============================================================================
CAMINHO_LOGO_IAC = "logo_iac.png.png" 
CAMINHO_LOGO_APLIQUEBEM = "logo_aplique.png.jpg"

def carregar_logo(caminho_imagem):
    if os.path.exists(caminho_imagem):
        try:
            return Image.open(caminho_imagem)
        except:
            return None
    return None

img_iac = carregar_logo(CAMINHO_LOGO_IAC)
img_aplique = carregar_logo(CAMINHO_LOGO_APLIQUEBEM)

# ==============================================================================
# 🔐 ACESSO RESTRITO (USUÁRIOS HOMOLOGADOS)
# ==============================================================================
USUARIOS_AUTORIZADOS = {
    "andre": "iaciac",
    "manoel": "iaciac",
    "hamilton": "iaciac",
    "iac": "apliquebem2026"
}

if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    _, col_central, _ = st.columns([1, 2, 1])
    with col_central:
        l1, l2 = st.columns(2)
        if img_iac: l1.image(img_iac, width=200)
        if img_aplique: l2.image(img_aplique, width=220)
        st.markdown("<h2 style='text-align: center; color: #005088;'>🔒 Gota Inteligente - Acesso Restrito</h2>", unsafe_allow_html=True)
        usuario_input = st.text_input("Usuário de Acesso:", key="user_login")
        senha_input = st.text_input("Senha de Segurança:", type="password", key="password_login")
        if st.button("🔑 Verificar Autorização", use_container_width=True):
            if usuario_input in USUARIOS_AUTORIZADOS and USUARIOS_AUTORIZADOS[usuario_input] == senha_input:
                st.session_state["autenticado"] = True
                st.rerun()
            else: st.error("❌ Credenciais incorretas.")
    st.stop()

# ==============================================================================
# 💧 APP PRINCIPAL
# ==============================================================================
if img_iac: st.sidebar.image(img_iac, width=100)
if img_aplique: st.sidebar.image(img_aplique, width=120)
st.sidebar.markdown("---")
if st.sidebar.button("🚪 Sair"):
    st.session_state["autenticado"] = False
    st.rerun()

st.title("💧 Analisador de Gotas Inteligente")
st.markdown("**Parceria Científica:** IAC & Programa Aplique Bem")
st.write("---")

st.sidebar.header("🛠️ Calibração")
fator_espalhamento = st.sidebar.slider("Fator de Espalhamento", 1.0, 3.0, 2.0, 0.1)

aba_upload, aba_graficos, aba_inspecao, aba_relatorio = st.tabs([
    "📥 Captura", "📊 Modelagem 3D e Gráficos", "🔍 Inspeção", "📋 Relatório Infográfico"
])

# Lógica de processamento (Resumida para o exemplo)
with aba_upload:
    arquivo_enviado = st.file_uploader("Selecione o cartão", type=['jpg','jpeg','png','heic','heif'])

if arquivo_enviado:
    # --- SIMULAÇÃO DE PROCESSAMENTO (A mesma do seu código OpenCV) ---
    # Para o exemplo, vamos assumir valores de processamento:
    dmv_simulado = 245.0  
    cobertura_simulada = 28.07
    densidade_simulada = 18.75
    span_simulado = 1.09
    pequenas, medias, grandes = 4.7, 21.3, 74.0
    cv_global = 0.44
    nome_arquivo = arquivo_enviado.name

    # --- ABA DE GRÁFICOS E PROJEÇÃO 3D DUPLA ---
    with aba_graficos:
        st.subheader("🛰️ Comparação Espacial 3D: Voo vs. Impacto")
        st.markdown("Visualize a diferença entre a gota suspensa no ar e o seu rastro de deposição no alvo.")
        
        col_3d_1, col_3d_2 = st.columns(2)
        
        raio = dmv_simulado / 2.0
        u = np.linspace(0, 2 * np.pi, 50)
        
        # 1. GOTA SUSPENSA (ESFERA NO AR)
        with col_3d_1:
            st.markdown("<h4 style='text-align: center; color: #0099ff;'>1. Gota em Voo (Microsfera)</h4>", unsafe_allow_html=True)
            v_sph = np.linspace(0, np.pi, 50)
            xs = raio * np.outer(np.cos(u), np.sin(v_sph))
            ys = raio * np.outer(np.sin(u), np.sin(v_sph))
            zs = raio * np.outer(np.ones(np.size(u)), np.cos(v_sph))
            
            fig_sph = go.Figure(data=[go.Surface(x=xs, y=ys, z=zs, colorscale='Blues', showscale=False)])
            fig_sph.update_layout(scene=dict(xaxis_title="um", yaxis_title="um", zaxis_title="um"), height=400, margin=dict(l=0,r=0,b=0,t=0))
            st.plotly_chart(fig_sph, use_container_width=True)
            st.caption(f"Volume esférico original: {dmv_simulado} µm de diâmetro.")

        # 2. GOTA NO ALVO (IMPACTO ACHATADO)
        with col_3d_2:
            st.markdown("<h4 style='text-align: center; color: #2e7d32;'>2. Gota no Alvo (Footprint)</h4>", unsafe_allow_html=True)
            v_imp = np.linspace(0, np.pi/2, 50)
            xi = (raio * fator_espalhamento) * np.outer(np.cos(u), np.sin(v_imp))
            yi = (raio * fator_espalhamento) * np.outer(np.sin(u), np.sin(v_imp))
            zi = (raio * 0.4) * np.outer(np.ones(np.size(u)), np.cos(v_imp))
            
            fig_imp = go.Figure(data=[go.Surface(x=xi, y=yi, z=zi, colorscale='Greens', showscale=False)])
            fig_imp.update_layout(scene=dict(xaxis_title="um", yaxis_title="um", zaxis_title="um"), height=400, margin=dict(l=0,r=0,b=0,t=0))
            st.plotly_chart(fig_imp, use_container_width=True)
            st.caption(f"Área de contato expandida pelo impacto no alvo.")

    # --- RELATÓRIO PDF (Mantendo o design horizontal e espaçado) ---
    with aba_relatorio:
        def gerar_pdf():
            pdf = FPDF()
            pdf.add_page()
            # Cabeçalho Premium
            pdf.set_fill_color(26, 36, 43)
            pdf.rect(0, 0, 210, 42, 'F')
            pdf.set_font("Arial", "B", 15); pdf.set_text_color(255, 255, 255); pdf.set_y(10)
            pdf.cell(0, 8, "LAUDO DA QUALIDADE DE PULVERIZACAO", ln=True, align="C")
            
            if os.path.exists(CAMINHO_LOGO_IAC): pdf.image(CAMINHO_LOGO_IAC, x=15, y=47, w=22)
            if os.path.exists(CAMINHO_LOGO_APLIQUEBEM): pdf.image(CAMINHO_LOGO_APLIQUEBEM, x=173, y=47, w=22)

            # Cards e Quadrado de Cobertura (Conforme os códigos anteriores)
            pdf.set_y(80); pdf.set_text_color(40, 50, 60); pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 6, "1. Indicadores de Performance Operacional", ln=True)
            # ... (Lógica dos cards e gráficos omitida aqui para brevidade, mas mantida no seu arquivo)
            
            return pdf.output(dest='S').encode('latin1')

        st.download_button("🚀 GERAR LAUDO PREMIUM", gerar_pdf(), "Laudo.pdf", "application/pdf", use_container_width=True)
