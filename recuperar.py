import streamlit as st
import requests
import io
from datetime import datetime
import zipfile

def get_complete_history(api_key):
    """
    Obtiene el historial completo de generaciones y lo organiza en versiones a, b, c.
    La función asume que las generaciones se hicieron en secuencias de tres (a, b, c).
    """
    url = "https://api.elevenlabs.io/v1/history"
    headers = {
        "Accept": "application/json",
        "xi-api-key": api_key
    }
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            history = data.get('history', [])
            
            if not history:
                st.warning("No se encontraron generaciones en el historial")
                return None
            
            # Ordenamos del más antiguo al más reciente para mantener el orden correcto
            history.sort(key=lambda x: x.get('created_at', 0))
            
            # Organizamos en versiones a, b, c
            version_a = []
            version_b = []
            version_c = []
            
            # Procesamos en grupos de 3, asumiendo el patrón a, b, c
            for i in range(0, len(history), 3):
                group = history[i:i+3]
                
                # Asignamos cada elemento a su versión correspondiente
                for j, item in enumerate(group):
                    if j == 0:  # Primer elemento del grupo -> versión A
                        version_a.append(item)
                    elif j == 1:  # Segundo elemento -> versión B
                        version_b.append(item)
                    elif j == 2:  # Tercer elemento -> versión C
                        version_c.append(item)
            
            return {
                'a': version_a,
                'b': version_b,
                'c': version_c
            }
            
        st.error(f"Error en la API: {response.status_code}")
        return None
    except Exception as e:
        st.error(f"Error al obtener el historial: {str(e)}")
        return None

def download_audio_from_history(api_key, history_item_id):
    """
    Descarga un audio específico del historial
    """
    url = f"https://api.elevenlabs.io/v1/history/{history_item_id}/audio"
    headers = {
        "Accept": "audio/mpeg",
        "xi-api-key": api_key
    }
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.content
        return None
    except Exception as e:
        st.error(f"Error al descargar audio: {str(e)}")
        return None

def create_version_zip(audio_files):
    """
    Crea un archivo ZIP con los audios, manteniendo el orden numérico
    """
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for i, audio in enumerate(audio_files, 1):
            zip_file.writestr(f"{i}.mp3", audio)
    return zip_buffer.getvalue()

def main():
    st.title("🎙️ Recuperador de Audios de Eleven Labs")
    st.write("Recupera todos tus audios organizados por versiones A, B y C")
    
    api_key = st.text_input("API Key de Eleven Labs", type="password")
    
    if st.button("Recuperar todos los audios"):
        if not api_key:
            st.warning("Por favor ingresa tu API key")
            return
        
        with st.spinner("Recuperando y organizando audios..."):
            # Obtenemos todo el historial organizado por versiones
            versions = get_complete_history(api_key)
            
            if not versions:
                st.warning("No se encontraron audios")
                return
            
            # Procesamos cada versión
            version_contents = {'a': [], 'b': [], 'c': []}
            progress_text = st.empty()
            
            total_items = sum(len(items) for items in versions.values())
            st.info(f"Se encontraron {total_items} audios en total")
            
            progress_bar = st.progress(0)
            items_processed = 0
            
            for version, items in versions.items():
                progress_text.text(f"Descargando versión {version.upper()}...")
                for item in items:
                    audio = download_audio_from_history(api_key, item.get('history_item_id'))
                    if audio:
                        version_contents[version].append(audio)
                    items_processed += 1
                    progress_bar.progress(items_processed / total_items)
            
            # Creamos y ofrecemos la descarga de cada versión
            st.subheader("📥 Descargar archivos")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            col1, col2, col3 = st.columns(3)
            
            if version_contents['a']:
                with col1:
                    st.download_button(
                        "⬇️ Descargar versión A",
                        data=create_version_zip(version_contents['a']),
                        file_name=f"version_A_{timestamp}.zip",
                        mime="application/zip",
                        key="download_a"
                    )
                    st.caption(f"{len(version_contents['a'])} archivos")
            
            if version_contents['b']:
                with col2:
                    st.download_button(
                        "⬇️ Descargar versión B",
                        data=create_version_zip(version_contents['b']),
                        file_name=f"version_B_{timestamp}.zip",
                        mime="application/zip",
                        key="download_b"
                    )
                    st.caption(f"{len(version_contents['b'])} archivos")
            
            if version_contents['c']:
                with col3:
                    st.download_button(
                        "⬇️ Descargar versión C",
                        data=create_version_zip(version_contents['c']),
                        file_name=f"version_C_{timestamp}.zip",
                        mime="application/zip",
                        key="download_c"
                    )
                    st.caption(f"{len(version_contents['c'])} archivos")
            
            st.success(f"""
                Archivos recuperados con éxito:
                - Versión A: {len(version_contents['a'])} archivos
                - Versión B: {len(version_contents['b'])} archivos
                - Versión C: {len(version_contents['c'])} archivos
            """)

if __name__ == "__main__":
    main()
