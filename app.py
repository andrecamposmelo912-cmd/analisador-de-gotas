import streamlit as st
import cv2
import numpy as np
import pandas as pd
from pillow_heif import register_heif_opener
import io
from PIL import Image
from fpdf import FPDF

# Registra o suporte a arquivos HEIC/HEIF do iPhone
register_heif_opener()

st.set_page_config(page_title="Analise Avancada de Gotas", page_icon="💧", layout="wide")

st.title("💧 Analisador de Gotas Inteligente & Consultivo")
st.markdown("""
Este software realiza a analise completa do espectro de pulverizacao de cartoes hidrossoluveis.
Os dados estatisticos sao traduzidos em **diagnosticos de campo faceis de entender**.
""")

# Configuracoes de calibracao na barra lateral
st.sidebar.header("🛠️ Configuracoes de Calibracao")
fator_espalhamento = st.sidebar.slider("Fator de Espalhameto (Mancha/Real)", min_value=1.0, max_value=3.0, value=2.0, step=0.1, 
                                      help="Fator pelo qual a gota aumenta ao impactar o papel. O padrao e 2.0.")

aba_upload, aba_graficos, aba_inspecao, aba_relatorio = st.tabs([
    "📥 Upload e Resultados", 
    "📊 Graficos do Espectro", 
    "🔍 Inspecao de Cartoes",
    "📋 Relatorio Tecnico Didatico"
])

arquivos_enviados = st.file_uploader("Arraste ou selecione as imagens dos cartoes", type=['jpg', 'jpeg', 'png', 'heic', 'heif'], accept_multiple_files=True)

def formatar_csv_br(df):
    df_br = df.copy()
    for col in df_br.columns:
        if df_br[col].dtype in [np.float64, np.float32]:
            df_br[col] = df_br[col].apply(lambda x: f"{x:.4f}".replace('.', ','))
    return df_br.to_csv(index=False, sep=';').encode('utf-8-sig')

if arquivos_enviados:
    resultados_gerais = []
    dados_graficos = {}
    imagens_processadas = {}
    
    for arquivo in arquivos_enviados:
        nome_arquivo = arquivo.name
        extensao = nome_arquivo.split('.')[-1].lower()
        
        try:
            if extensao in ['heic', 'heif']:
                pil_img = Image.open(arquivo).convert("RGB")
                img_rgb = np.array(pil_img)
                img = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
                _, img_jpeg_bytes = cv2.imencode('.jpg', img)
                arquivo_exibicao = io.BytesIO(img_jpeg_bytes.tobytes())
            else:
                file_bytes = np.asarray(bytearray(arquivo.read()), dtype=np.uint8)
                img = cv2.imdecode(file_bytes, 1)
                arquivo_exibicao = arquivo
        except Exception as e:
            st.error(f"Erro ao processar o arquivo {nome_arquivo}: {e}")
            continue

        if img is None:
            st.error(f"Não foi possível decodificar a imagem: {nome_arquivo}")
            continue
            
        altura_px, largura_px = img.shape[:2]
        area_total_pixels = altura_px * largura_px
        
        largura_mm = 30.0
        altura_mm = 80.0
        area_cartao_cm2 = (largura_mm / 10.0) * (altura_mm / 10.0)
        
        mm_por_pixel = largura_mm / largura_px
        um_por_pixel = mm_por_pixel * 1000.0
        
        # Inteligencia de Cor (Amarelo ou Branco)
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
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
        
        # Contornos das Gotas
        contornos, _ = cv2.findContours(mascara, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        gotas_filtradas = [c for c in contornos if cv2.contourArea(c) > 3]
        num_gotas = len(gotas_filtradas)
        
        pixels_gotas = cv2.countNonZero(mascara)
        porcentagem_cobertura = (pixels_gotas / area_total_pixels) * 100
        densidade_gotas = num_gotas / area_cartao_cm2 if num_gotas > 0 else 0
        
        # Estatisticas de Diametro e Volume
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
            dv05 = float(np.interp(0.5, fracao_acumulada, diametros_ordenados))
            dv09 = float(np.interp(0.9, fracao_acumulada, diametros_ordenados))
            span = (dv09 - dv01) / dv05 if dv05 > 0 else 0
            
            pequenas = np.sum(diametros_reais_um < 150) / num_gotas * 100
            medias = np.sum((diametros_reais_um >= 150) & (diametros_reais_um <= 300)) / num_gotas * 100
            grandes = np.sum(diametros_reais_um > 300) / num_gotas * 100
        else:
            dv01 = dv05 = dv09 = span = pequenas = medias = grandes = 0.0
            
        # CV Espacial
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
                    
        cv_distribuicao = (np.std(contagem_quadrantes) / np.mean(contagem_quadrantes) * 100) if np.mean(contagem_quadrantes) > 0 else 0.0

        resultados_gerais.append({
            "Nome do Arquivo": nome_arquivo, "Tipo Detectado": tipo_cartao, "Cobertura (%)": round(porcentagem_cobertura, 2),
            "Nº de Gotas": num_gotas, "Densidade (gotas/cm²)": round(densidade_gotas, 2), "Dv0.1 (µm)": round(dv01, 1),
            "Dv0.5 / DMV (µm)": round(dv05, 1), "Dv0.9 (µm)": round(dv09, 1), "Amplitude (SPAN)": round(span, 2),
            "Gotas Pequenas (<150µm) %": round(pequenas, 1), "Gotas Médias (150-300µm) %": round(medias, 1), "Gotas Grandes (>300µm) %": round(grandes, 1),
            "CV da Distribuição (%)": round(cv_distribuicao, 2)
        })
        
        dados_graficos[nome_arquivo] = {"diametros": diametros_reais_um, "classes": [pequenas, medias, grandes]}
        
        img_visualizacao = img.copy()
        cv2.drawContours(img_visualizacao, gotas_filtradas, -1, (0, 255, 0), 2)
        imagens_processadas[nome_arquivo] = {
            "original": arquivo_exibicao, "analisada": cv2.cvtColor(img_visualizacao, cv2.COLOR_BGR2RGB), "cv_img": img_visualizacao
        }

    df_geral = pd.DataFrame(resultados_gerais)

    # --- ABA 1: UPLOAD E RESULTADOS ---
    with aba_upload:
        st.subheader("📊 Resumo das Metricas Principais")
        media_dmv = df_geral["Dv0.5 / DMV (µm)"].mean()
        media_densidade = df_geral["Densidade (gotas/cm²)"].mean()
        media_cobertura = df_geral["Cobertura (%)"].mean()
        media_cv = df_geral["CV da Distribuição (%)"].mean()
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("DMV Medio Geral", f"{round(media_dmv, 1)} um")
        
        if media_densidade >= 60:
            st.success(f"Densidade Média: {round(media_densidade, 1)} g/cm²\n\n🟢 Ideal")
        else:
            st.error(f"Densidade Média: {round(media_densidade, 1)} g/cm²\n\n🔴 Baixa")
            
        c3.metric("Cobertura Media", f"{round(media_cobertura, 2)} %")
        c4.metric("CV Espacial Medio", f"{round(media_cv, 1)} %")
        
        st.write("---")
        st.subheader("📋 Tabela Geral de Resultados")
        st.dataframe(df_geral, use_container_width=True)
        
        csv_formatado = formatar_csv_br(df_geral)
        st.download_button(
            label="📥 Baixar Tabela Completa para o Excel (Padrao BR)",
            data=csv_formatado, file_name="analise_espectro_gotas.csv", mime="text/csv"
        )

    # --- ABA 2: GRAFICOS DO ESPECTRO ---
    with aba_graficos:
        st.subheader(" Análise Grafica Estatistica")
        arquivo_selecionado = st.selectbox("Selecione o cartão para ver os gráficos:", list(dados_graficos.keys()))
        if arquivo_selecionado:
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                st.markdown("**Frequencia de Tamanho das Gotas (Histograma Nativo)**")
                counts, bins = np.histogram(dados_graficos[arquivo_selecionado]["diametros"], bins=15)
                df_hist_nativo = pd.DataFrame({"Quantidade": counts}, index=bins[:-1].astype(int))
                st.bar_chart(df_hist_nativo)
                
            with col_g2:
                st.markdown("**Distribuicao de Classes de Gotas (%)**")
                classes = dados_graficos[arquivo_selecionado]["classes"]
                df_classes_nativo = pd.DataFrame({
                    "Percentual (%)": classes
                }, index=['Pequenas (<150um)', 'Medias (150-300um)', 'Grandes (>300um)'])
                st.bar_chart(df_classes_nativo)

    # --- ABA 3: INSPECAO DE CARTOES ---
    with aba_inspecao:
        st.subheader("🔍 Inspecao Individual de Cartoes")
        for nome_foto, imgs in imagens_processadas.items():
            with st.expander(f"Cartão: {nome_foto}"):
                col_i1, col_i2 = st.columns(2)
                with col_i1:
                    st.image(imgs["original"], caption="Imagem Original", use_container_width=True)
                with col_i2:
                    st.image(imgs["analisada"], caption="Gotas Detectadas em Verde", use_container_width=True)

    # --- ABA 4: RELATORIO TECNICO DIDATICO ---
    with aba_relatorio:
        st.markdown("## 📋 Laudo de Campo e Recomendacoes de Pulverizacao")
        st.markdown("---")
        
        cartao_relatorio = st.selectbox(
            "Selecione o cartão para gerar o Laudo:", 
            list(dados_graficos.keys()), 
            key="rel_select"
        )
        
        if cartao_relatorio:
            dados_cartao = df_geral[df_geral["Nome do Arquivo"] == cartao_relatorio].iloc[0]
            
            dmv_atual = dados_cartao["Dv0.5 / DMV (µm)"]
            densidade_atual = dados_cartao["Densidade (gotas/cm²)"]
            deriva_atual = dados_cartao["Gotas Pequenas (<150µm) %"]
            span_atual = dados_cartao["Amplitude (SPAN)"]
            cobertura_atual = dados_cartao["Cobertura (%)"]
            
            # Classificacao do DMV
            if dmv_atual < 100:
                classe_gota = "Muito Fina"
                interpretacao_dmv = "Risco critico de evaporacao e perda de produto antes de tocar o alvo."
            elif 100 <= dmv_atual < 150:
                classe_gota = "Fina"
                interpretacao_dmv = "Alta penetracao na cultura, mas exige atencao redobrada ao vento."
            elif 150 <= dmv_atual <= 250:
                classe_gota = "Media"
                interpretacao_dmv = "Excelente equilibrio. Tamanho ideal para a maioria dos Fungicidas e Inseticidas."
            elif 250 < dmv_atual <= 350:
                classe_gota = "Grossa"
                interpretacao_dmv = "Ideal para Herbicidas Sistemicos. Baixo risco de deriva e boa translocacao."
            else:
                classe_gota = "Muito Grossa"
                interpretacao_dmv = "Risco elevado de escorrimento do produto nas folhas."

            # Exibicao dos Blocos Informativos Nativos
            st.markdown(f"### Diagnóstico do Cartão: {cartao_relatorio}")
            
            col_card1, col_card2, col_card3 = st.columns(3)
            with col_card1:
                st.metric(label="📊 Tamanho Medio da Gota (DMV)", value=f"{dmv_atual} um", delta=f"Classe: {classe_gota}", delta_color="off")
                st.caption(f"Analise: {interpretacao_dmv}")
                
            with col_card2:
                if densidade_atual >= 60:
                    st.success(f"Densidade: {densidade_atual} gotas/cm²\n\n🟢 Ideal para cobertura.")
                else:
                    st.error(f"Densidade: {densidade_atual} gotas/cm²\n\n🔴 Baixa densidade no alvo.")
                    
            with col_card3:
                if deriva_atual > 30:
                    st.error(f"Potencial de Deriva: {deriva_atual}%\n\n🔴 Alto Risco de perda.")
                else:
                    st.success(f"Potencial de Deriva: {deriva_atual}%\n\n🟢 Seguro contra deriva.")

            st.write("")
            col_card4, col_card5 = st.columns(2)
            with col_card4:
                st.info(f"Uniformidade (SPAN): {span_atual}\n\n" + 
                        ("Espectro homogeneo." if span_atual <= 1.2 else "Alta variacao de tamanhos."))
            with col_card5:
                st.info(f"Cobertura Real da Calda: {cobertura_atual}% do cartao atingido.")

            # Recomendacoes
            if deriva_atual > 30:
                rec_deriva = "Risco de Deriva Elevado: Reduza ligeiramente a pressao ou use bicos com inducao de ar."
            else:
                rec_deriva = "Controle de Deriva Eficiente: Os parametros operacionais estao seguros."
                
            if densidade_atual < 60:
                rec_densidade = "Densidade Insuficiente: Considere aumentar o volume de calda (L/ha) ou verificar bicos."
            else:
                rec_densidade = "Densidade Excelente: Quantidade de gotas ideal para deposicao foliar."

            st.write("---")
            st.markdown("### 💡 Plano de Ação Recomendado")
            st.warning(f"""
            Orizentacoes praticas para o operador:
            1. {rec_deriva}
            2. {rec_densidade}
            """)

            # --- ENGINE CORRIGIDA DE GERACAO DO PDF (FPDF2) ---
            def gerar_pdf_laudo():
                pdf = FPDF()
                pdf.add_page()
                pdf.set_margins(15, 15, 15)
                
                # Cabeçalho
                pdf.set_fill_color(31, 119, 180)
                pdf.rect(0, 0, 210, 35, 'F')
                
                pdf.set_font("Arial", "B", 16)
                pdf.set_text_color(255, 255, 255)
                pdf.cell(0, 10, "LAUDO DE AVALIACAO DA QUALIDADE DE APLICACAO", ln=True, align="C")
                pdf.set_font("Arial", "", 10)
                pdf.cell(0, 5, f"Amostra: {cartao_relatorio}", ln=True, align="C")
                pdf.ln(15)
                
                # Tabela
                pdf.set_text_color(0, 0, 0)
                pdf.set_font("Arial", "B", 12)
                pdf.cell(0, 10, "1. Resultados do Espectro", ln=True)
                pdf.ln(2)
                
                pdf.set_fill_color(230, 230, 230)
                pdf.set_font("Arial", "B", 10)
                pdf.cell(50, 8, "Parametro", border=1, fill=True)
                pdf.cell(35, 8, "Valor", border=1, fill=True, align="C")
                pdf.cell(95, 8, "Interpretacao Pratica", border=1, fill=True)
                pdf.ln()
                
                pdf.set_font("Arial", "", 10)
                pdf.cell(50, 8, "DMV", border=1)
                pdf.cell(35, 8, f"{dmv_atual} um", border=1, align="C")
                pdf.cell(95, 8, f"Classe: {classe_gota}", border=1)
                pdf.ln()
                
                pdf.cell(50, 8, "Densidade", border=1)
                pdf.cell(35, 8, f"{densidade_atual} g/cm2", border=1, align="C")
                pdf.cell(95, 8, "Adequada" if densidade_atual >= 60 else "Baixa densidade", border=1)
                pdf.ln()
                
                pdf.cell(50, 8, "Deriva", border=1)
                pdf.cell(35, 8, f"{deriva_atual}%", border=1, align="C")
                pdf.cell(95, 8, "Risco de Deriva Elevado" if deriva_atual > 30 else "Nivel Seguro", border=1)
                pdf.ln()
                
                pdf.cell(50, 8, "Cobertura", border=1)
                pdf.cell(35, 8, f"{cobertura_atual}%", border=1, align="C")
                pdf.cell(95, 8, "Area coberta no papel", border=1)
                pdf.ln(15)
                
                # Recomendacoes
                pdf.set_font("Arial", "B", 12)
                pdf.cell(0, 10, "2. Plano de Acao", ln=True)
                pdf.ln(2)
                
                pdf.set_fill_color(255, 243, 205)
                pdf.set_text_color(102, 77, 3)
                pdf.set_font("Arial", "", 10)
                
                texto_pdf = f"Recomendacoes de Campo:\n\n- {rec_deriva}\n\n- {rec_densidade}"
                pdf.multi_cell(180, 6, texto_pdf, border=1, fill=True)
                
                # CORREÇÃO CIRÚRGICA: Força a saída para string de bytes bruta latente ('S')
                # e faz o cast definitivo para bytes aceitos pelo Streamlit
                pdf_output_str = pdf.output(dest='S')
                if isinstance(pdf_output_str, str):
                    return pdf_output_str.encode('latin1')
                return bytes(pdf_output_str)

            # Executa a função e obtém a sequência limpa de bytes
            pdf_bytes = gerar_pdf_laudo()
            
            st.write("")
            st.download_button(
                label="📥 Baixar Laudo de Campo em PDF",
                data=pdf_bytes,
                file_name=f"Laudo_Tecnico_{cartao_relatorio.split('.')[0]}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
