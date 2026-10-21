import csv
import telepot
import requests
import json
import re
from bs4 import BeautifulSoup
import time
from datetime import datetime
import streamlit as st

def extraer_articulo(url):
    try:
        # User-Agent para evitar bloqueos de seguridad del servidor
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        r1 = requests.get(url, headers=headers)
        coverpage = r1.content
        soup1 = BeautifulSoup(coverpage, 'html5lib')
        
        # URL original del artículo
        canonical_tag = soup1.find('link', rel='canonical')
        url_articulo = canonical_tag['href'] if canonical_tag else url
        
        # Extracción del Título Principal (H1)
        titulo_tag = soup1.find('h1') or soup1.find('div', class_='ArticleHeader-Title')
        titulo = titulo_tag.get_text(strip=True) if titulo_tag else "Título no encontrado"
        
        # Fecha de publicación
        fecha_tag = soup1.find('div', class_='Article-Date') or soup1.find('span', class_='ee-article-date')
        if fecha_tag:
            fecha = fecha_tag.get_text(strip=True)
        else:
            fecha = datetime.now().strftime("%d-%m-%Y")

        # Autor o Redactor de la nota
        autor_tag = soup1.find('div', class_='Article-Author') or soup1.find('a', class_='Author-Link') or soup1.find('span', class_='ee-article-author')
        autor = autor_tag.get_text(strip=True) if autor_tag else "Redacción El Espectador"

        # Recorrido de navegación / Sección
        seccion_tag = soup1.find('a', class_='Article-Section') or soup1.find('div', class_='Breadcrumb')
        recorrido = seccion_tag.get_text(strip=True) if seccion_tag else "Elespectador.com > Sección General"
        
        # Extracción del Subtítulo o Teaser
        subtitulo_general = ""
        header_tag = soup1.find('div', class_=lambda c: c and 'ArticleHeader' in c)
        if header_tag:
            parrafos_header = header_tag.find_all('p')
            if parrafos_header:
                subtitulo_general = " ".join([p.get_text(strip=True) for p in parrafos_header])

        if not subtitulo_general:
            teaser_tag = soup1.find(class_=lambda c: c and 'teaser' in c) or soup1.find('p', class_='ee-gated-content__teaser')
            if teaser_tag:
                subtitulo_general = teaser_tag.get_text(strip=True)

        # ========================================================
        # NUEVA EXTRACCIÓN PROFUNDA Y RECURSIVA (CAPTURA DESDE EL 1ER PÁRRAFO)
        # ========================================================
        texto_limpio_lista = []
        parrafos_vistos = set()  # Para prevenir que se dupliquen fragmentos de texto
        
        frases_a_omitir = [
            "Para conocer más sobre", "Más contenido:", "Lea también", 
            "En contexto", "Le puede interesar", "Publicidad", 
            "Inicia sesión", "Suscríbete"
        ]

        # 1. Buscar en todo el contenedor principal de forma profunda (recursive=True)
        contenedor_principal = soup1.find('div', class_='entry-content')
        if contenedor_principal:
            # Buscamos de forma recursiva para capturar párrafos ocultos en sub-contenedores o bloques de WP
            for elem in contenedor_principal.find_all(['p', 'h2'], recursive=True):
                # IMPORTANTE: No leemos el texto que está atrapado en la plantilla oculta todavía
                if elem.find_parent('template'):
                    continue
                    
                texto_elemento = elem.get_text(strip=True)
                if texto_elemento and texto_elemento != "El Espectador" and not any(f in texto_elemento for f in frases_a_omitir):
                    if texto_elemento not in parrafos_vistos:
                        texto_limpio_lista.append(texto_elemento)
                        parrafos_vistos.add(texto_elemento)

        # 2. Capturar párrafos ocultos dentro de la plantilla <template> (Paywall)
        template_tag = soup1.find('template', class_='ee-gated-content__more')
        if template_tag:
            html_interno = template_tag.string if template_tag.string else "".join(str(c) for c in template_tag.contents)
            inner_soup = BeautifulSoup(html_interno, 'html5lib')

            for elem in inner_soup.find_all(['p', 'h2'], recursive=True):
                texto_elemento = elem.get_text(strip=True)
                if texto_elemento and texto_elemento != "El Espectador" and not any(f in texto_elemento for f in frases_a_omitir):
                    if texto_elemento not in parrafos_vistos:
                        texto_limpio_lista.append(texto_elemento)
                        parrafos_vistos.add(texto_elemento)

        texto_cuerpo = "\n\n".join(texto_limpio_lista)

        if subtitulo_general and subtitulo_general not in texto_cuerpo:
            texto_final = f"{subtitulo_general}\n\n{texto_cuerpo}"
        else:
            texto_final = texto_cuerpo if texto_cuerpo else subtitulo_general

        # ESTRUCTURACIÓN DEL CONTENIDO COMPLETO CON METADATOS INTEGRADOS PARA EL COPIADO
        contenido_completo_con_metadatos = (
            f"TÍTULO: {titulo}\n"
            f"URL ORIGEN: {url_articulo}\n"
            f"FECHA: {fecha}\n"
            f"AUTOR: {autor}\n"
            f"SECCIÓN: {recorrido}\n"
            f"--------------------------------------------------\n\n"
            f"{texto_final}"
        )

        # Envío opcional a Telegram
        token = '5541258900:AAE0PhrKqTjHMWk3-ZdePgzrgRJiB3hv5CI'
        receiver_id = 582395721
        try:
            bot = telepot.Bot(token)
            if len(contenido_completo_con_metadatos) > 4096:
                for x in range(0, len(contenido_completo_con_metadatos), 4096):
                    bot.sendMessage(receiver_id, contenido_completo_con_metadatos[x:x+4096])
            else:
                bot.sendMessage(receiver_id, contenido_completo_con_metadatos)
        except Exception:
            pass 

        return {
            "texto_final": contenido_completo_con_metadatos,
            "titulo": titulo,
            "subtitulo": subtitulo_general,
            "cuerpo": texto_cuerpo,
            "autor": autor,
            "fecha": fecha,
            "recorrido": recorrido,
            "url": url_articulo
        }

    except Exception as e:
        return {"error": f"Error: {str(e)}"}

# Configuración de la página
st.set_page_config(
    page_title="Extractor de Artículos",
    page_icon="📰",
    layout="wide"
)

# Inicializar estados de sesión obligatorios
if 'mostrar_formulario' not in st.session_state:
    st.session_state.mostrar_formulario = True
if 'resultados' not in st.session_state:
    st.session_state.resultados = None
if 'historial_links' not in st.session_state:
    st.session_state.historial_links = []

def procesar_extraccion(url_directa=None):
    url = url_directa if url_directa else st.session_state.url_input
    
    if url:
        with st.spinner("Extrayendo contenido..."):
            res = extraer_articulo(url)

        if res and "error" not in res:
            st.session_state.resultados = res
            st.session_state.mostrar_formulario = False
            if url not in st.session_state.historial_links:
                st.session_state.historial_links.insert(0, url)
        else:
            st.error(res.get("error", "No se pudo extraer el artículo."))
    else:
        st.warning("Por favor ingresa una URL válida")

def reiniciar():
    st.session_state.mostrar_formulario = True
    st.session_state.resultados = None
    st.rerun()

# Configuración de la barra lateral (Historial de consultas)
st.sidebar.header("📜 Historial de esta Sesión")
if st.session_state.historial_links:
    st.sidebar.caption("Haz clic en cualquier link previo para volver a cargarlo:")
    for link_previo in st.session_state.historial_links:
        nombre_corto = link_previo.replace("https://elespectador.com", "").split("/")[-2] if "/" in link_previo else link_previo[:25]
        if st.sidebar.button(f"🔗 {nombre_corto}", key=f"hist_{link_previo}", help=link_previo):
            with st.spinner("Cargando desde el historial..."):
                res = extraer_articulo(link_previo)
                if res and "error" not in res:
                    st.session_state.resultados = res
                    st.session_state.mostrar_formulario = False
                    st.rerun()
else:
    st.sidebar.info("Aún no has consultado artículos en esta sesión.")

st.sidebar.markdown("---")
st.sidebar.header("Acerca de")
st.sidebar.info("Herramienta optimizada de extracción universal para El Espectador.")

# Título de la App
st.title("📰 Extractor de Artículos de Periódicos")

if st.session_state.mostrar_formulario:
    st.markdown("Ingresa la URL del artículo que deseas extraer")

    st.text_input(
        "URL del artículo",
        key="url_input",
        placeholder="https://elespectador.com...",
        help="Ingresa la URL completa y presiona Enter o haz clic en el botón",
        on_change=lambda: procesar_extraccion()
    )

    st.button("Extraer Artículo", type="primary", on_click=lambda: procesar_extraccion())

elif st.session_state.resultados:
    res = st.session_state.resultados
    
    # 1. BOTÓN SUPERIOR: Permite reiniciar sin bajar la pantalla
    col_top_title, col_top_btn = st.columns([4, 1])
    with col_top_btn:
        st.button("🔄 Extraer otro", key="btn_top_reiniciar", on_click=reiniciar, type="secondary")
    
    # Vista en pantalla limpia de la noticia
    st.header(res['titulo'])
    st.caption(f"🔗 **Link original:** {res['url']}")
    st.caption(f"📌 {res['recorrido']} | ✍️ {res['autor']} | 📅 {res['fecha']}")
    
    if res['subtitulo']:
        st.markdown(f"### *{res['subtitulo']}*")
    
    st.markdown("---")
    st.write(res['cuerpo'])
    st.markdown("---")
    
