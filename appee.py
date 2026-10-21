import streamlit as st
import csv
import telepot
import requests
import json
import re
from bs4 import BeautifulSoup
import time
from datetime import datetime
import streamlit.components.v1 as components  # Requerido para el botón de copiado rápido inteligente

def extraer_articulo(url):
    try:
        # User-Agent para evitar bloqueos del servidor
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

        # Extracción y limpieza del cuerpo
        texto_limpio_lista = []
        template_tag = soup1.find('template', class_='ee-gated-content__more')

        if template_tag:
            html_interno = template_tag.string if template_tag.string else "".join(str(c) for c in template_tag.contents)
            inner_soup = BeautifulSoup(html_interno, 'html5lib')

            for elem in inner_soup.find_all(['p', 'h2']):
                texto_elemento = elem.get_text(strip=True)

                frases_a_omitir = [
                    "Para conocer más sobre", "Más contenido:", "Lea también", 
                    "En contexto", "Le puede interesar", "Publicidad", 
                    "Inicia sesión", "Suscríbete"
                ]

                if texto_elemento == "El Espectador" or any(frase in texto_elemento for frase in frases_a_omitir):
                    continue

                if texto_elemento:
                    texto_limpio_lista.append(texto_elemento)

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

if 'mostrar_formulario' not in st.session_state:
    st.session_state.mostrar_formulario = True
if 'resultados' not in st.session_state:
    st.session_state.resultados = None

def procesar_extraccion():
    url = st.session_state.url_input
    if url:
        with st.spinner("Extrayendo contenido..."):
            res = extraer_articulo(url)

        if res and "error" not in res:
            st.session_state.resultados = res
            st.session_state.mostrar_formulario = False
        else:
            st.error(res.get("error", "No se pudo extraer el artículo."))
    else:
        st.warning("Por favor ingresa una URL válida")

def reiniciar():
    st.session_state.mostrar_formulario = True
    st.session_state.resultados = None
    st.rerun()

st.title("📰 Extractor de Artículos de Periódicos")

if st.session_state.mostrar_formulario:
    st.markdown("Ingresa la URL del artículo que deseas extraer")

    st.text_input(
        "URL del artículo",
        key="url_input",
        placeholder="https://elespectador.com...",
        help="Ingresa la URL completa y presiona Enter o haz clic en el botón",
        on_change=procesar_extraccion
    )

    st.button("Extraer Artículo", type="primary", on_click=procesar_extraccion)

elif st.session_state.resultados:
    res = st.session_state.resultados
    
    # Vista en pantalla limpia y ordenada del título y metadatos
    st.header(res['titulo'])
    st.caption(f"🔗 **Link original:** {res['url']}")
    st.caption(f"📌 {res['recorrido']} | ✍️ {res['autor']} | 📅 {res['fecha']}")
    
    if res['subtitulo']:
        st.markdown(f"### *{res['subtitulo']}*")
    
    st.markdown("---")
    st.write(res['cuerpo'])
    st.markdown("---")
    
    st.subheader("📋 Acciones del Artículo")

    # BOTÓN DE COPIADO INVISIBLE (HTML/JS): Copia todo el bloque con metadatos sin mostrar el cuadro plano en Streamlit
    texto_a_copiar_json = json.dumps(res['texto_final'])
    
    html_boton_copiar = f"""
    <button id="copy-btn" style="
        background-color: #24a0ed;
        color: white;
        border: none;
        padding: 10px 20px;
        font-size: 16px;
        border-radius: 5px;
        cursor: pointer;
        font-weight: bold;
        width: 100%;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    ">📋 Copiar Artículo Completo (Con Metadatos)</button>

    <script>
    document.getElementById('copy-btn').addEventListener('click', function() {{
        const textToCopy = {texto_a_copiar_json};
        navigator.clipboard.writeText(textToCopy).then(function() {{
            const btn = document.getElementById('copy-btn');
            btn.style.backgroundColor = #4CAF50;
            btn.innerText = '¡Copiado con Éxito!';
            setTimeout(function() {{
                btn.style.backgroundColor = '#24a0ed';
                btn.innerText = '📋 Copiar Artículo Completo (Con Metadatos)';
            }}, 2000);
        }}).catch(function(err) {{
            alert('No se pudo copiar el texto de forma automática.');
        }});
    }});
    </script>
    """
    
    # Renderizar el botón flotante nativo de transferencia limpia
    components.html(html_boton_copiar, height=60)

    # Bloque de controles inferiores
    col1, col2 = st.columns(2)

    with col1:
        st.download_button(
            label="💾 Descargar como archivo .txt",
            data=res['texto_final'],
            file_name=f"articulo_{datetime.now().strftime('%d_%m_%H%M')}.txt",
            mime="text/plain"
        )

    with col2:
        st.button("🔄 Extraer otro artículo", on_click=reiniciar)

# Sidebar
st.sidebar.header("Acerca de")
st.sidebar.info("Herramienta optimizada de extracción universal para El Espectador.")


