cat << 'EOF' > ~/Documents/app.py
import streamlit as st
import cv2
import numpy as np
import pandas as pd

st.set_page_config(page_title="Análise de Gotas", page_icon="💧", layout="wide")
st.title("💧 Analisador de Papel Hidrossolúvel")
st.markdown("Carregue as imagens dos papéis (**8cm x 3cm**) para calcular a cobertura, número e tamanho das gotas.")

arquivos_enviados = st.file_uploader("Arraste ou selecione as imagens", type=['jpg', 'jpeg', 'png'], accept_multiple_files=True)

if arquivos_enviados:
    resultados = []
    st.subheader("Processando Imagens...")
    
    for arquivo in arquivos_enviados:
        file_bytes = np.asarray(bytearray(arquivo.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, 1)
        
        altura_px, largura_px = img.shape[:2]
        area_total_pixels = altura_px * largura_px
        mm2_por_pixel = (30.0 * 80.0) / area_total_pixels

        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        azul_baixo = np.array([90, 50, 50])
        azul_alto = np.array([140, 255, 255])
        mascara = cv2.inRange(hsv, azul_baixo, azul_alto)

        contornos, _ = cv2.findContours(mascara, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        gotas_filtradas = [c for c in contornos if cv2.contourArea(c) > 2]

        num_gotas = len(gotas_filtradas)
        pixels_gotas = cv2.countNonZero(mascara)
        porcentagem_cobertura = (pixels_gotas / area_total_pixels) * 100
        
        areas_gotas_mm2 = [cv2.contourArea(c) * mm2_por_pixel for c in gotas_filtradas]
        tamanho_medio_mm2 = np.mean(areas_gotas_mm2) if num_gotas > 0 else 0

        resultados.append({
            "Nome do Arquivo": arquivo.name,
            "Cobertura (%)": round(porcentagem_cobertura, 2),
            "Nº de Gotas": num_gotas,
            "Tam. Médio (mm²)": round(tamanho_medio_mm2, 4)
        })

        img_visualizacao = img.copy()
        cv2.drawContours(img_visualizacao, gotas_filtradas, -1, (0, 255, 0), 2)
        img_visualizacao_rgb = cv2.cvtColor(img_visualizacao, cv2.COLOR_BGR2RGB)

        with st.expander(f"Ver detalhes de: {arquivo.name}"):
            col1, col2 = st.columns(2)
            with col1:
                st.image(arquivo, caption="Imagem Original", use_container_width=True)
            with col2:
                st.image(img_visualizacao_rgb, caption="Gotas Detectadas (Verde)", use_container_width=True)

    st.write("---")
    st.subheader("📊 Tabela de Resultados")
    df = pd.DataFrame(resultados)
    st.dataframe(df, use_container_width=True)

    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button(label="📥 Baixar Resultados em Excel (CSV)", data=csv, file_name="analise_hidrosoluvel.csv", mime="text/csv")
EOF
