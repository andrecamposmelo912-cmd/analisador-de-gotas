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

dispositivo_ajustado = obter_dispositivo()

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
            cultura TEXT,
            posicao TEXT,
            cobertura REAL,
            densidade REAL,
            dmv REAL,
            span REAL,
            classe_asabe TEXT
        )
    """)
    conn.commit()
    conn.close()

def salvar_analise_bd(cultura, posicao, cob, dens, dmv, span, classe):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        cursor.execute("""
            INSERT INTO historico_analises (data_hora, cultura, posicao, cobertura, densidade, dmv, span, classe_asabe)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (agora, cultura, posicao, cob, dens, dmv, span, classe))
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

# Seletor de Tipo de Papel (Importante para a sua validação científica!)
st.sidebar.header("📄 Matriz de Amostragem")
tipo_papel_sel = st.sidebar.selectbox(
    "Tipo de Papel Utilizado:",
    ["Hidrossensível (Amarelo)", "Cromecote (Branco + Corante)"]
)

# Painel de Calibração Lateral
st.sidebar.header("🔬 Calibração de Visão (IAC)")
sensibilidade_azul = st.sidebar.slider(
    "Sensibilidade de Captura", 
    min_value=1, max_value=25, value=11, step=2,
    help="Valores menores evitam contaminação de fundo; valores maiores capturam pingos muito claros."
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
    st.title("💧 Analisador de Gotas Inteligente 2.4")
    st.markdown("**Parceria Científica de Campo:** Instituto Agronómico (IAC) & Programa Aplique Bem")
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
if "dados_analise" not in st.session_state:
    st.session_state["dados_analise"] = {}
if "cultura_selecionada" not in st.session_state:
    st.session_state["cultura_selecionada"] = "Cana-de-Açúcar"

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
    "📥 Captura e Resultados", "📊 Gráficos e Projeções 3D", "🔍 Inspeção de Cartões", "📋 Relatório e Validação Dropscope"
])

# ------------------------------------------------------------------------------
# 📥 ABA 1: CAPTURA E RESULTADOS DE DOSSEL MULTI-PAPEL
# ------------------------------------------------------------------------------
with aba_upload:
    st.subheader("🌱 Configuração do Ensaio / Arquitetura do Alvo")
    cultura_sel = st.selectbox(
        "Selecione a Cultura Agroindustrial:",
        ["Cana-de-Açúcar", "Soja", "Milho", "Algodão", "Café", "Citros", "Hortifrúti"],
        key="cultura_box_upload"
    )
    st.session_state["cultura_selecionada"] = cultura_sel
    
    with st.expander("📸 Envio de Ficheiros do Ensaio", expanded=not st.session_state["analise_concluida"]):
        col_desenho, col_uploads = st.columns([1, 1])
        
        with col_desenho:
            st.markdown(f"#### 📐 Diagrama de Posicionamento: **{st.session_state['cultura_selecionada']}**")
            st.info(f"Modo Ativo: **Papel {tipo_papel_sel}**")
            if st.session_state['cultura_selecionada'] == "Cana-de-Açúcar":
                st.info("💡 **Diretriz IAC - Cana:** Posicione os cartões de forma estratégica:\n* **Topo:** No topo do colmo/folhas abertas.\n* **Meio:** Região mediana.\n* **Baixeiro:** Próximo à base/colmo inferior.")
            elif st.session_state['cultura_selecionada'] == "Soja":
                st.info("💡 **Diretriz IAC - Soja:** Atente-se ao fechamento das linhas.\n* **Topo:** Folhas superiores.\n* **Baixeiro:** Interior do dossel inferior.")
            else:
                st.info(f"💡 Colete amostras verticais no(a) {st.session_state['cultura_selecionada']}.")

        with col_uploads:
            st.markdown("#### Ficheiros de Amostras (Envie apenas os que coletou)")
            img_topo = st.file_uploader("📥 Cartão 1: TOPO (Terço Superior)", type=['jpg','jpeg','png','heic','heif'], key="up_topo")
            img_meio = st.file_uploader("📥 Cartão 2: MEIO (Terço Médio)", type=['jpg','jpeg','png','heic','heif'], key="up_meio")
            img_baixo = st.file_uploader("📥 Cartão 3: BAIXEIRO (Terço Inferior)", type=['jpg','jpeg','png','heic','heif'], key="up_baixo")
            
            st.write("")
            btn_analisar = st.button("🚀 INICIAR LEITURA DE DOSSEL", use_container_width=True, type="primary")
            
            if btn_analisar:
                dict_imagens = {}
                if img_topo: dict_imagens["Topo"] = img_topo
                if img_meio: dict_imagens["Meio"] = img_meio
                if img_baixo: dict_imagens["Baixeiro"] = img_baixo
                
                if not dict_imagens:
                    st.warning("⚠️ Envie pelo menos um cartão para iniciar o processamento.")
                else:
                    resultados_temp = {}
                    
                    for posicao, arq in dict_imagens.items():
                        nome_arq = arq.name
                        ext = nome_arq.split('.')[-1].lower()
                        if ext in ['heic', 'heif']:
                            pil_img = Image.open(arq).convert("RGB")
                            img_bgr = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
                        else:
                            file_bytes = np.asarray(bytearray(arq.read()), dtype=np.uint8)
                            img_bgr = cv2.imdecode(file_bytes, 1)
                            
                        if img_bgr is not None:
                            # 🎯 CORREÇÃO HOMOGRÁFICA DE PERSPECTIVA
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
                                margem_h, margem_w = int(h_orig * 0.1), int(w_orig * 0.1)
                                img_focada = img_bgr[margem_h:h_orig-margem_h, margem_w:w_orig-margem_w]
                                img_focada = cv2.resize(img_focada, (400, 900))
                                
                            alt_px, larg_px = img_focada.shape[:2]
                            area_tot_px = alt_px * larg_px
                            um_por_px = (30.0 / larg_px) * 1000.0
                            
                            # ==========================================================================
                            # 🔬 SELEÇÃO DUPLA DE MOTOR DE VISÃO CIENTÍFICA (AMARELO vs CROMECOTE)
                            # ==========================================================================
                            if "Hidrossensível" in tipo_papel_sel:
                                # Conversão CIELAB para contraste absoluto no canal b*
                                lab = cv2.cvtColor(img_focada, cv2.COLOR_BGR2Lab)
                                b_canal = lab[:, :, 2]
                                b_suavizado = cv2.bilateralFilter(b_canal, 9, 50, 50)
                                
                                otsu_th, _ = cv2.threshold(b_suavizado, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                                bias = (sensibilidade_azul - 11) * 1.5
                                _, mascara = cv2.threshold(b_suavizado, otsu_th + bias, 255, cv2.THRESH_BINARY_INV)
                            else:
                                # Cromecote (Branco + Corante Azul/Escuro)
                                gray_c = cv2.cvtColor(img_focada, cv2.COLOR_BGR2GRAY)
                                gray_suavizado = cv2.bilateralFilter(gray_c, 9, 50, 50)
                                
                                # Grayscale Otsu invertido para isolar o corante escuro no papel brilhante branco
                                th_val, _ = cv2.threshold(gray_suavizado, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
                                bias = (11 - sensibilidade_azul) * 1.5 # Direção inversa para papel claro
                                _, mascara = cv2.threshold(gray_suavizado, th_val + bias, 255, cv2.THRESH_BINARY_INV)
                            
                            # Limpeza morfológica estrita para mitigar ruídos térmicos
                            kernel_limpeza = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
                            mascara = cv2.morphologyEx(mascara, cv2.MORPH_OPEN, kernel_limpeza)
                            
                            contornos, _ = cv2.findContours(mascara, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                            gotas = [c for c in contornos if cv2.contourArea(c) > 2]
                            
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
                            
                            resultados_temp[posicao] = {
                                "cobertura": round(cob, 2), "densidade": round(dens, 2),
                                "dmv": round(dmv, 1), "span": round(span, 2), "asabe": classificar_asabe(dmv),
                                "img_original": cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB), 
                                "img_analisada": img_vis, "mascara": mascara,
                                "diametros": diametros, "focada": img_focada, "total_gotas": len(gotas),
                                "classes": [pequenas_perc, medias_perc, grandes_perc]
                            }
                            
                            salvar_analise_bd(st.session_state["cultura_selecionada"], posicao, round(cob, 2), round(dens, 2), round(dmv, 1), round(span, 2), classificar_asabe(dmv))
                            
                    st.session_state["dados_analise"] = resultados_temp
                    st.session_state["analise_concluida"] = True
                    st.rerun()

    # Exibição do Painel de Resultados de Dossel
    if st.session_state["analise_concluida"]:
        st.write("---")
        c_voltar, c_tit_res = st.columns([1, 4])
        with c_voltar:
            if st.button("⬅️ Fazer Nova Análise", use_container_width=True):
                st.session_state["analise_concluida"] = False
                st.session_state["dados_analise"] = {}
                st.rerun()
        with c_tit_res:
            st.markdown(f"### 📊 Resultados de Campo: **{st.session_state['cultura_selecionada']}** ({tipo_papel_sel})")
            
        res_dados = st.session_state["dados_analise"]
        lista_posicoes = [p for p in ["Topo", "Meio", "Baixeiro"] if p in res_dados]
        
        if lista_posicoes:
            abas_profundidade = st.tabs([f"📍 Posicionamento: {pos}" for pos in lista_posicoes])
            for idx, pos in enumerate(lista_posicoes):
                with abas_profundidade[idx]:
                    dados_pos = res_dados[pos]
                    
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("💧 DMV (Mediana)", f"{dados_pos['dmv']} µm")
                    c2.metric("🎯 Cobertura Superficial", f"{dados_pos['cobertura']} %")
                    c3.metric("🔢 Densidade de Gotas", f"{dados_pos['densidade']} g/cm²")
                    c4.metric("📈 Gotas Contadas", f"{dados_pos['total_gotas']} gotas")
                    
                    st.markdown("#### 🔬 Avaliação e Veredito Técnico")
                    if st.session_state["cultura_selecionada"] == "Cana-de-Açúcar" and pos == "Baixeiro":
                        if dados_pos['densidade'] < 40:
                            st.error(f"❌ **Densidade Baixa:** A cobertura de {dados_pos['densidade']} gotas/cm² está insuficiente para o controle de ferrugem no baixeiro da cana. Meta sugerida pelo IAC: >40 gotas/cm².")
                        else:
                            st.success("🎯 **Excelente Penetração:** Densidade e cobertura adequadas para transpor a folhagem da cana-de-açúcar.")
                    elif dados_pos['cobertura'] < 4.0:
                        st.warning("⚠️ **Atenção:** Baixa penetração detectada. O dossel superior pode estar criando efeito guarda-chuva.")
                    else:
                        st.success("✅ **Conformidade Técnica:** Cobertura dentro dos parâmetros ideais de pulverização.")
                        
                    st.write("")
                    st.image(dados_pos["img_analisada"], caption=f"Perímetros da Amostra - {pos}", use_container_width=True)
        else:
            st.info("Suba as imagens no botão inicial para renderizar os dados.")

# ------------------------------------------------------------------------------
# 📊 ABA 2: GRÁFICOS E SIMULAÇÕES VOLUMÉTRICAS EM 3D
# ------------------------------------------------------------------------------
with aba_graficos:
    st.subheader("📊 Análise de Homogeneidade e Projeções Espaciais")
    
    res_dados = st.session_state["dados_analise"]
    if not res_dados:
        st.warning("⚠️ Nenhum cartão processado no momento. Vá para a aba 'Captura e Resultados' e processe pelo menos uma amostra.")
    else:
        posicoes_disponiveis = list(res_dados.keys())
        pos_sel = st.selectbox("Selecione a amostra para analisar os gráficos:", posicoes_disponiveis, key="pos_sel_graficos")
        dados_pos = res_dados[pos_sel]
        
        col_g1, col_g2 = st.columns(2)
        
        with col_g1:
            st.markdown("**Frequência Real de Tamanho das Gotas (µm)**")
            if len(dados_pos["diametros"]) > 0:
                counts, bins = np.histogram(dados_pos["diametros"], bins=15)
                st.bar_chart(pd.DataFrame({"Quantidade": counts}, index=bins[:-1].astype(int)))
            else:
                st.caption("Gotas insuficientes para gerar histograma.")
                
            st.markdown("**Distribuição de Classes de Gotas (%)**")
            st.bar_chart(pd.DataFrame({"Percentual (%)": dados_pos["classes"]}, index=['Pequenas (<150µm)', 'Médias (150-300µm)', 'Grandes (>300µm)']))
            
        with col_g2:
            st.markdown("**Distribuição Espacial em 3D (Gota Mediana em Voo)**")
            raio_g = max(dados_pos["dmv"] / 2.0, 10.0)
            u_p = np.linspace(0, 2 * np.pi, 25)
            v_p = np.linspace(0, np.pi, 25)
            xs = raio_g * np.outer(np.cos(u_p), np.sin(v_p))
            ys = raio_g * np.outer(np.sin(u_p), np.sin(v_p))
            zs = raio_g * np.outer(np.ones(np.size(u_p)), np.cos(v_p))
            fig_sph = go.Figure(data=[go.Surface(x=xs, y=ys, z=zs, colorscale="Blues", showscale=False)])
            fig_sph.update_layout(scene=dict(aspectmode='cube'), height=300, margin=dict(l=0,r=0,b=0,t=0))
            st.plotly_chart(fig_sph, use_container_width=True)
            st.caption(f"Simulação baseada no DMV calculado ({dados_pos['dmv']} µm).")

# ------------------------------------------------------------------------------
# 🔍 ABA 3: LABORATÓRIO DE INSPEÇÃO VISUAL AVANÇADA (WATERSHED E FILTROS)
# ------------------------------------------------------------------------------
with aba_inspecao:
    st.subheader("🔬 Laboratório de Inspeção e Análise de Imagem")
    st.markdown("Utilize esta aba para aplicar filtros matemáticos avançados no cartão processado.")
    
    res_dados = st.session_state["dados_analise"]
    if not res_dados:
        st.warning("⚠️ Nenhum cartão processado no momento. Vá para a aba 'Captura e Resultados' e processe uma amostra.")
    else:
        posicoes_disponiveis = list(res_dados.keys())
        pos_sel = st.selectbox("Escolha a amostra para auditar:", posicoes_disponiveis, key="pos_sel_inspecao")
        dados_pos = res_dados[pos_sel]
        
        filtro_selecionado = st.radio(
            "🔬 Escolha o Filtro Diagnóstico Avançado:",
            ["1. Visão de Campo", "2. Mapa Térmico de Deposição", "3. Watershed (Separação de Gotas)", "4. Isolamento Estrito de Deriva (<150µm)"],
            key="filtro_inspecao_radio"
        )
        
        col_img_1, col_img_2 = st.columns(2)
        
        with col_img_1:
            st.image(dados_pos["img_original"], caption="Amostra Original de Campo", use_container_width=True)
            
        with col_img_2:
            if "1." in filtro_selecionado:
                st.image(dados_pos["img_analisada"], caption="Detecção Convencional de Perímetro", use_container_width=True)
                st.info("Gotas identificadas e circuladas em vermelho.")
                
            elif "2." in filtro_selecionado:
                b_map = cv2.GaussianBlur(dados_pos["mascara"], (45, 45), 0)
                h_map = cv2.cvtColor(cv2.applyColorMap(b_map, cv2.COLORMAP_JET), cv2.COLOR_BGR2RGB)
                st.image(h_map, caption="Mapa Térmico de Concentração de Calda", use_container_width=True)
                st.warning("⚠️ **Diagnóstico:** Áreas vermelhas indicam acúmulos e risco de escorrimento. Áreas em azul representam falha.")
                
            elif "3." in filtro_selecionado:
                dist_transform = cv2.distanceTransform(dados_pos["mascara"], cv2.DIST_L2, 5)
                _, sure_fg = cv2.threshold(dist_transform, 0.3 * dist_transform.max(), 255, 0)
                sure_fg = np.uint8(sure_fg)
                
                img_ws = cv2.cvtColor(dados_pos["focada"], cv2.COLOR_BGR2RGB)
                img_ws[sure_fg == 255] = [0, 255, 0]
                
                st.image(img_ws, caption="Identificação de Núcleos (Watershed)", use_container_width=True)
                st.info("💡 ** Watershed:** Este filtro localiza o pico central de cada mancha para separar gotas coladas.")
                
            elif "4." in filtro_selecionado:
                img_deriva = np.zeros_like(dados_pos["focada"])
                cont_deriva = 0
                for i, c in enumerate(dados_pos["img_analisada"]):
                    if i < len(dados_pos["diametros"]) and dados_pos["diametros"][i] < 150.0:
                        cv2.drawContours(img_deriva, [c], -1, (255, 0, 180), -1)
                        cont_deriva += 1
                
                st.image(cv2.cvtColor(img_deriva, cv2.COLOR_BGR2RGB), caption="Apenas Espectro de Risco de Deriva (<150µm)", use_container_width=True)
                perc_deriva = (cont_deriva / dados_pos["total_gotas"] * 100) if dados_pos["total_gotas"] > 0 else 0
                st.error(f"🚨 **Gotas Voláteis:** {cont_deriva} gotas sob risco direto de deriva ({perc_deriva:.1f}% do total).")

# ------------------------------------------------------------------------------
# 📋 ABA 4: RELATÓRIOS E VALIDAÇÃO CIENTÍFICA (GOTINT VS DROPSCOPE)
# ------------------------------------------------------------------------------
with aba_relatorio:
    st.subheader("📋 Geração de Laudos e Validação Científica")
    st.markdown("Valide o robô comparando-o com o equipamento de laboratório de referência (Dropscope) para gerar dados para o seu artigo ou homologação comercial.")
    
    res_dados = st.session_state.get("dados_analise", {})
    
    if res_dados:
        aba_sub_laudo, aba_sub_validacao = st.tabs(["📝 Laudo Técnico Comercial", "🔬 Validação Científica (Artigo)"])
        
        with aba_sub_laudo:
            st.markdown("### 📊 Sumário Executivo do Ensaio Atual")
            lista_pos_sum = list(res_dados.keys())
            total_papeis = len(lista_pos_sum)
            
            media_cob = np.mean([res_dados[p]["cobertura"] for p in lista_pos_sum])
            media_dens = np.mean([res_dados[p]["densidade"] for p in lista_pos_sum])
            media_dmv = np.mean([res_dados[p]["dmv"] for p in lista_pos_sum])
            
            c_sum1, c_sum2, c_sum3, c_sum4 = st.columns(4)
            c_sum1.metric("📋 Total de Papéis", f"{total_papeis} un")
            c_sum2.metric("💧 DMV Médio", f"{media_dmv:.1f} µm")
            c_sum3.metric("🎯 Cobertura Média", f"{media_cob:.2f} %")
            c_sum4.metric("🔢 Densidade Média", f"{media_dens:.1f} g/cm²")
            
            def gerar_pdf_laudo_grafico(dados_ensaio, cultura_nome, clima_info):
                pdf = FPDF()
                pdf.add_page()
                pdf.set_margins(15, 15, 15)
                
                pdf.set_fill_color(26, 36, 43)
                pdf.rect(0, 0, 210, 42, 'F')
                
                pdf.set_y(12)
                pdf.set_font("Arial", "B", 14)
                pdf.set_text_color(255, 255, 255)
                pdf.cell(0, 8, "PROGRAMA APLIQUE BEM - LAUDO DE CONFORMIDADE TECNICA", ln=True, align="C")
                pdf.set_font("Arial", "I", 9.5)
                pdf.cell(0, 5, "Parceria Cientifica: Instituto Agronomico (IAC)", ln=True, align="C")
                
                pdf.set_y(48)
                pdf.set_text_color(40, 50, 60)
                pdf.set_font("Arial", "B", 12)
                pdf.cell(0, 8, f"Relatorio de Ensaio: {cultura_nome}", ln=True)
                
                pdf.ln(3)
                pdf.line(15, pdf.get_y(), 195, pdf.get_y())
                pdf.ln(4)
                
                pdf.set_font("Arial", "B", 11)
                pdf.cell(0, 6, "1. Condicoes Climatologicas Coletadas", ln=True)
                pdf.ln(1)
                
                pdf.set_fill_color(245, 247, 248)
                pdf.rect(15, pdf.get_y(), 180, 16, 'F')
                pdf.set_font("Arial", "", 9.5)
                
                if clima_info:
                    texto_clima = (
                        f"Localidade: {clima_info['local']}   |   Temperatura: {clima_info['temp']} C\n"
                        f"Humidade Relativa (UR): {clima_info['uhr']}%   |   Velocidade do Vento: {clima_info['vento']} km/h"
                    )
                else:
                    texto_clima = "Localidade informada: Campinas (Dados de satelite nao carregados)."
                    
                pdf.multi_cell(180, 5.5, texto_clima, border=1)
                pdf.ln(4)
                
                pdf.set_font("Arial", "B", 11)
                pdf.cell(0, 6, "2. Diagnostico Individual dos Cartoes Hidrossenseis", ln=True)
                pdf.ln(2)
                
                pdf.set_fill_color(0, 80, 136)
                pdf.set_text_color(255, 255, 255)
                pdf.set_font("Arial", "B", 9)
                
                pdf.cell(30, 8, "Posicao", border=1, fill=True, align="C")
                pdf.cell(30, 8, "DMV (Dv0.5)", border=1, fill=True, align="C")
                pdf.cell(30, 8, "Cobertura (%)", border=1, fill=True, align="C")
                pdf.cell(35, 8, "Densidade (g/cm2)", border=1, fill=True, align="C")
                pdf.cell(20, 8, "SPAN", border=1, fill=True, align="C")
                pdf.cell(35, 8, "Classe ASABE", border=1, fill=True, align="C")
                pdf.ln()
                
                pdf.set_text_color(40, 50, 60)
                pdf.set_font("Arial", "", 9)
                
                for pos, dados in dados_ensaio.items():
                    pdf.cell(30, 8, str(pos), border=1, align="C")
                    pdf.cell(30, 8, f"{dados['dmv']} um", border=1, align="C")
                    pdf.cell(30, 8, f"{dados['cobertura']}%", border=1, align="C")
                    pdf.cell(35, 8, f"{dados['densidade']}", border=1, align="C")
                    pdf.cell(20, 8, f"{dados['span']}", border=1, align="C")
                    pdf.cell(35, 8, str(dados['asabe']), border=1, align="C")
                    pdf.ln()
                    
                pdf.ln(6)
                pdf.set_y(266)
                pdf.set_font("Arial", "I", 7.5)
                pdf.set_text_color(140, 140, 140)
                pdf.cell(0, 4, "Algoritmo Computacional de Calibracao Hidrossensivel IAC / Aplique Bem 2026.", ln=True, align="C")
                return pdf.output(dest='S').encode('latin1', errors='replace')

            try:
                pdf_bytes = gerar_pdf_laudo_grafico(res_dados, st.session_state["cultura_selecionada"], dados_clima)
                st.download_button(
                    label="🚀 GERAR LAUDO COMPLETO DO DOSSEL (PDF)",
                    data=pdf_bytes,
                    file_name="Laudo_Tecnico_Dossel_IAC.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"Erro ao compor o laudo em PDF: {e}")
        
        with aba_sub_validacao:
            st.markdown("### 🔬 Validação e Correlação Estatística (Dropscope vs. GotInt)")
            st.write("Insira abaixo as leituras de referência extraídas do software físico do Dropscope para comparar com o algoritmo do robô.")
            
            valid_pos_sel = st.selectbox("Selecione qual papel do dossel deseja validar:", lista_pos_sum)
            dados_got = res_dados[valid_pos_sel]
            
            c_val1, c_val2, c_val3 = st.columns(3)
            with c_val1:
                ref_dmv = st.number_input("DMV de Referência Dropscope (µm):", min_value=1.0, value=float(dados_got["dmv"] * 0.95), step=1.0)
            with c_val2:
                ref_cob = st.number_input("Cobertura de Referência Dropscope (%):", min_value=0.1, value=float(dados_got["cobertura"] * 0.98), step=0.1)
            with c_val3:
                ref_dens = st.number_input("Densidade de Referência Dropscope (g/cm²):", min_value=0.1, value=float(dados_got["densidade"] * 1.02), step=0.1)
            
            # --- CÁLCULO ESTATÍSTICO DE ERRO ---
            erro_dmv = abs(dados_got["dmv"] - ref_dmv) / ref_dmv * 100
            erro_cob = abs(dados_got["cobertura"] - ref_cob) / ref_cob * 100
            erro_dens = abs(dados_got["densidade"] - ref_dens) / ref_dens * 100
            
            st.write("---")
            st.markdown("#### 📊 Desvio Relativo de Leitura")
            
            col_err1, col_err2, col_err3 = st.columns(3)
            col_err1.metric("Erro Relativo DMV", f"{erro_dmv:.2f} %", delta="Margem aceitável" if erro_dmv <= 10 else "Calibração recomendada", delta_color="normal" if erro_dmv <= 10 else "inverse")
            col_err2.metric("Erro Relativo Cobertura", f"{erro_cob:.2f} %", delta="Margem aceitável" if erro_cob <= 10 else "Calibração recomendada", delta_color="normal" if erro_cob <= 10 else "inverse")
            col_err3.metric("Erro Relativo Densidade", f"{erro_dens:.2f} %", delta="Margem aceitável" if erro_dens <= 10 else "Calibração recomendada", delta_color="normal" if erro_dens <= 10 else "inverse")
            
            # --- MODELAGEM DE RECOMENDAÇÃO DE AJUSTE CIENTÍFICO ---
            st.markdown("#### 🔧 Engenharia de Ajuste de Curva")
            if erro_dmv > 5.0 or erro_dens > 5.0:
                # Sugere novo fator de espalhamento matemático com base no desvio
                fator_sugerido = fator_espalhamento * (dados_got["dmv"] / ref_dmv)
                st.warning(f"💡 **Recomendação de Calibração:** Para aproximar os dados ao padrão do Dropscope, ajuste o **Fator de Espalhamento** na barra lateral para **{fator_sugerido:.2f}**.")
            else:
                st.success("🎯 **Excelente Correlação:** O algoritmo e o Dropscope estão perfeitamente correlacionados para esta amostra. Erro estatístico abaixo de 5%.")
                
            # Gráfico de barras comparativo direto Dropscope vs GotInt
            fig_comp = go.Figure()
            fig_comp.add_trace(go.Bar(name='Dropscope (Referência)', x=['DMV (µm)', 'Cobertura (%)', 'Densidade (g/cm²)'], y=[ref_dmv, ref_cob, ref_dens], marker_color='#005088'))
            fig_comp.add_trace(go.Bar(name='GotInt 2.4', x=['DMV (µm)', 'Cobertura (%)', 'Densidade (g/cm²)'], y=[dados_got["dmv"], dados_got["cobertura"], dados_got["densidade"]], marker_color='#00a651'))
            fig_comp.update_layout(barmode='group', height=350, margin=dict(l=0, r=0, t=10, b=10))
            st.plotly_chart(fig_comp, use_container_width=True)
            
    else:
        st.info("Efetue a leitura de um cartão na aba 'Captura e Resultados' para ativar o painel de validação.")
        
    st.write("---")
    st.markdown("### 💾 Leituras Registradas no Banco de Dados Local")
    try:
        conn = sqlite3.connect(DB_NAME)
        df_h = pd.read_sql_query("SELECT id, data_hora, cultura, posicao, cobertura, densidade, dmv, span, classe_asabe FROM historico_analises ORDER BY id DESC LIMIT 20", conn)
        conn.close()
        
        if not df_h.empty:
            st.dataframe(df_h, use_container_width=True)
            st.success("✅ Sincronização do banco de dados ativa e estável.")
        else:
            st.info("Nenhuma leitura arquivada no banco local.")
    except Exception as e:
        st.error(f"Erro ao aceder ao banco de dados local: {e}")
