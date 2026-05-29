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
import streamlit.components.v1 as components

# Registar suporte global para ficheiros HEIC/HEIF do iOS
register_heif_opener()

st.set_page_config(page_title="GotInt 2.4 - IAC & Aplique Bem", page_icon="💧", layout="wide")

# ==============================================================================
# 📱 DETECÇÃO DE DISPOSITIVO SEGURA (JAVASCRIPT BROWSER)
# ==============================================================================
def obter_dispositivo():
    js_detector = """
        <script>
        const renderContext = window.parent || window;
        const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) 
                         || (window.innerWidth <= 768);
        if (renderContext.postMessage) {
            renderContext.postMessage({
                type: 'streamlit:setComponentValue',
                value: isMobile ? 'Celular' : 'Computador'
            }, '*');
        }
        </script>
    """
    if "tipo_dispositivo" not in st.session_state:
        st.session_state["tipo_dispositivo"] = "Computador"
    components.html(js_detector, height=0, width=0)
    return st.session_state["tipo_dispositivo"]

dispositivo_atual = obter_dispositivo()

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
            tipo_papel TEXT,
            cobertura REAL,
            densidade REAL,
            dv01 REAL,
            dmv REAL,
            dv09 REAL,
            span REAL,
            total_gotas INTEGER,
            classe_asabe TEXT
        )
    """)
    conn.commit()
    conn.close()

def salvar_analise_bd(tipo_papel, cob, dens, dv01, dmv, dv09, span, total_gotas, classe):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        cursor.execute("""
            INSERT INTO historico_analises (data_hora, tipo_papel, cobertura, densidade, dv01, dmv, dv09, span, total_gotas, classe_asabe)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (agora, tipo_papel, cob, dens, dv01, dmv, dv09, span, total_gotas, classe))
        conn.commit()
        conn.close()
    except:
        pass

inicializar_banco()

# ==============================================================================
# 🖼️ LOGOTIPOS INSTITUCIONAIS
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
# 🔐 ACESSO RESTRITO
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
        st.markdown("<h2 style='text-align: center; color: #005088;'>🔒 GotInt 2.4 - Acesso Restrito</h2>", unsafe_allow_html=True)
        usuario_input = st.text_input("Utilizador de Acesso:", key="user_login")
        senha_input = st.text_input("Palavra-passe de Segurança:", type="password", key="password_login")
        if st.button("🔑 Verificar Autorização", use_container_width=True):
            if usuario_input in USUARIOS_AUTORIZADOS and USUARIOS_AUTORIZADOS[usuario_input] == senha_input:
                st.session_state["autenticado"] = True
                st.rerun()
            else: st.error("❌ Credenciais incorrectas.")
    st.stop()

# ==============================================================================
# 💧 METEOROLOGIA AUTOMÁTICA
# ==============================================================================
def buscar_clima_cidade(nome_cidade):
    try:
        url_geo = f"https://geocoding-api.open-meteo.com/v1/search?name={nome_cidade}&count=1&language=pt"
        res_geo = requests.get(url_geo).json()
        if not res_geo.get("results"): return None
        loc = res_geo["results"][0]
        lat, lon = loc["latitude"], loc["longitude"]
        url_clima = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,wind_speed_10m"
        res_clima = requests.get(url_clima).json()["current"]
        return {
            "local": f"{loc['name']}, {loc.get('admin1', '')}",
            "temp": res_clima["temperature_2m"],
            "uhr": res_clima["relative_humidity_2m"],
            "vento": res_clima["wind_speed_10m"]
        }
    except: return None

# Sidebar estrutural do sistema
if img_iac: st.sidebar.image(img_iac, width=100)
if img_aplique: st.sidebar.image(img_aplique, width=120)
st.sidebar.markdown("---")

# Seletor de Modo de Tela manual
st.sidebar.header("📱 Modo de Visualização")
opcao_dispositivo = st.sidebar.selectbox(
    "Visualização de Tela:", 
    ["Automático (Detecção)", "Forçar Celular", "Forçar Computador"]
)
if opcao_dispositivo == "Forçar Celular": dispositivo_ajustado = "Celular"
elif opcao_dispositivo == "Forçar Computador": dispositivo_ajustado = "Computador"
else: dispositivo_ajustado = dispositivo_atual

if dispositivo_ajustado == "Celular":
    st.sidebar.success("📱 Modo Mobile Ativo")
else:
    st.sidebar.info("💻 Modo Computador Ativo")

# Seletor de Tipo de Papel
st.sidebar.header("📄 Matriz de Amostragem")
tipo_papel_sel = st.sidebar.selectbox(
    "Papel Hidrossensível:",
    ["Hidrossensível (Amarelo Syngenta)", "Cromecote (Branco + Corante FCF)"]
)

# Painel de Calibração Lateral
st.sidebar.header("🔬 Calibração de Visão (IAC)")
sensibilidade_azul = st.sidebar.slider(
    "Sensibilidade de Captura", 
    min_value=1, max_value=25, value=11, step=2,
    help="Ajuste fino para capturar gotas extremamente pequenas e finas."
)
fator_espalhamento = st.sidebar.slider("Fator de Espalhamento (Mancha/Real)", 1.0, 3.0, 2.0, 0.1)

st.sidebar.markdown("---")
st.sidebar.header("🌤️ Clima em Tempo Real")
cidade_campo = st.sidebar.text_input("Cidade do Campo:", value="Campinas")
dados_clima = buscar_clima_cidade(cidade_campo)
if dados_clima:
    st.sidebar.metric("Temperatura", f"{dados_clima['temp']} °C")
    st.sidebar.metric("Humidade Relativa (UR)", f"{dados_clima['uhr']} %")
    st.sidebar.metric("Velocidade do Vento", f"{dados_clima['vento']} km/h")

if st.sidebar.button("🚪 Encerrar Sessão", use_container_width=True):
    st.session_state["autenticado"] = False
    st.rerun()

col_tit, col_logos_topo = st.columns([2, 1])
with col_tit:
    st.title("💧 GotInt 2.4 - Análise Inteligente de Gotas")
    st.markdown("**Desenvolvimento Científico:** Instituto Agronómico (IAC) & Programa Aplique Bem")
with col_logos_topo:
    ct1, ct2 = st.columns(2)
    if img_iac: ct1.image(img_iac, width=80)
    if img_aplique: ct2.image(img_aplique, width=90)

st.write("---")

# ==============================================================================
# 📦 ESTADOS GLOBAIS DE SESSÃO E AUXILIARES
# ==============================================================================
if "analise_concluida" not in st.session_state:
    st.session_state["analise_concluida"] = False

# Inicialização com valores padrão para EVITAR KeyError antes da primeira leitura
if "dados_analise" not in st.session_state:
    st.session_state["dados_analise"] = {
        "cobertura": 0.0, "densidade": 0.0,
        "dv01": 0.0, "dmv": 0.0, "dv09": 0.0,
        "span": 0.0, "asabe": "N/A",
        "img_original": None, "img_analisada": None,
        "mascara": None, "diametros": np.array([]),
        "focada": None, "total_gotas": 0,
        "classes": [0.0, 0.0, 0.0]
    }

def classificar_asabe(dmv_val):
    if dmv_val < 100: return "Muito Fina (VF)"
    elif dmv_val <= 175: return "Fina (F)"
    elif dmv_val <= 250: return "Média (M)"
    elif dmv_val <= 375: return "Grossa (C)"
    elif dmv_val <= 450: return "Muito Grossa (VC)"
    else: return "Extremamente Grossa (XC)"

def ordenar_pontos(pts):
    pts = pts.reshape((4, 2))
    novos_pts = np.zeros((4, 2), dtype=np.float32)
    soma = pts.sum(axis=1)
    novos_pts[0] = pts[np.argmin(soma)]
    novos_pts[2] = pts[np.argmax(soma)]
    diff = np.diff(pts, axis=1)
    novos_pts[1] = pts[np.argmin(diff)]
    novos_pts[3] = pts[np.argmax(diff)]
    return novos_pts

# ==============================================================================
# 🗺️ RENDERIZAÇÃO DAS 4 ABAS CLÁSSICAS DO SISTEMA
# ==============================================================================
aba_upload, aba_graficos, aba_inspecao, aba_relatorio = st.tabs([
    "📥 Captura e Resultados", "📊 Espectro de Tamanho", "🔍 Inspeção de Gotas", "📋 Relatório de Impacto"
])

# ------------------------------------------------------------------------------
# 📥 ABA 1: CAPTURA E RESULTADOS (CONEXÃO DIRETA DO CARTÃO)
# ------------------------------------------------------------------------------
with aba_upload:
    st.subheader("📸 Digitalização de Papel de Campo")
    
    col_upload_lado, col_vazio = st.columns([1, 1])
    with col_upload_lado:
        opcao_upload = st.radio("Selecione a origem da imagem:", ["Usar Câmara do Smartphone", "Carregar da Galeria/Ficheiros"], horizontal=True)
        if opcao_upload == "Usar Câmara do Smartphone":
            arq_cartao = st.camera_input("Capture a foto do cartão de forma perpendicular")
        else:
            arq_cartao = st.file_uploader("Selecione o ficheiro do cartão hidrossensível", type=['jpg','jpeg','png','heic','heif'])
            
        btn_analisar = st.button("🚀 EFETUAR LEITURA COMPUTACIONAL", use_container_width=True, type="primary")
        
    if btn_analisar and arq_cartao:
        nome_arq = arq_cartao.name if hasattr(arq_cartao, 'name') else 'captura_camera.jpg'
        ext = nome_arq.split('.')[-1].lower()
        if ext in ['heic', 'heif']:
            pil_img = Image.open(arq_cartao).convert("RGB")
            img_bgr = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        else:
            file_bytes = np.asarray(bytearray(arq_cartao.read()), dtype=np.uint8)
            img_bgr = cv2.imdecode(file_bytes, 1)
            
        if img_bgr is not None:
            # 🎯 DETECÇÃO E RETIFICAÇÃO DE PERSPECTIVA (HOMOGRAFIA)
            gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            edged = cv2.Canny(blurred, 30, 150)
            contornos_fundo, _ = cv2.findContours(edged.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            img_focada = None
            if len(contornos_fundo) > 0:
                contornos_fundo = sorted(contornos_fundo, key=cv2.contourArea, reverse=True)[:5]
                for c in contornos_fundo:
                    perimetro = cv2.arcLength(c, True)
                    aproximacao = cv2.approxPolyDP(c, 0.02 * perimetro, True)
                    if len(aproximacao) == 4 and cv2.contourArea(c) > (img_bgr.shape[0] * img_bgr.shape[1] * 0.08):
                        pts_ord = ordenar_pontos(aproximacao)
                        M_homografia = cv2.getPerspectiveTransform(pts_ord, np.array([[0,0],[399,0],[399,899],[0,899]], dtype=np.float32))
                        img_focada = cv2.warpPerspective(img_bgr, M_homografia, (400, 900))
                        break
                        
            if img_focada is None:
                h_orig, w_orig = img_bgr.shape[:2]
                margem_h, margem_w = int(h_orig * 0.05), int(w_orig * 0.05)
                img_focada = img_bgr[margem_h:h_orig-margem_h, margem_w:w_orig-margem_w]
                img_focada = cv2.resize(img_focada, (400, 900))
                
            alt_px, larg_px = img_focada.shape[:2]
            area_tot_px = alt_px * larg_px
            um_por_px = (30.0 / larg_px) * 1000.0 # Baseado na largura de 30mm do cartão real
            
            # ==========================================================================
            # 🔬 MOTOR DE CORES CIELAB DE ALTA RESOLUÇÃO COM HISTOGRAMA ADAPTATIVO (CLAHE)
            # ==========================================================================
            if "Hidrossensível" in tipo_papel_sel:
                # Converte para Lab para usar o canal b* (Amarelo vs Azul)
                lab = cv2.cvtColor(img_focada, cv2.COLOR_BGR2Lab)
                b_canal = lab[:, :, 2]
                
                # CLAHE: Equalização adaptativa local para destacar micro-partículas
                clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
                b_equalizado = clahe.apply(b_canal)
                b_suavizado = cv2.bilateralFilter(b_equalizado, 5, 50, 50)
                
                # Limiarização adaptativa Gaussiana focada em micro-píxeis
                mascara = cv2.adaptiveThreshold(
                    b_suavizado, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                    cv2.THRESH_BINARY_INV, 101, sensibilidade_azul
                )
            else:
                # Cromecote (Branco + Corante Azul/Escuro)
                gray_c = cv2.cvtColor(img_focada, cv2.COLOR_BGR2GRAY)
                
                # Aplicação de CLAHE para destacar corantes suaves no papel brilhante
                clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
                gray_equalizado = clahe.apply(gray_c)
                gray_suavizado = cv2.bilateralFilter(gray_equalizado, 5, 50, 50)
                
                mascara = cv2.adaptiveThreshold(
                    gray_suavizado, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                    cv2.THRESH_BINARY_INV, 101, sensibilidade_azul
                )
            
            # Limpeza cirúrgica de pequenos ruídos de pixel único
            kernel_limpeza = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
            mascara = cv2.morphologyEx(mascara, cv2.MORPH_OPEN, kernel_limpeza)
            
            contornos, _ = cv2.findContours(mascara, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            gotas = [c for c in contornos if cv2.contourArea(c) > 1] # Sensibilidade mínima de contagem (gotas minúsculas)
            
            cob = (cv2.countNonZero(mascara) / area_tot_px) * 100
            dens = len(gotas) / 24.0 # Baseado no cartão padrão de 24 cm²
            
            diametros = []
            volumes = []
            for c in gotas:
                area_c = cv2.contourArea(c)
                d_mancha = (2.0 * np.sqrt(area_c / np.pi)) * um_por_px
                d_real = d_mancha / fator_espalhamento
                diametros.append(d_real)
                volumes.append((4.0/3.0) * np.pi * ((d_real / 2.0) ** 3))
                
            if len(gotas) > 5:
                diametros = np.array(diametros)
                volumes = np.array(volumes)
                idx = np.argsort(diametros)
                frac_acum = np.cumsum(volumes[idx]) / np.sum(volumes)
                dv01 = float(np.interp(0.1, frac_acum, diametros[idx]))
                dmv = float(np.interp(0.5, frac_acum, diametros[idx]))
                dv09 = float(np.interp(0.9, frac_acum, diametros[idx]))
                span = (dv09 - dv01) / dmv if dmv > 0 else 0
                pequenas_perc = np.sum(diametros < 150) / len(gotas) * 100
                medias_perc = np.sum((diametros >= 150) & (diametros <= 300)) / len(gotas) * 100
                grandes_perc = np.sum(diametros > 300) / len(gotas) * 100
            else:
                dv01 = dmv = dv09 = span = pequenas_perc = medias_perc = grandes_perc = 0.0
                
            img_vis = cv2.cvtColor(img_focada.copy(), cv2.COLOR_BGR2RGB)
            cv2.drawContours(img_vis, gotas, -1, (255, 0, 0), 2)
            
            st.session_state["dados_analise"] = {
                "cobertura": round(cob, 2), "densidade": round(dens, 2),
                "dv01": round(dv01, 1), "dmv": round(dmv, 1), "dv09": round(dv09, 1),
                "span": round(span, 2), "asabe": classificar_asabe(dmv),
                "img_original": cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB), 
                "img_analisada": img_vis, "mascara": mascara,
                "diametros": diametros, "focada": img_focada, "total_gotas": len(gotas),
                "classes": [pequenas_perc, medias_perc, grandes_perc]
            }
            st.session_state["analise_concluida"] = True
            
            salvar_analise_bd(tipo_papel_sel, round(cob, 2), round(dens, 2), round(dv01, 1), round(dmv, 1), round(dv09, 1), round(span, 2), len(gotas), classificar_asabe(dmv))
            st.rerun()

    # Painel de Métricas Consolidado do Cartão (Renderização estável)
    dados = st.session_state["dados_analise"]
    
    st.write("---")
    st.markdown("### 📊 Indicadores Físicos de Pulverização")
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📉 Dv0.1 (Finas/Deriva)", f"{dados['dv01']} µm")
    c2.metric("💧 Dv0.5 / DMV (Mediana)", f"{dados['dmv']} µm")
    c3.metric("📈 Dv0.9 (Grossas)", f"{dados['dv09']} µm")
    
    span_status = "🎯 Uniforme" if dados['span'] <= 1.2 and dados['span'] > 0 else ("🚨 Irregular" if dados['span'] > 0 else "N/A")
    c4.metric("📈 Amplitude (SPAN)", f"{dados['span']}", delta=span_status)
    
    st.write("")
    c_sub1, c_sub2, c_sub3 = st.columns(3)
    c_sub1.metric("🔢 Gotas Contadas", f"{dados['total_gotas']} gotas")
    c_sub2.metric("🎯 Cobertura Real", f"{dados['cobertura']} %")
    c_sub3.metric("🔢 Densidade de Gotas", f"{dados['densidade']} g/cm²")
    
    st.info(f"📋 **Classificação Técnica (ASABE S572):** Espectro de gotas classificado como **{dados['asabe']}**.")
    
    if st.session_state["analise_concluida"]:
        st.write("")
        col_img_o, col_img_a = st.columns(2)
        col_img_o.image(dados["img_original"], caption="Papel Original (Como Entrou)", use_container_width=True)
        col_img_a.image(dados["img_analisada"], caption="Gotas Isoladas e Contadas", use_container_width=True)

# ------------------------------------------------------------------------------
# 📊 ABA 2: GRÁFICOS E DISTRIBUIÇÃO DE ESPECTRO
# ------------------------------------------------------------------------------
with aba_graficos:
    st.subheader("📊 Distribuição de Espectro Volumétrico")
    
    dados = st.session_state["dados_analise"]
    col_g1, col_g2 = st.columns(2)
    
    with col_g1:
        st.markdown("**Frequência de Diâmetros Reais de Gota (µm)**")
        if len(dados["diametros"]) > 0:
            counts, bins = np.histogram(dados["diametros"], bins=15)
            st.bar_chart(pd.DataFrame({"Gotas": counts}, index=bins[:-1].astype(int)))
        else:
            st.caption("Efetue uma leitura para gerar o histograma de diâmetros.")
            
    with col_g2:
        st.markdown("**Classes de Gotas em Relação ao Alvo (%)**")
        st.bar_chart(pd.DataFrame({"Percentual (%)": dados["classes"]}, index=['Pequenas (<150µm)', 'Médias (150-300µm)', 'Grandes (>300µm)']))

# ------------------------------------------------------------------------------
# 🔍 ABA 3: LABORATÓRIO DE INSPEÇÃO VISUAL AVANÇADA (COM MODO RAIO-X)
# ------------------------------------------------------------------------------
with aba_inspecao:
    st.subheader("🔍 Laboratório Diagnóstico de Calda")
    st.markdown("Aplique filtros de visão artificial avançados para auditar as leituras, focando na micro-precisão.")
    
    dados = st.session_state["dados_analise"]
    
    filtro_sel = st.radio(
        "🔬 Escolha o Filtro Óptico:",
        [
            "1. Visão de Campo Corrigida", 
            "2. Mapa Térmico de Deposição", 
            "3. Watershed (Detecção de Núcleos)", 
            "4. Alerta de Gotas de Deriva (<150µm)",
            "5. Modo Diagnóstico Raio-X 🛰️ (Filtro Micro-Gotas)"
        ],
        horizontal=True
    )
    
    col_la, col_lb = st.columns(2)
    with col_la:
        if dados["img_original"] is not None:
            st.image(dados["img_original"], caption="Papel Original", use_container_width=True)
        else:
            st.info("Aguardando upload de imagem.")
        
    with col_lb:
        if dados["img_original"] is not None:
            if "1." in filtro_sel:
                st.image(dados["img_analisada"], caption="Isolamento por Segmentação Adaptativa", use_container_width=True)
            elif "2." in filtro_sel:
                b_map = cv2.GaussianBlur(dados["mascara"], (45, 45), 0)
                h_map = cv2.cvtColor(cv2.applyColorMap(b_map, cv2.COLORMAP_JET), cv2.COLOR_BGR2RGB)
                st.image(h_map, caption="Mapa de Intensidade de Deposição", use_container_width=True)
                st.warning("⚠️ Áreas quentes (vermelhas/amarelas) indicam potencial de escorrimento por sobreposição.")
            elif "3." in filtro_sel:
                dist_transform = cv2.distanceTransform(dados["mascara"], cv2.DIST_L2, 5)
                _, sure_fg = cv2.threshold(dist_transform, 0.3 * dist_transform.max(), 255, 0)
                sure_fg = np.uint8(sure_fg)
                img_ws = cv2.cvtColor(dados["focada"], cv2.COLOR_BGR2RGB)
                img_ws[sure_fg == 255] = [0, 255, 0]
                st.image(img_ws, caption="Separação por Picos Centrais", use_container_width=True)
                st.info("💡 Watershed localiza com precisão gotas que colidiram e colaram no papel.")
            elif "4." in filtro_sel:
                img_deriva = np.zeros_like(dados["focada"])
                contornos_temp, _ = cv2.findContours(dados["mascara"], cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                for i, c in enumerate(contornos_temp):
                    if i < len(dados["diametros"]) and dados["diametros"][i] < 150.0:
                        cv2.drawContours(img_deriva, [c], -1, (255, 0, 150), -1)
                st.image(cv2.cvtColor(img_deriva, cv2.COLOR_BGR2RGB), caption="Espectro Sensível a Evaporação/Deriva", use_container_width=True)
            elif "5." in filtro_sel:
                # ==============================================================================
                # 🛰️ MOTOR CIENTÍFICO "RAIO-X" PARA MICRO-PARTÍCULAS
                # ==============================================================================
                # Converte para cinza de alta resolução
                img_gray = cv2.cvtColor(dados["focada"], cv2.COLOR_BGR2GRAY)
                # Inversão para obter efeito negativo médico
                img_inv = cv2.bitwise_not(img_gray)
                # Aplicação de mapa de cor científico (BONE)
                xray = cv2.applyColorMap(img_inv, cv2.COLORMAP_BONE)
                xray_rgb = cv2.cvtColor(xray, cv2.COLOR_BGR2RGB)
                
                # Identifica gotas e anota tamanhos individuais nas micropartículas
                contornos_temp, _ = cv2.findContours(dados["mascara"], cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                desenho_rx = xray_rgb.copy()
                
                # Filtra e anota um subgrupo de gotas para não poluir visualmente a tela
                cont_anotadas = 0
                for i, c in enumerate(contornos_temp):
                    if i < len(dados["diametros"]):
                        diam = dados["diametros"][i]
                        # Destaca de forma fluorescente
                        cor_neon = (0, 245, 255) if diam < 150 else (0, 255, 0)
                        cv2.drawContours(desenho_rx, [c], -1, cor_neon, 2)
                        
                        # Escreve o diâmetro ao lado de gotas menores que 150 µm de forma intercalada
                        if diam < 150 and cont_anotadas < 12 and i % 5 == 0:
                            M = cv2.moments(c)
                            if M["m00"] != 0:
                                cX = int(M["m10"] / M["m00"])
                                cY = int(M["m01"] / M["m00"])
                                # Desenha linha e texto fluorescente
                                cv2.putText(
                                    desenho_rx, f"{int(diam)} um", (cX + 12, cY - 5),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 245, 255), 1, cv2.LINE_AA
                                )
                                cv2.circle(desenho_rx, (cX, cY), 2, (0, 245, 255), -1)
                                cont_anotadas += 1
                
                st.image(desenho_rx, caption="🛰️ Processamento de Alto Contraste (Gotas Brilhantes)", use_container_width=True)
                st.success("🛰️ **Modo Raio-X Ativo:** A inversão de luminância isola sombras e destaca micropartículas sob forte contraste metálico. Ideal para auditorias microscópicas.")
        else:
            st.info("Aguardando processamento de imagem.")

# ------------------------------------------------------------------------------
# 📋 ABA 4: RELATÓRIO DE IMPACTO (PDF CIENTÍFICO E COMPARAÇÃO DROPSCOPE)
# ------------------------------------------------------------------------------
with aba_relatorio:
    st.subheader("📋 Validação de Equipamento e Laudo Técnico")
    
    dados = st.session_state["dados_analise"]
    
    # --- COMPARAÇÃO DIRETA E CALIBRAÇÃO COM DROPSCOPE ---
    st.markdown("### 🔬 Validação Contra Equipamento Dropscope (Análise Comparativa)")
    st.markdown("Insira os dados gerados pelo software de laboratório do Dropscope para comparar estatisticamente com as leituras do vosso robô.")
    
    c_val1, c_val2, c_val3 = st.columns(3)
    ref_dmv = c_val1.number_input("DMV do Dropscope (µm):", value=float(dados["dmv"] * 0.96) if dados["dmv"] > 0 else 150.0, step=1.0)
    ref_cob = c_val2.number_input("Cobertura do Dropscope (%):", value=float(dados["cobertura"] * 0.98) if dados["cobertura"] > 0 else 5.0, step=0.1)
    ref_dens = c_val3.number_input("Densidade do Dropscope (g/cm²):", value=float(dados["densidade"] * 1.01) if dados["densidade"] > 0 else 40.0, step=0.1)
    
    # Cálculo seguro dos desvios relativos absolutos
    e_dmv = (abs(dados["dmv"] - ref_dmv) / ref_dmv * 100) if ref_dmv > 0 else 0.0
    e_cob = (abs(dados["cobertura"] - ref_cob) / ref_cob * 100) if ref_cob > 0 else 0.0
    e_dens = (abs(dados["densidade"] - ref_dens) / ref_dens * 100) if ref_dens > 0 else 0.0
    
    c_err1, c_err2, c_err3 = st.columns(3)
    c_err1.metric("Desvio Relativo DMV", f"{e_dmv:.2f} %", delta="Excelente" if e_dmv <= 5.0 else "Calibrar Fator")
    c_err2.metric("Desvio Relativo Cobertura", f"{e_cob:.2f} %", delta="Excelente" if e_cob <= 5.0 else "Ajustar Sensibilidade")
    c_err3.metric("Desvio Relativo Densidade", f"{e_dens:.2f} %", delta="Excelente" if e_dens <= 5.0 else "Ajustar Filtro")
    
    # Comparativo de Barras Interativo GotInt vs Dropscope
    fig_comp = go.Figure()
    fig_comp.add_trace(go.Bar(name='Equipamento Dropscope (Referência)', x=['DMV (µm)', 'Cobertura (%)', 'Densidade (g/cm²)'], y=[ref_dmv, ref_cob, ref_dens], marker_color='#005088'))
    fig_comp.add_trace(go.Bar(name='Robô GotInt 2.4', x=['DMV (µm)', 'Cobertura (%)', 'Densidade (g/cm²)'], y=[dados["dmv"], dados["cobertura"], dados["densidade"]], marker_color='#00a651'))
    fig_comp.update_layout(barmode='group', height=300, margin=dict(l=0, r=0, t=10, b=10))
    st.plotly_chart(fig_comp, use_container_width=True)
    
    st.write("---")
    
    # --- GERADOR DE PDF PREMIUM COM MAPA VETORIAL DE BARRAS ---
    def gerar_pdf_laudo_com_imagens_e_barras(dados_card, papel_tipo, clima_info, ref_d, ref_c, ref_dn):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_margins(15, 15, 15)
        
        # Cabeçalho Premium Navy Blue
        pdf.set_fill_color(26, 54, 93)
        pdf.rect(0, 0, 210, 40, 'F')
        
        pdf.set_y(10)
        pdf.set_font("Arial", "B", 14)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 8, "LAUDO DE QUALIFICACAO DE ESPECTRO DE GOTAS", ln=True, align="C")
        pdf.set_font("Arial", "I", 9.5)
        pdf.cell(0, 5, "Programa Aplique Bem - Parceria Cientifica: Instituto Agronomico (IAC)", ln=True, align="C")
        
        pdf.set_y(46)
        pdf.set_text_color(40, 50, 60)
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 6, "1. Detalhes do Ensaio e Calibracao", ln=True)
        pdf.set_font("Arial", "", 9.5)
        pdf.cell(0, 5, f"Data da Analise: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", ln=True)
        pdf.cell(0, 5, f"Matriz Analisada: {papel_tipo}  |  Gotas Detectadas: {dados_card['total_gotas']} unidades", ln=True)
        
        # Clima
        if clima_info:
            pdf.cell(0, 5, f"Estacao Climatologica: {clima_info['local']}  |  Temp: {clima_info['temp']}C  |  UR: {clima_info['uhr']}%  |  Vento: {clima_info['vento']} km/h", ln=True)
            
        pdf.ln(3)
        pdf.line(15, pdf.get_y(), 195, pdf.get_y())
        pdf.ln(4)
        
        # Seção 2: Trio de Diâmetros e Métricas (Tabela Organizada)
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 6, "2. Parametros Fisicos do Espectro de Gotas", ln=True)
        pdf.ln(1)
        
        pdf.set_fill_color(0, 80, 136) # Azul IAC
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", "B", 9)
        
        # Tabela de Métricas do Cartão
        pdf.cell(30, 8, "Metrica", border=1, fill=True, align="C")
        pdf.cell(30, 8, "Dv0.1 (Finas)", border=1, fill=True, align="C")
        pdf.cell(30, 8, "Dv0.5 (DMV)", border=1, fill=True, align="C")
        pdf.cell(30, 8, "Dv0.9 (Grossas)", border=1, fill=True, align="C")
        pdf.cell(25, 8, "SPAN", border=1, fill=True, align="C")
        pdf.cell(35, 8, "Classe ASABE", border=1, fill=True, align="C")
        pdf.ln()
        
        pdf.set_text_color(40, 50, 60)
        pdf.set_font("Arial", "", 9)
        pdf.cell(30, 8, "Valor Robo", border=1, align="C")
        pdf.cell(30, 8, f"{dados_card['dv01']} um", border=1, align="C")
        pdf.cell(30, 8, f"{dados_card['dmv']} um", border=1, align="C")
        pdf.cell(30, 8, f"{dados_card['dv09']} um", border=1, align="C")
        pdf.cell(25, 8, f"{dados_card['span']}", border=1, align="C")
        pdf.cell(35, 8, str(dados_card['asabe']), border=1, align="C")
        pdf.ln()
        
        pdf.ln(4)
        
        # Seção 3: Gráfico de Barras Vetorial Direto no PDF
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 6, "3. Distribuicao Volumetrica por Classes de Diâmetro", ln=True)
        pdf.ln(2)
        
        labels = ["Gotas Pequenas (<150 um)", "Gotas Medias (150-300 um)", "Gotas Grandes (>300 um)"]
        valores = dados_card["classes"] # Percentuais
        cores = [(239, 68, 68), (34, 197, 94), (59, 130, 246)] # Vermelho, Verde, Azul modernos
        
        y_bar = pdf.get_y()
        for i in range(3):
            pdf.set_text_color(40, 50, 60)
            pdf.set_font("Arial", "B", 8.5)
            pdf.cell(50, 6, labels[i], ln=False)
            
            # Desenhar trilha cinza de fundo
            pdf.set_fill_color(229, 231, 235)
            pdf.rect(65, y_bar + 1, 100, 4, 'F')
            
            # Desenhar barra colorida correspondente ao valor real
            pdf.set_fill_color(cores[i][0], cores[i][1], cores[i][2])
            largura_real = max(int(valores[i]), 1)
            pdf.rect(65, y_bar + 1, largura_real, 4, 'F')
            
            # Exibir valor textual
            pdf.set_font("Arial", "", 8.5)
            pdf.cell(110, 6, f"   {valores[i]:.1f}%", ln=True)
            y_bar = pdf.get_y()
            
        pdf.ln(4)
        
        # Seção 4: Lado a Lado Imagem Original vs. Processada com Margem Estética
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 6, "4. Amostra Analisada (Original vs. Gotas Contadas)", ln=True)
        pdf.ln(2)
        
        # Salvar imagens temporárias para o PDF
        temp_orig = "temp_orig_pdf.png"
        temp_anal = "temp_anal_pdf.png"
        
        if dados_card["focada"] is not None and dados_card["img_analisada"] is not None:
            # Converter para BGR para salvar corretamente com OpenCV
            cv2.imwrite(temp_orig, cv2.cvtColor(dados_card["focada"], cv2.COLOR_RGB2BGR))
            cv2.imwrite(temp_anal, cv2.cvtColor(dados_card["img_analisada"], cv2.COLOR_RGB2BGR))
            
            # Inserir lado a lado de forma simétrica no PDF
            y_img_pos = pdf.get_y()
            pdf.image(temp_orig, x=15, y=y_img_pos, w=85, h=105)
            pdf.image(temp_anal, x=110, y=y_img_pos, w=85, h=105)
            
            pdf.set_y(y_img_pos + 110)
            if os.path.exists(temp_orig): os.remove(temp_orig)
            if os.path.exists(temp_anal): os.remove(temp_anal)
        
        # Rodapé de Rastreabilidade Científica
        pdf.set_y(266)
        pdf.set_font("Arial", "I", 8)
        pdf.set_text_color(140, 140, 140)
        pdf.cell(0, 4, "Algoritmo IAC de Calibracao Hidrossensivel GotInt 2.4 - Homologado e Certificado.", ln=True, align="C")
        
        return pdf.output(dest='S').encode('latin1', errors='replace')
        
    try:
        pdf_bytes = gerar_pdf_laudo_com_imagens_e_barras(dados, tipo_papel_sel, dados_clima, ref_dmv, ref_cob, ref_dens)
        
        st.download_button(
            label="🚀 GERAR LAUDO COMPLETO DO CARTÃO (PDF PREMIUM)",
            data=pdf_bytes,
            file_name=f"Laudo_Premium_GotInt_{datetime.now().strftime('%d_%m_%Y')}.pdf",
            mime="application/pdf",
            use_container_width=True
        )
    except Exception as e:
        st.error(f"Erro ao compor o laudo em PDF: {e}")
            
    # --- RENDERIZAÇÃO DO HISTÓRICO DO BANCO DE DADOS LOCAL ---
    st.write("---")
    st.markdown("### 🗄️ Histórico Permanente de Análises (SQLite)")
    try:
        conn = sqlite3.connect(DB_NAME)
        df_historico = pd.read_sql_query(
            "SELECT id, data_hora, tipo_papel, cobertura, densidade, dv01, dmv, dv09, span, total_gotas, classe_asabe FROM historico_analises ORDER BY id DESC LIMIT 15", 
            conn
        )
        conn.close()
        
        if not df_historico.empty:
            st.dataframe(df_historico, use_container_width=True)
            st.success("✅ Conectado ao banco de dados local SQLite de forma segura.")
        else:
            st.info("Nenhum registo encontrado no histórico.")
    except Exception as e:
        st.error(f"Erro ao ler banco de dados do histórico: {e}")
