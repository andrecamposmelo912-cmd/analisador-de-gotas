import streamlit as st
import cv2
import numpy as np
import pandas as pd
from pillow_heif import register_heif_opener
import io
import os
from PIL import Image
from fpdf import FPDF

# Registra o suporte a arquivos HEIC/HEIF do iPhone
register_heif_opener()

st.set_page_config(page_title="Gota Inteligente - IAC & Aplique Bem", page_icon="💧", layout="wide")

# ==============================================================================
# 🖼️ CONFIGURAÇÃO DOS LOGOTIPOS LOCAIS (AJUSTADO PARA O SEU REPOSITÓRIO)
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
# 🔐 TELA DE LOGIN CENTRALIZADA E PROPORCIONAL
# ==============================================================================
USUARIOS_AUTORIZADOS = {
    "andre": "agro2026",      
    "iac": "apliquebem2026"  
}

if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    # Espaçamento para descer o conteúdo para o centro da tela
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    
    # Criamos 3 colunas para centralizar o bloco principal (1 lateral, 2 central, 1 lateral)
    _, col_central, _ = st.columns([1, 2, 1])
    
    with col_central:
        # Bloco dos Logotipos
        # Usamos colunas internas para colocar os logos lado a lado
        l1, l2 = st.columns(2)
        with l1:
            if img_iac:
                # Ajustamos a largura para que o logo vertical (IAC) não fique gigante
                st.image(img_iac, width=200) 
        with l2:
            if img_aplique:
                # Ajustamos para que o logo horizontal (Aplique Bem) acompanhe a proporção
                st.image(img_aplique, width=220)

        # Título e Login
        st.markdown("<h2 style='text-align: center; color: #005088;'>🔒 Gota Inteligente - Acesso Restrito</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center;'>Plataforma oficial de análise digitalizada de pulverização em parceria com o <b>IAC</b> e <b>Programa Aplique Bem</b>.</p>", unsafe_allow_html=True)
        
        usuario_input = st.text_input("Usuário de Acesso:", key="user_login")
        senha_input = st.text_input("Senha de Segurança:", type="password", key="password_login")
        
        st.markdown("<br>", unsafe_allow_html=True)
        botao_entrar = st.button("🔑 Verificar Autorização", use_container_width=True)
        
        if botao_entrar:
            if usuario_input in USUARIOS_AUTORIZADOS and USUARIOS_AUTORIZADOS[usuario_input] == senha_input:
                st.session_state["autenticado"] = True
                st.success("Acesso autorizado! Carregando painel...")
                st.rerun()
            else:
                st.error("❌ Credenciais incorretas ou usuário não autorizado.")
                
    st.stop()

# ==============================================================================
# 💧 APLICATIVO PRINCIPAL (SÓ EXECUTA SE AUTENTICADO)
# ==============================================================================

# Logos menores no Topo da Barra Lateral para não ocupar espaço
if img_iac: st.sidebar.image(img_iac, width=100)
if img_aplique: st.sidebar.image(img_aplique, width=120)

st.sidebar.markdown("---")
if st.sidebar.button("🚪 Encerrar Sessão (Sair)", use_container_width=True):
    st.session_state["autenticado"] = False
    st.rerun()

# Cabeçalho do App
col_tit, col_logos_topo = st.columns([2, 1])
with col_tit:
    st.title("💧 Analisador de Gotas Inteligente")
    st.markdown("**Parceria Científica:** Instituto Agronômico (IAC) & Programa Aplique Bem")
with col_logos_topo:
    # Mantemos os logos pequenos no topo do app também
    ct1, ct2 = st.columns(2)
    if img_iac: ct1.image(img_iac, width=80)
    if img_aplique: ct2.image(img_aplique, width=90)

st.write("---")

st.sidebar.header("🛠️ Configurações de Calibração")
fator_espalhamento = st.sidebar.slider("Fator de Espalhamento (Mancha/Real)", min_value=1.0, max_value=3.0, value=2.0, step=0.1)

aba_upload, aba_graficos, aba_inspecao, aba_relatorio = st.tabs([
    "📥 Captura e Resultados", 
    "📊 Gráficos do Espectro", 
    "🔍 Inspeção de Cartões",
    "📋 Relatório Técnico Didático"
])

with aba_upload:
    st.subheader("📸 Captura do Cartão Hidrossensível")
    metodo_captura = st.radio("Escolha como inserir o cartão:", ["Usar a Câmera do Celular", "Enviar foto da Galeria/Arquivo"], horizontal=True)
    
    arquivo_enviado = None
    if metodo_captura == "Usar a Câmera do Celular":
        arquivo_enviado = st.camera_input("Posicione o cartão de forma centralizada e tire a foto")
    else:
        arquivo_enviado = st.file_uploader("Selecione a imagem do cartão", type=['jpg', 'jpeg', 'png', 'heic', 'heif'])

def formatar_csv_br(df):
    df_br = df.copy()
    for col in df_br.columns:
        if df_br[col].dtype in [np.float64, np.float32]:
            df_br[col] = df_br[col].apply(lambda x: f"{x:.4f}".replace('.', ','))
    return df_br.to_csv(index=False, sep=';').encode('utf-8-sig')

if arquivo_enviado:
    resultados_gerais = []
    dados_graficos = {}
    imagens_processadas = {}
    
    nome_arquivo = getattr(arquivo_enviado, 'name', 'captura_camera.jpg')
    extensao = nome_arquivo.split('.')[-1].lower()
    
    try:
        if extensao in ['heic', 'heif']:
            pil_img = Image.open(arquivo_enviado).convert("RGB")
            img_rgb = np.array(pil_img)
            img_original = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
        else:
            file_bytes = np.asarray(bytearray(arquivo_enviado.read()), dtype=np.uint8)
            img_original = cv2.imdecode(file_bytes, 1)
    except Exception as e:
        st.error(f"Erro ao processar imagem: {e}")
        st.stop()

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
        
        altura_px, largura_px = img_focada.shape[:2]
        area_total_pixels = altura_px * largura_px
        
        largura_mm = 30.0
        altura_mm = 80.0
        area_cartao_cm2 = (largura_mm / 10.0) * (altura_mm / 10.0)
        
        mm_por_pixel = largura_mm / largura_px
        um_por_pixel = mm_por_pixel * 1000.0
        
        hsv = cv2.cvtColor(img_focada, cv2.COLOR_BGR2HSV)
        amostra_hsv = hsv[altura_px//4:3*altura_px//4, largura_px//4:3*largura_px//4]
        tom_medio_h = np.mean(amostra_hsv[:, :, 0])
        tom_medio_s = np.mean(amostra_hsv[:, :, 1])
        
        if 15 <= tom_medio_h <= 45 and tom_medio_s > 60:
            tipo_cartao = "Original (Amarelo)"
            amarelo_baixo = np.array([15, 50, 40])
            amarelo_alto = np.array([45, 255, 255])
            mascara_fundo = cv2.inRange(hsv, amarelo_baixo, amarelo_alto)
            mascara = cv2.bitwise_not(mascara_fundo)
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
            mascara = cv2.morphologyEx(mascara, cv2.MORPH_OPEN, kernel)
        else:
            tipo_cartao = "Revelado (Branco)"
            azul_baixo = np.array([85, 40, 40])
            azul_alto = np.array([145, 255, 255])
            mascara = cv2.inRange(hsv, azul_baixo, azul_alto)
        
        contornos, _ = cv2.findContours(mascara, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        gotas_filtradas = [c for c in contornos if cv2.contourArea(c) > 3]
        num_gotas = len(gotas_filtradas)
        
        pixels_gotas = cv2.countNonZero(mascara)
        porcentagem_cobertura = (pixels_gotas / area_total_pixels) * 100
        densidade_gotas = num_gotas / area_cartao_cm2 if num_gotas > 0 else 0
        
        diametros_reais_um = []
        volumes_reais_um3 = []
        
        for c in gotas_filtradas:
            area_px = cv2.contourArea(c)
            diametro_mancha_px = 2.0 * np.sqrt(area_px / np.pi)
            diametro_mancha_um = diametro_mancha_px * um_por_pixel
            diametro_real_um = diametro_mancha_um / fator_espalhamento
            volume_real_um3 = (4.0 / 3.0) * np.pi * ((diametro_real_um / 2.0) ** 3)
            
            diametros_reais_um.append(diametro_real_um)
            volumes_reais_um3.append(volume_real_um3)
            
        diametros_reais_um = np.array(diametros_reais_um)
        volumes_reais_um3 = np.array(volumes_reais_um3)
        
        if num_gotas > 0:
            indices_ordenados = np.argsort(diametros_reais_um)
            diametros_ordenados = diametros_reais_um[indices_ordenados]
            volumes_ordenados = volumes_reais_um3[indices_ordenados]
            
            volume_total = np.sum(volumes_ordenados)
            volume_acumulado = np.cumsum(volumes_ordenados)
            fracao_acumulada = volume_acumulado / volume_total
            
            dv01 = float(np.interp(0.1, fracao_acumulada, diametros_ordenados))
            text_dv05 = float(np.interp(0.5, fracao_acumulada, diametros_ordenados))
            dv09 = float(np.interp(0.9, fracao_acumulada, diametros_ordenados))
            span = (dv09 - dv01) / text_dv05 if text_dv05 > 0 else 0
            
            pequenas = np.sum(diametros_reais_um < 150) / num_gotas * 100
            medias = np.sum((diametros_reais_um >= 150) & (diametros_reais_um <= 300)) / num_gotas * 100
            grandes = np.sum(diametros_reais_um > 300) / num_gotas * 100
        else:
            dv01 = text_dv05 = dv09 = span = pequenas = medias = grandes = 0.0
            
        quad_h = altura_px // 2
        quad_w = largura_px // 2
        contagem_quadrantes = [0, 0, 0, 0]
        for c in gotas_filtradas:
            M = cv2.moments(c)
            if M["m00"] != 0:
                cX = int(M["m10"] / M["m00"])
                cY = int(M["m01"] / M["m00"])
                if cX < quad_w and cY < quad_h: contagem_quadrantes[0] += 1
                elif cX >= quad_w and cY < quad_h: contagem_quadrantes[1] += 1
                elif cX < quad_w and cY >= quad_h: contagem_quadrantes[2] += 1
                else: contagem_quadrantes[3] += 1
                    
        cv_espacial = (np.std(contagem_quadrantes) / np.mean(contagem_quadrantes) * 100) if np.mean(contagem_quadrantes) > 0 else 0.0

        resultados_gerais.append({
            "Nome do Arquivo": nome_arquivo, "Tipo Detectado": tipo_cartao, "Cobertura (%)": round(porcentagem_cobertura, 2),
            "Nº de Gotas": num_gotas, "Densidade (gotas/cm²)": round(densidade_gotas, 2), "Dv0.1 (µm)": round(dv01, 1),
            "Dv0.5 / DMV (µm)": round(text_dv05, 1), "Dv0.9 (µm)": round(dv09, 1), "Amplitude (SPAN)": round(span, 2),
            "Gotas Pequenas (<150µm) %": round(pequenas, 1), "Gotas Médias (150-300µm) %": round(medias, 1), "Gotas Grandes (>300µm) %": round(grandes, 1),
            "CV da Distribuição (%)": round(cv_espacial, 2)
        })
        
        dados_graficos[nome_arquivo] = {"diametros": diametros_reais_um, "classes": [pequenas, medias, grandes]}
        
        img_visualizacao = img_focada.copy()
        cv2.drawContours(img_visualizacao, gotas_filtradas, -1, (0, 255, 0), 2)
        imagens_processadas[nome_arquivo] = {
            "original": img_original, 
            "analisada": cv2.cvtColor(img_visualizacao, cv2.COLOR_BGR2RGB),
            "focada_bgr": img_visualizacao
        }

    df_geral = pd.DataFrame(resultados_gerais)

    # --- DASHBOARD DE RESULTADOS ---
    with aba_upload:
        st.write("---")
        st.markdown("### 📊 Dashboard de Resultados da Amostra")
        
        dados_amostra = df_geral.iloc[0]
        cobertura = dados_amostra["Cobertura (%)"]
        num_gotas = dados_amostra["Nº de Gotas"]
        densidade = dados_amostra["Densidade (gotas/cm²)"]
        dmv = dados_amostra["Dv0.5 / DMV (µm)"]
        span = dados_amostra["Amplitude (SPAN)"]
        cv_espacial_val = dados_amostra["CV da Distribuição (%)"]

        col_dash1, col_dash2, col_dash3, col_dash4 = st.columns(4)
        
        with col_dash1:
            st.metric(label="💧 Diâmetro Mediano (DMV)", value=f"{dmv} µm")
            if dmv < 150: st.caption("⚠️ **Gotas Finas:** Risco de deriva.")
            elif 150 <= dmv <= 300: st.caption("✅ **Gotas Médias:** Ótimo equilíbrio.")
            else: st.caption("⚠️ **Gotas Grossas:** Risco de escorrimento.")

        with col_dash2:
            st.metric(label="📈 Densidade de Gotas", value=f"{densidade} g/cm²")
            if densidade >= 60:
                st.markdown("<span style='color:green; font-weight:bold;'>🟢 DENSIDADE IDEAL</span>", unsafe_allow_html=True)
            else:
                st.markdown("<span style='color:red; font-weight:bold;'>🔴 DENSIDADE BAIXA</span>", unsafe_allow_html=True)

        with col_dash3:
            st.metric(label="🎯 Cobertura do Alvo", value=f"{cobertura} %")
            st.caption("Área total atingida.")

        with col_dash4:
            st.metric(label="🔢 Total de Gotas", value=int(num_gotas))
            st.caption("Contagem absoluta.")

        st.write("")
        col_dash5, col_dash6 = st.columns(2)
        with col_dash5:
            st.info(f"**Uniformidade (SPAN):** {span}\n\n" + ("✨ Homogêneo." if span <= 1.2 else "⚠️ Alta variação."))
        with col_dash6:
            st.info(f"**CV Espacial:** {cv_espacial_val} %\n\n" + ("✨ Cobertura regular." if cv_espacial_val <= 30 else "⚠️ Aplicação irregular."))

        st.write("---")
        with st.expander("🔍 Ver Dados Completos em Tabela (Excel)"):
            st.dataframe(df_geral, use_container_width=True)
            csv_formatado = formatar_csv_br(df_geral)
            st.download_button(label="📥 Baixar Tabela (.CSV Excel)", data=csv_formatado, file_name="dados_gotas.csv", mime="text/csv", use_container_width=True)

    # --- GRÁFICOS ---
    with aba_graficos:
        st.subheader("Análise Gráfica Estatística")
        if nome_arquivo in dados_graficos:
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                st.markdown("**Frequência de Tamanho das Gotas (Histograma)**")
                counts, bins = np.histogram(dados_graficos[nome_arquivo]["diametros"], bins=15)
                df_hist = pd.DataFrame({"Quantidade": counts}, index=bins[:-1].astype(int))
                st.bar_chart(df_hist)
            with col_g2:
                st.markdown("**Distribuição de Classes de Gotas (%)**")
                classes = dados_graficos[nome_arquivo]["classes"]
                df_classes = pd.DataFrame({"Percentual (%)": classes}, index=['Pequenas (<150µm)', 'Médias (150-300µm)', 'Grandes (>300µm)'])
                st.bar_chart(df_classes)

    # --- INSPEÇÃO ---
    with aba_inspecao:
        st.subheader("🔍 Inspeção e Isolamento do Cartão")
        if nome_arquivo in imagens_processadas:
            col_i1, col_i2 = st.columns(2)
            with col_i1:
                st.image(imagens_processadas[nome_arquivo]["original"], caption="Foto de Entrada", use_container_width=True)
            with col_i2:
                st.image(imagens_processadas[nome_arquivo]["analisada"], caption="Área Útil Isolada (Gotas em Verde)", use_container_width=True)

    # --- LAUDO EM PDF ---
    with aba_relatorio:
        st.markdown("## 📋 Laudo de Campo Homologado IAC & Aplique Bem")
        st.markdown("---")
        
        if nome_arquivo in dados_graficos:
            dados_cartao = df_geral.iloc[0]
            dmv_atual = dados_cartao["Dv0.5 / DMV (µm)"]
            densidade_atual = dados_cartao["Densidade (gotas/cm²)"]
            deriva_atual = dados_cartao["Gotas Pequenas (<150µm) %"]
            medias_atual = dados_cartao["Gotas Médias (150-300µm) %"]
            grandes_atual = dados_cartao["Gotas Grandes (>300µm) %"]
            span_atual = dados_cartao["Amplitude (SPAN)"]
            cobertura_atual = dados_cartao["Cobertura (%)"]
            cv_global = dados_cartao["CV da Distribuição (%)"]
            
            classe_gota = "Média" if 150 <= dmv_atual <= 250 else ("Fina" if dmv_atual < 150 else "Grossa")

            st.write("### 💡 Plano de Ação Prático Recomendado")
            rec_deriva = "Risco de Deriva Elevado: Reduza a pressão de pulverização ou use bicos com indução de ar." if deriva_atual > 30 else "Controle de Deriva Eficiente: Nível operacional seguro."
            rec_densidade = "Densidade Insuficiente: Aumente o volume de calda (L/ha) ou adere bicos de maior vazão." if densidade_atual < 60 else "Densidade Excelente: Quantidade ideal para deposição."
            st.warning(f"1. {rec_deriva}\n\n2. {rec_densidade}")

            def gerar_pdf_laudo_grafico(cv_val):
                pdf = FPDF()
                pdf.add_page()
                pdf.set_margins(15, 15, 15)
                pdf.set_fill_color(0, 80, 136)
                pdf.rect(0, 0, 210, 38, 'F')
                pdf.set_font("Arial", "B", 13)
                pdf.set_text_color(255, 255, 255)
                pdf.cell(0, 10, "LAUDO DIGITAL DE QUALIDADE DE APLICACAO", ln=True, align="C")
                pdf.set_font("Arial", "", 9)
                pdf.cell(0, 4, "Parceria Homologada: Instituto Agronomico (IAC) & Programa Aplique Bem", ln=True, align="C")
                pdf.cell(0, 4, f"Documento de Campo - Arquivo Original: {nome_arquivo}", ln=True, align="C")
                pdf.ln(18)
                
                if os.path.exists(CAMINHO_LOGO_IAC):
                    pdf.image(CAMINHO_LOGO_IAC, x=15, y=42, w=22)
                if os.path.exists(CAMINHO_LOGO_APLIQUEBEM):
                    pdf.image(CAMINHO_LOGO_APLIQUEBEM, x=173, y=42, w=22)
                
                pdf.set_y(68)
                pdf.set_text_color(0, 0, 0)
                pdf.set_font("Arial", "B", 11)
                pdf.cell(0, 8, "1. Indicadores de Campo Fundamentais", ln=True)
                pdf.set_font("Arial", "", 10)
                pdf.cell(90, 6, f"- Diametro Mediano Volumetrico (DMV): {dmv_atual} um ({classe_gota})", ln=True)
                pdf.cell(90, 6, f"- Densidade Global Observada: {densidade_atual} gotas/cm2", ln=True)
                pdf.cell(90, 6, f"- Cobertura Real da Area Foliar: {cobertura_atual}%", ln=True)
                pdf.cell(90, 6, f"- Uniformidade Operacional (SPAN): {span_atual}", ln=True)
                pdf.cell(90, 6, f"- Coeficiente de Variacao Espacial: {cv_val}%", ln=True)
                pdf.ln(6)
                
                pdf.set_font("Arial", "B", 11)
                pdf.cell(0, 8, "2. Grafico de Distribuicao do Espectro de Gotas (%)", ln=True)
                pdf.ln(4)
                
                v_classes = [deriva_atual, medias_atual, grandes_atual]
                l_classes = ["Gotas Finas (<150um)", "Gotas Medias (150-300um)", "Gotas Grossas (>300um)"]
                c_barras = [(230, 80, 80), (80, 200, 120), (80, 120, 200)]
                
                iy = pdf.get_y()
                for i in range(3):
                    pdf.set_font("Arial", "", 9)
                    pdf.text(16, iy + (i * 12) + 5, l_classes[i])
                    pdf.set_fill_color(240, 240, 240)
                    pdf.rect(60, iy + (i * 12), 100, 7, 'F')
                    pdf.set_fill_color(*c_barras[i])
                    pdf.rect(60, iy + (i * 12), max(1, int(v_classes[i])), 7, 'F')
                    pdf.text(165, iy + (i * 12) + 5, f"{v_classes[i]}%")
                
                pdf.set_y(iy + 40)
                pdf.set_font("Arial", "B", 11)
                pdf.cell(0, 8, "3. Plano de Acao e Recomendacoes Tecnicas", ln=True)
                pdf.ln(2)
                pdf.set_fill_color(255, 243, 205)
                pdf.set_text_color(102, 77, 3)
                pdf.set_font("Arial", "", 9.5)
                t_laudo = f"Recomendacoes de Campo:\n- {rec_deriva}\n- {rec_densidade}"
                pdf.multi_cell(180, 5, t_laudo, border=1, fill=True)
                pdf.ln(6)
                
                pdf.set_text_color(0, 0, 0)
                pdf.set_font("Arial", "B", 11)
                pdf.cell(0, 8, "4. Amostra Digitalizada do Cartao", ln=True)
                pdf.ln(2)
                
                if nome_arquivo in imagens_processadas:
                    img_f = Image.fromarray(cv2.cvtColor(imagens_processadas[nome_arquivo]["focada_bgr"], cv2.COLOR_BGR2RGB))
                    tmp = "tmp_laudo.jpg"
                    img_f.save(tmp, "JPEG", quality=90)
                    pdf.image(tmp, x=75, y=pdf.get_y(), w=60)
                    if os.path.exists(tmp): os.remove(tmp)

                pdf_out = pdf.output(dest='S')
                return pdf_out.encode('latin1') if isinstance(pdf_out, str) else bytes(pdf_out)

            pdf_b = gerar_pdf_laudo_grafico(cv_global)
            
            st.download_button(
                label="📥 Baixar Laudo de Campo em PDF",
                data=pdf_b,
                file_name=f"Laudo_IAC_{nome_arquivo.split('.')[0]}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
