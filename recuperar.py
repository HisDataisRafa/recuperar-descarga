import streamlit as st
import requests
import io
from datetime import datetime, timedelta
import zipfile

def get_recent_history(api_key, hours_ago=1):
    """
    Obtiene el historial reciente de generaciones de Eleven Labs y lo organiza en secuencias ABC.
    La función asume que las generaciones se hicieron en orden: a, b, c, a, b, c, ...
    """
    url = "https://api.elevenlabs.io/v1/history"
    headers = {
        "Accept": "application/json",
        "xi-api-key": api_key
    }
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            # Obtenemos el historial y lo ordenamos por fecha (más reciente primero)
            history = response.json().get('history', [])
            history.sort(key=lambda x: x['date'], reverse=True)
            
            # Filtramos por tiempo
            current_time = datetime.utcnow()
            recent_items = []
            
            for item in history:
                item_time = datetime.fromisoformat(item['date'].replace('Z', '+00:00'))
                if current_time - item_time <= timedelta(hours=hours_ago):
                    recent_items.append(item)
                else:
                    # Como están ordenados por fecha, podemos romper el ciclo
                    break
            
            # Organizamos en grupos de tres (a, b, c)
            version_a = []
            version_b = []
            version_c = []
            
            # Como el historial está ordenado del más reciente al más antiguo,
            # necesitamos procesar en grupos de 3 en orden inverso
            for i in range(0, len(recent_items), 3):
                group = recent_items[i:i+3]
                # Revertimos el grupo para mantener el orden a, b, c
                group.reverse()
                
                # Asignamos cada item a su versión correspondiente
                for j, item in enumerate(group):
                    if j == 0:
                        version_a.append(item)
                    elif j == 1:
                        version_b.append(item)
                    elif j == 2:
                        version_c.append(item)
            
            return {
                'a': version_a,
                'b': version_b,
                'c': version_c
            }
        
        st.error(f"Error en la respuesta de la API: {response.status_code}")
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
    Crea un archivo ZIP con los audios, manteniendo el orden correcto
    """
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for i, audio in enumerate(audio_files, 1):
            zip_file.writestr(f"{i}.mp3", audio)
    return zip_buffer.getvalue()

def main():
    st.title("🎙️ Recuperador de Audios de Eleven Labs")
    st.write("Recupera tus archivos de audio recientes organizados por versiones A, B y C")
    
    api_key = st.text_input("API Key de Eleven Labs", type="password")
    hours = st.number_input("Recuperar audios de las últimas X horas", 
                           min_value=1, 
                           max_value=24, 
                           value=1)
    
    if st.button("Recuperar audios"):
        if not api_key:
            st.warning("Por favor ingresa tu API key")
            return
        
        with st.spinner("Buscando y organizando audios recientes..."):
            # Obtenemos el historial organizado por versiones
            versions = get_recent_history(api_key, hours)
            
            if not versions:
                st.warning("No se encontraron audios en el período especificado")
                return
            
            # Verificamos si hay elementos en cada versión
            if not any(versions.values()):
                st.warning("No se encontraron secuencias completas de audio")
                return
            
            # Procesamos cada versión
            version_contents = {'a': [], 'b': [], 'c': []}
            progress_text = st.empty()
            
            for version, items in versions.items():
                progress_text.text(f"Descargando versión {version.upper()}...")
                for item in items:
                    audio = download_audio_from_history(api_key, item['history_item_id'])
                    if audio:
                        version_contents[version].append(audio)
            
            # Creamos y ofrecemos la descarga de cada versión
            st.subheader("📥 Descargar archivos")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            col1, col2, col3 = st.columns(3)
            
            if version_contents['a']:
                with col1:
                    st.download_button(
                        "⬇️ Descargar versión A",
                        data=create_version_zip(version_contents['a']),
                        file_name=f"recovered_versionA_{timestamp}.zip",
                        mime="application/zip",
                        key="download_a"
                    )
                    st.caption(f"{len(version_contents['a'])} archivos")
            
            if version_contents['b']:
                with col2:
                    st.download_button(
                        "⬇️ Descargar versión B",
                        data=create_version_zip(version_contents['b']),
                        file_name=f"recovered_versionB_{timestamp}.zip",
                        mime="application/zip",
                        key="download_b"
                    )
                    st.caption(f"{len(version_contents['b'])} archivos")
            
            if version_contents['c']:
                with col3:
                    st.download_button(
                        "⬇️ Descargar versión C",
                        data=create_version_zip(version_contents['c']),
                        file_name=f"recovered_versionC_{timestamp}.zip",
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
