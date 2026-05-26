import streamlit as st
import cv2
import numpy as np
import pandas as pd
from pillow_heif import register_heif_opener
import io
import os
import sqlite3
from datetime import datetime
import requests
from PIL import Image
from fpdf import FPDF
import plotly.graph_objects as go
from streamlit.web.server.websocket_headers import _get_websocket_headers

# Registra o suporte a arquivos HEIC/HEIF do iPhone
register_heif_opener()

st.set_page_config(page_title="Gota Inteligente - IAC & Aplique Bem", page_icon="💧", layout="wide")

# ==============================================================================
# 📱 DETECÇÃO DE DISPOSITIVO (CELULAR VS COMPUTADOR)
# ==============================================================================
def detectar_dispositivo():
    headers = _get_websocket_headers()
    if headers:
        user_agent = headers.get("User-Agent", "").lower()
        if any(term in user_agent for term in ["android", "iphone", "ipad", "mobile", "windows phone"]):
            return "Celular"
    return "Computador"

dispositivo_atual = detectar_dispositivo()

# ==============================================================================
# 🗄️ CONFIGURAÇÃO DO BANCO DE DADOS LOCAL (SQLITE)
# ==============================================================================
DB_NAME = "gotas_inteligentes.db"

def inicializar_banco():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS historico_analises (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_hora TEXT,
            arquivo TEXT,
            tipo_cartao TEXT,
            cobertura REAL,
            num_gotas INTEGER,
            densidade REAL,
            dmv REAL,
            span REAL,
            classe_asabe TEXT
        )
    """)
    conn.commit()
    conn.close()

def salvar_analise_bd(arquivo, tipo, cob, gotas, dens, dmv, span, classe):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    cursor.execute("""
        INSERT INTO historico_analises (data_hora, arquivo, tipo_cartao, cobertura, num_gotas, densidade, dmv, span, classe_asabe)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (agora, arquivo, tipo, cob, gotas, dens, dmv, span, classe))
    conn.commit()
    conn.close()

inicializar_banco()

# ==============================================================================
# 🖼️ CONFIGURAÇÃO DOS LOGOTIPOS LOCAIS
# ==============================================================================
CAMINHO_LOGO_IAC = "logo_iac.png.png" 
CAMINHO_LOGO_APLIQUEBEM = "logo_aplique.png.jpg"

def carregar_logo(caminho_imagem):
    if os.path.exists(caminho_imagem):
        try: return Image.open(caminho_imagem)
        except: return None
    return None

img_iac = carregar_logo(CAMINHO_LOGO_IAC)
img_aplique = carregar_logo(CAMINHO_LOGO_APLIQUEBEM)

# ==============================================================================
# 🔐 ACESSO RESTRITO (USUÁRIOS HOMOLOGADOS)
# ==============================================================================
USUARIOS_AUTORIZADOS = {
    "andre": "iaciac", "manoel": "iaciac", "hamilton": "iaciac", "iac": "apliquebem2026"
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
# 💧 METEOROLOGIA AUTOMÁTICA POR CIDADE
# ==============================================================================
def buscar_clima_cidade(nome_cidade):
    try:
        url_geo = f"https://geocoding-api.open-meteo.com/v1/search?name={nome_cidade}&count=1&language=pt"
        res_geo = requests.get(url_geo).json()
        if not res_geo.get("results"): return None
        
        loc = res_geo["results"][0]
        lat, lon = loc["latitude"], loc["longitude"]
        nome_completo = f"{loc['name']}, {loc.get('admin1', '')}"
        
        url_clima = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,wind_speed_10m"
        res_clima = requests.get(url_clima).json()["current"]
        
        return {
            "local": nome_completo,
            "temp": res_clima["temperature_2m"],
            "uhr": res_clima["relative_humidity_2m"],
            "vento": res_clima["wind_speed_10m"]
        }
    except:
        return None

# Sidebar estrutural
if img_iac: st.sidebar.image(img_iac, width=100)
if img_aplique: st.sidebar.image(img_aplique, width=120)
st.sidebar.markdown("---")

# Informa o modo dinâmico na sidebar
if dispositivo_atual == "Celular":
    st.sidebar.success("📱 Interface Mobile Otimizada")
else:
    st.sidebar.info("💻 Interface Desktop Ativada")

if st.sidebar.button("🚪 Encerrar Sessão", use_container_width=True):
    st.session_state["autenticado"] = False
    st.rerun()

col_tit, col_logos_topo = st.columns([2, 1])
with col_tit:
    st.title("💧 Analisador de Gotas Inteligente")
    st.markdown("**Parceria Científica:** Instituto Agronômico (IAC) & Programa Aplique Bem")
with col_logos_topo:
    ct1, ct2 = st.columns(2)
    if img_iac: ct1.image(img_iac, width=80)
    if img_aplique: ct2.image(img_aplique, width=90)

st.write("---")

st.sidebar.header("🛠️ Parâmetros Operacionais")
fator_espalhamento = st.sidebar.slider("Fator de Espalhamento (Mancha/Real)", 1.0, 3.0, 2.0, 0.1)

st.sidebar.markdown("---")
st.sidebar.header("🌤️ Clima em Tempo Real")
cidade_campo = st.sidebar.text_input("Cidade do Campo / Propriedade:", value="Campinas")
dados_clima = buscar_clima_cidade(cidade_campo)

if dados_clima:
    st.sidebar.caption(f"📍 {dados_clima['local']}")
    st.sidebar.metric("Temperatura", f"{dados_clima['temp']} °C")
    st.sidebar.metric("Umidade Relativa (UR)", f"{dados_clima['uhr']} %")
    st.sidebar.metric("Velocidade do Vento", f"{dados_clima['vento']} km/h")
else:
    st.sidebar.warning("Cidade não localizada. Insira o nome correto.")

aba_upload, aba_graficos, aba_inspecao, aba_relatorio = st.tabs([
    "📥 Captura e Resultados", "📊 Gráficos e Projeções 3D", "🔍 Inspeção de Cartões", "📋 Relatório e Histórico"
])

with aba_upload:
    st.subheader("📸 Captura do Cartão Hidrossensível")
    
    # Adaptação de Interface baseada no Dispositivo
    opcao_padrao = 0 if dispositivo_atual == "Celular" else 1
    metodo_captura = st.radio("Inserção:", ["Usar a Câmera do Celular", "Enviar foto da Galeria"], index=opcao_padrao, horizontal=True)
    
    arquivo_enviado = st.camera_input("Foto") if metodo_captura == "Usar a Câmera do Celular" else st.file_uploader("Arquivo", type=['jpg', 'jpeg', 'png', 'heic', 'heif'])

def classificar_asabe(dmv_val):
    if dmv_val < 100: return "Muito Fina (VF)"
    elif dmv_val <= 175: return "Fina (F)"
    elif dmv_val <= 250: return "Média (M)"
    elif dmv_val <= 375: return "Grossa (C)"
    elif dmv_val <= 450: return "Muito Grossa (VC)"
    else: return "Extremamente Grossa (XC)"

if arquivo_enviado:
    resultados_gerais = []
    dados_graficos = {}
    imagens_processadas = {}
    
    nome_arquivo = getattr(arquivo_enviado, 'name', 'captura_camera.jpg')
    extensao = nome_arquivo.split('.')[-1].lower()
    
    try:
        if extensao in ['heic', 'heif']:
            pil_img = Image.open(arquivo_enviado).convert("RGB")
            img_original = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        else:
            file_bytes = np.asarray(bytearray(arquivo_enviado.read()), dtype=np.uint8)
            img_original = cv2.imdecode(file_bytes, 1)
    except Exception as e:
        st.error(f"Erro no processamento da imagem: {e}"); st.stop()

    if img_original is not None:
        gray = cv2.cvtColor(img_original, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edged = cv2.Canny(blurred, 30, 150)
        contornos_fundo, _ = cv2.findContours(edged.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        img_focada = img_original.copy()
        if len(contornos_fundo) > 0:
            maior_contorno = max(contornos_fundo, key=cv2.contourArea)
            if cv2.contourArea(maior_contorno) > (img_original.shape[0] * img_original.shape[1] * 0.15):
                x, y, w, h = cv2.boundingRect(maior_contorno)
                img_focada = img_original[y:y+h, x:x+w]
        
        # ✂️ ESTRATÉGIA 1: CORTE DE SEGURANÇA DAS BORDAS (BORDER CROP)
        # Corta fora 8% de cada extremidade para ignorar o corte do papel e marcas de dedo
        alt_f, larg_f = img_focada.shape[:2]
        margem_y = int(alt_f * 0.08)
        margem_x = int(larg_f * 0.08)
        
        # Garante que o corte só ocorra se a imagem final mantiver tamanho mínimo estável
        if alt_f > (margem_y * 2) and larg_f > (margem_x * 2):
            img_focada = img_focada[margem_y : alt_f - margem_y, margem_x : larg_f - margem_x]
            
        # Recalcula dimensões da área real útil limpa
        altura_px, largura_px = img_focada.shape[:2]
        area_total_pixels = altura_px * largura_px
        area_cartao_cm2 = (30.0 / 10.0) * (80.0 / 10.0)
        um_por_pixel = (30.0 / largura_px) * 1000.0
        
        hsv = cv2.cvtColor(img_focada, cv2.COLOR_BGR2HSV)
        amostra_hsv = hsv[altura_px//4:3*altura_px//4, largura_px//4:3*largura_px//4]
        tom_medio_h = np.mean(amostra_hsv[:, :, 0])
        tom_medio_s = np.mean(amostra_hsv[:, :, 1])
        
        if 15 <= tom_medio_h <= 45 and tom_medio_s > 60:
            tipo_cartao = "Original (Amarelo)"
            mascara = cv2.bitwise_not(cv2.inRange(hsv, np.array([15, 50, 40]), np.array([45, 255, 255])))
            mascara = cv2.morphologyEx(mascara, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2)))
        else:
            tipo_cartao = "Revelado (Branco)"
            mascara = cv2.inRange(hsv, np.array([85, 40, 40]), np.array([145, 255, 255]))
        
        contornos, _ = cv2.findContours(mascara, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        gotas_filtradas = [c for c in contornos if cv2.contourArea(c) > 3]
        num_gotas = len(gotas_filtradas)
        porcentagem_cobertura = (cv2.countNonZero(mascara) / area_total_pixels) * 100
        densidade_gotas = num_gotas / area_cartao_cm2 if num_gotas > 0 else 0
        
        diametros_reais_um = []
        volumes_reais_um3 = []
        for c in gotas_filtradas:
            area_px = cv2.contourArea(c)
            diametro_mancha_um = (2.0 * np.sqrt(area_px / np.pi)) * um_por_pixel
            diametro_real_um = diametro_mancha_um / fator_espalhamento
            diametros_reais_um.append(diametro_real_um)
            volumes_reais_um3.append((4.0 / 3.0) * np.pi * ((diametro_real_um / 2.0) ** 3))
            
        diametros_reais_um = np.array(diametros_reais_um)
        volumes_reais_um3 = np.array(volumes_reais_um3)
        
        if num_gotas > 0:
            idx = np.argsort(diametros_reais_um)
            diametros_ord = diametros_reais_um[idx]
            frac_acum = np.cumsum(volumes_reais_um3[idx]) / np.sum(volumes_reais_um3)
            dv01 = float(np.interp(0.1, frac_acum, diametros_ord))
            text_dv05 = float(np.interp(0.5, frac_acum, diametros_ord))
            dv09 = float(np.interp(0.9, frac_acum, diametros_ord))
            span = (dv09 - dv01) / text_dv05 if text_dv05 > 0 else 0
            pequenas = np.sum(diametros_reais_um < 150) / num_gotas * 100
            medias = np.sum((diametros_reais_um >= 150) & (diametros_reais_um <= 300)) / num_gotas * 100
            grandes = np.sum(diametros_reais_um > 300) / num_gotas * 100
        else:
            dv01 = text_dv05 = dv09 = span = pequenas = medias = grandes = 0.0
            
        quad_h, quad_w = altura_px // 2, largura_px // 2
        cont_q = [0, 0, 0, 0]
        for c in gotas_filtradas:
            M = cv2.moments(c)
            if M["m00"] != 0:
                cX, cY = int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"])
                if cX < quad_w and cY < quad_h: cont_q[0] += 1
                elif cX >= quad_w and cY < quad_h: cont_q[1] += 1
                elif cX < quad_w and cY >= quad_h: cont_q[2] += 1
                else: cont_q[3] += 1
        cv_espacial = (np.std(cont_q) / np.mean(cont_q) * 100) if np.mean(cont_q) > 0 else 0.0
        
        classe_asabe_final = classificar_asabe(text_dv05)

        salvar_analise_bd(nome_arquivo, tipo_cartao, round(porcentagem_cobertura, 2), num_gotas, round(densidade_gotas, 2), round(text_dv05, 1), round(span, 2), classe_asabe_final)

        resultados_gerais.append({
            "Nome do Arquivo": nome_arquivo, "Tipo Detectado": tipo_cartao, "Cobertura (%)": round(porcentagem_cobertura, 2),
            "Nº de Gotas": num_gotas, "Densidade (gotas/cm²)": round(densidade_gotas, 2), "Dv0.1 (µm)": round(dv01, 1),
            "Dv0.5 / DMV (µm)": round(text_dv05, 1), "Dv0.9 (µm)": round(dv09, 1), "Amplitude (SPAN)": round(span, 2),
            "Gotas Pequenas (<150µm) %": round(pequenas, 1), "Gotas Médias (150-300µm) %": round(medias, 1), "Gotas Grandes (>300µm) %": round(grandes, 1),
            "CV da Distribuição (%)": round(cv_espacial, 2)
        })
        dados_graficos[nome_arquivo] = {"diametros": diametros_reais_um, "classes": [pequenas, medias, grandes], "dmv": text_dv05}
        
        img_vis = img_focada.copy()
        cv2.drawContours(img_vis, gotas_filtradas, -1, (0, 255, 0), 2)
        imagens_processadas[nome_arquivo] = {"original": img_original, "analisada": cv2.cvtColor(img_vis, cv2.COLOR_BGR2RGB), "focada_bgr": img_vis}

    df_geral = pd.DataFrame(resultados_gerais)

    # --- DEFINIÇÃO DOS GRÁFICOS PLOTLY 3D ---
    raio = dados_graficos[nome_arquivo]["dmv"] / 2.0
    u = np.linspace(0, 2 * np.pi, 50)
    
    # 1. Gota em voo
    v_sph = np.linspace(0, np.pi, 50)
    xs, ys, zs = raio * np.outer(np.cos(u), np.sin(v_sph)), raio * np.outer(np.sin(u), np.sin(v_sph)), raio * np.outer(np.ones(np.size(u)), np.cos(v_sph))
    fig_sph = go.Figure(data=[go.Surface(x=xs, y=ys, z=zs, colorscale=[[0, '#a5d6a7'], [0.5, '#0099ff'], [1, '#0033aa']], showscale=False)])
    fig_sph.update_layout(scene=dict(xaxis_title="um", yaxis_title="um", zaxis_title="um", aspectmode='cube'), height=450, margin=dict(l=0,r=0,b=0,t=10))

    # 2. Gota impactada
    v_imp = np.linspace(0, np.pi / 2, 50)
    xi, yi, zi = (raio * fator_espalhamento) * np.outer(np.cos(u), np.sin(v_imp)), (raio * fator_espalhamento) * np.outer(np.sin(u), np.sin(v_imp)), (raio * 0.4) * np.outer(np.ones(np.size(u)), np.cos(v_imp))
    tp = raio * fator_espalhamento * 1.5
    Xp, Yp = np.meshgrid(np.linspace(-tp, tp, 10), np.linspace(-tp, tp, 10))
    fig_imp = go.Figure()
    fig_imp.add_trace(go.Surface(x=Xp, y=Yp, z=np.zeros_like(Xp), colorscale=[[0, '#2e7d32'], [1, '#1b5e20']], showscale=False, opacity=0.6))
    fig_imp.add_trace(go.Surface(x=xi, y=yi, z=zi, colorscale=[[0, '#00e5ff'], [1, '#006064']], showscale=False))
    fig_imp.update_layout(scene=dict(xaxis_title="um", yaxis_title="um", zaxis_title="um", aspectmode='manual', aspectratio=dict(x=1, y=1, z=0.4)), height=450, margin=dict(l=0,r=0,b=0,t=10))

    with aba_upload:
        st.write("---")
        st.markdown("### 📊 Dashboard de Resultados de Campo")
        dados_amostra = df_geral.iloc[0]
        
        c_d1, c_d2, c_d3, c_d4 = st.columns(4)
        c_d1.metric(label="💧 Diâmetro Mediano (DMV)", value=f"{dados_amostra['Dv0.5 / DMV (µm)']} µm")
        c_d2.metric(label="📈 Densidade de Gotas", value=f"{dados_amostra['Densidade (gotas/cm²)']} g/cm²")
        c_d3.metric(label="🎯 Cobertura do Alvo", value=f"{dados_amostra['Cobertura (%)']} %")
        c_d4.metric(label="🔢 Total de Gotas", value=int(dados_amostra['Nº de Gotas']))

        st.info(f"📋 **Classificação Técnica Internacional (ASABE S572):** O espectro da sua calda gerou gotas do tipo **{classe_asabe_final}**.")

        if dados_clima:
            st.write("---")
            st.markdown("### 🌤️ Diagnóstico Dinâmico de Risco Climático Coletado")
            perda_evap = round(pequenas, 1)
            if dados_clima["temp"] > 30.0 or dados_clima["uhr"] < 50.0:
                st.warning(f"⚠️ **Condições Climáticas Desfavoráveis na Localidade:** A temperatura está em {dados_clima['temp']}°C e a UR em {dados_clima['uhr']}%. Com base na leitura do cartão, **{perda_evap}%** do seu volume aplicado (gotas finas) está sob alto risco de sofrer **Evaporação Instantânea**.")
            else:
                st.success(f"✅ **Janela Climatológica Favorável:** Condições locais seguras. Apenas {perda_evap}% do espectro possui vulnerabilidade térmica.")

    with aba_graficos:
        st.subheader("📊 Modelagem Espacial das Gotas")
        if nome_arquivo in dados_graficos:
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                st.markdown("**Frequência de Tamanho das Gotas (Histograma)**")
                counts, bins = np.histogram(dados_graficos[nome_arquivo]["diametros"], bins=15)
                st.bar_chart(pd.DataFrame({"Quantidade": counts}, index=bins[:-1].astype(int)))
            with col_g2:
                st.markdown("**Distribuição de Classes de Gotas (%)**")
                st.bar_chart(pd.DataFrame({"Percentual (%)": dados_graficos[nome_arquivo]["classes"]}, index=['Pequenas', 'Médias', 'Grandes']))
            
            st.write("---")
            st.markdown("### 🛰️ Comparação Espacial Realística 3D (Efeito do Impacto)")
            
            # Ajusta colunas dos gráficos 3D se for celular para não espremer a tela
            col_3d_1, col_3d_2 = st.columns(1) if dispositivo_atual == "Celular" else st.columns(2)
            with col_3d_1:
                st.markdown("<h4 style='text-align: center; color: #0099ff;'>🛰️ 1. Gota em Voo Sustentado (Esfera)</h4>", unsafe_allow_html=True)
                st.plotly_chart(fig_sph, use_container_width=True)
            with col_3d_2:
                st.markdown("<h4 style='text-align: center; color: #2e7d32;'>🎯 2. Deposição Hidrodinâmica no Alvo</h4>", unsafe_allow_html=True)
                st.plotly_chart(fig_imp, use_container_width=True)

    with aba_inspecao:
        st.subheader("🔍 Inspeção e Isolamento do Cartão")
        if nome_arquivo in imagens_processadas:
            col_i1, col_i2 = st.columns(1) if dispositivo_atual == "Celular" else st.columns(2)
            col_i1.image(imagens_processadas[nome_arquivo]["original"], caption="Foto de Entrada (Capturada)", use_container_width=True)
            col_i2.image(imagens_processadas[nome_arquivo]["analisada"], caption="Área Útil com Borda Cortada (Gotas Isoladas)", use_container_width=True)

    with aba_relatorio:
        st.markdown("## 📋 Geração de Laudo Técnico")
        
        dados_cartao = df_geral.iloc[0]
        dmv_atual = dados_cartao["Dv0.5 / DMV (µm)"]
        densidade_atual = dados_cartao["Densidade (gotas/cm²)"]
        deriva_atual = dados_cartao["Gotas Pequenas (<150µm) %"]
        medias_atual = dados_cartao["Gotas Médias (150-300µm) %"]
        grandes_atual = dados_cartao["Gotas Grandes (>300µm) %"]
        span_atual = dados_cartao["Amplitude (SPAN)"]
        cobertura_atual = dados_cartao["Cobertura (%)"]
        
        rec_deriva = "Risco de Deriva Elevado: Ajuste os bicos." if deriva_atual > 30 else "Controle de Deriva Eficiente."
        rec_densidade = "Densidade Insuficiente: Verifique o volume de calda." if densidade_atual < 60 else "Densidade Excelente."

        def gerar_pdf_laudo_grafico():
            pdf = FPDF()
            pdf.add_page()
            pdf.set_margins(15, 15, 15)
            
            # --- HEADER PREMIUM ---
            pdf.set_fill_color(26, 36, 43)
            pdf.rect(0, 0, 210, 42, 'F')
            pdf.set_font("Arial", "B", 14)
            pdf.set_text_color(255, 255, 255)
            pdf.set_y(10)
            pdf.cell(0, 8, "LAUDO DA QUALIDADE DE PULVERIZACAO INTERATIVA", ln=True, align="C")
            pdf.set_font("Arial", "I", 9)
            pdf.cell(0, 5, "Homologacao Tecnica Operacional: IAC & Programa Aplique Bem", ln=True, align="C")
            
            if os.path.exists(CAMINHO_LOGO_IAC): pdf.image(CAMINHO_LOGO_IAC, x=15, y=47, w=22)
            if os.path.exists(CAMINHO_LOGO_APLIQUEBEM): pdf.image(CAMINHO_LOGO_APLIQUEBEM, x=173, y=47, w=22)
            
            # --- SEÇÃO METEOROLOGIA NO LAUDO ---
            pdf.set_y(75)
            pdf.set_text_color(40, 50, 60)
            pdf.set_font("Arial", "B", 11)
            pdf.cell(0, 6, "1. Condicoes Climatologicas da Estacao Local de Analise", ln=True)
            pdf.ln(1)
            pdf.set_fill_color(245, 247, 248)
            pdf.rect(15, pdf.get_y(), 180, 16, 'F')
            pdf.set_font("Arial", "", 9.5)
            
            if dados_clima:
                texto_clima = f"Localidade informada: {dados_clima['local']}   |   Temperatura: {dados_clima['temp']} C\nUmidade Relativa (UR): {dados_clima['uhr']}%   |   Velocidade do Vento: {dados_clima['vento']} km/h"
            else:
                texto_clima = f"Localidade informada: {cidade_campo} (Dados de satelite nao carregados no momento)."
            pdf.multi_cell(180, 5, texto_clima, border=1)
            
            # --- CARDS DE METRICAS ---
            pdf.ln(4)
            pdf.set_font("Arial", "B", 11)
            pdf.cell(0, 6, "2. Indicadores de Performance Operacional", ln=True)
            pdf.ln(2)
            
            indicadores = [
                {"label": "DMV GERAL", "val": f"{dmv_atual} um", "status": classe_asabe_final},
                {"label": "DENSIDADE", "val": f"{densidade_atual} g/cm2", "status": "Ideal" if densidade_atual >= 60 else "Baixa"},
                {"label": "ESTABILIDADE", "val": f"SPAN {span_atual}", "status": "Estavel" if span_atual <= 1.2 else "Variavel"}
            ]
            pos_x = 15
            for ind in indicadores:
                pdf.set_fill_color(248, 249, 250)
                pdf.rect(pos_x, pdf.get_y(), 56, 18, 'F')
                pdf.rect(pos_x, pdf.get_y(), 56, 18, 'D')
                pdf.set_font("Arial", "B", 7.5)
                pdf.set_text_color(100, 110, 120)
                pdf.text(pos_x + 4, pdf.get_y() + 5, ind["label"])
                pdf.set_font("Arial", "B", 12)
                pdf.set_text_color(20, 30, 40)
                pdf.text(pos_x + 4, pdf.get_y() + 11, ind["val"])
                pdf.set_font("Arial", "", 7.5)
                pdf.text(pos_x + 4, pdf.get_y() + 15, f"Status: {ind['status']}")
                pos_x += 62
            
            # --- SEÇÃO MODELAGEM 3D ---
            pdf.set_y(122)
            pdf.set_text_color(40, 50, 60)
            pdf.set_font("Arial", "B", 11)
            pdf.cell(0, 6, "3. Projecao Computacional 3D (Efeito Fator Espalhamento)", ln=True)
            pdf.ln(2)
            
            tmp_sph = "tmp_sph.png"
            tmp_imp = "tmp_imp.png"
            fig_sph.write_image(tmp_sph, width=500, height=400, scale=2)
            fig_imp.write_image(tmp_imp, width=500, height=400, scale=2)
            
            y_grafico = pdf.get_y()
            pdf.image(tmp_sph, x=15, y=y_grafico, w=88, h=65)
            pdf.image(tmp_imp, x=107, y=y_grafico, w=88, h=65)
            
            pdf.set_font("Arial", "I", 8)
            pdf.set_text_color(100, 100, 100)
            pdf.text(18, y_grafico + 68, "Modelo A: Gota esferica suspensa em voo livre.")
            pdf.text(110, y_grafico + 68, f"Modelo B: Mancha expandida apos colidir (Fator: {fator_espalhamento}).")
            
            if os.path.exists(tmp_sph): os.remove(tmp_sph)
            if os.path.exists(tmp_imp): os.remove(tmp_imp)
            
            # --- SEÇÃO DIAGNÓSTICO ---
            pdf.set_y(200)
            pdf.set_font("Arial", "B", 11)
            pdf.set_text_color(40, 50, 60)
            pdf.cell(0, 6, "4. Diagnostico de Campo e Engenharia de Calibracao", ln=True)
            pdf.ln(1)
            pdf.set_fill_color(255, 251, 230)
            pdf.set_text_color(90, 70, 10)
            pdf.set_font("Arial", "", 9)
            texto_quadro = f"Recomendacoes Tecnicas:\n[DERIVA] -> {rec_deriva}\n[DENSIDADE] -> {rec_densidade}"
            pdf.multi_cell(180, 5, texto_quadro, border=1, fill=True)
            
            # --- CARTÃO HORIZONTAL ---
            pdf.set_y(222)
            pdf.set_text_color(40, 50, 60)
            pdf.set_font("Arial", "B", 11)
            pdf.cell(0, 6, "5. Amostragem Digital do Cartao Hidrossensivel", ln=True)
            pdf.ln(1)
            
            if nome_arquivo in imagens_processadas:
                img_f = Image.fromarray(cv2.cvtColor(imagens_processadas[nome_arquivo]["focada_bgr"], cv2.COLOR_BGR2RGB))
                img_horizontal = img_f.rotate(90, expand=True)
                tmp_c = "tmp_laudo_h.jpg"
                img_horizontal.save(tmp_c, "JPEG", quality=95)
                pdf.image(tmp_c, x=50, y=pdf.get_y(), w=110, h=35)
                if os.path.exists(tmp_c): os.remove(tmp_c)
            
            # --- RODAPÉ ---
            pdf.set_y(266)
            pdf.set_font("Arial", "I", 7.5)
            pdf.set_text_color(140, 140, 140)
            pdf.cell(0, 4, "Algoritmo Computacional de Calibracao Hidrossensivel IAC / Aplique Bem 2026.", ln=True, align="C")

            return pdf.output(dest='S').encode('latin1')

        pdf_bytes = gerar_pdf_laudo_grafico()
        st.download_button(
            label="🚀 GERAR LAUDO COMPLETO COM GRÁFICOS 3D E CLIMA (PDF)",
            data=pdf_bytes,
            file_name=f"Laudo_Completo_3D_{nome_arquivo.split('.')[0]}.pdf",
            mime="application/pdf",
            use_container_width=True
        )

# --- PAINEL DE HISTÓRICO ---
with aba_relatorio:
    st.write("---")
    st.markdown("### 🗄️ Histórico Permanente de Análises")
    conn = sqlite3.connect(DB_NAME)
    df_historico = pd.read_sql_query("SELECT * FROM historico_analises ORDER BY id DESC", conn)
    conn.close()
    if not df_historico.empty:
        st.dataframe(df_historico, use_container_width=True)
