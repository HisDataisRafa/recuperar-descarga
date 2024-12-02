import streamlit as st
import requests
import io
from datetime import datetime, timedelta
import zipfile

def get_recent_history(api_key, hours_ago=1):
    """
    Obtiene el historial reciente de generaciones de Eleven Labs
    """
    url = "https://api.elevenlabs.io/v1/history"
    headers = {
        "Accept": "application/json",
        "xi-api-key": api_key
    }
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            history = response.json().get('history', [])
            
            # Filtrar por tiempo reciente
            current_time = datetime.utcnow()
            recent_items = []
            
            for item in history:
                item_time = datetime.fromisoformat(item['date'].replace('Z', '+00:00'))
                if current_time - item_time <= timedelta(hours=hours_ago):
                    recent_items.append(item)
            
            return recent_items
        return []
    except Exception as e:
        st.error(f"Error al obtener el historial: {str(e)}")
        return []

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

def create_version_zip(audio_files, version):
    """
    Crea un archivo ZIP para una versión específica
    """
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for i, audio in enumerate(audio_files, 1):
            zip_file.writestr(f"{i}.mp3", audio)
    return zip_buffer.getvalue()

def recover_audio_files():
    st.title("🔄 Recuperador de Audios de Eleven Labs")
    st.write("Recupera tus archivos de audio recientes aunque la interfaz se haya reiniciado")
    
    api_key = st.text_input("API Key de Eleven Labs", type="password")
    hours = st.number_input("Recuperar audios de las últimas X horas", 
                           min_value=1, 
                           max_value=24, 
                           value=1)
    
    if st.button("Buscar audios recientes"):
        if not api_key:
            st.warning("Por favor ingresa tu API key")
            return
            
        with st.spinner("Buscando audios recientes..."):
            recent_history = get_recent_history(api_key, hours)
            
            if not recent_history:
                st.warning("No se encontraron audios recientes")
                return
            
            # Agrupar por conjuntos de tres (a, b, c)
            grouped_items = {}
            for item in recent_history:
                # Extraer el número de fragmento del texto
                text_start = item.get('text', '')[:50]  # Primeros 50 caracteres para identificar
                if text_start not in grouped_items:
                    grouped_items[text_start] = []
                grouped_items[text_start].append(item)
            
            # Procesar cada grupo
            version_a = []
            version_b = []
            version_c = []
            
            with st.status("Descargando audios...") as status:
                total_groups = len(grouped_items)
                for i, (text, items) in enumerate(grouped_items.items()):
                    status.update(label=f"Procesando grupo {i+1} de {total_groups}")
                    
                    # Ordenar por fecha para mantener el orden a, b, c
                    items.sort(key=lambda x: x['date'])
                    
                    for j, item in enumerate(items[:3]):  # Tomar solo los primeros 3 de cada grupo
                        audio = download_audio_from_history(api_key, item['history_item_id'])
                        if audio:
                            if j == 0:
                                version_a.append(audio)
                            elif j == 1:
                                version_b.append(audio)
                            else:
                                version_c.append(audio)
            
            # Crear los ZIPs
            if version_a or version_b or version_c:
                st.success("¡Audios recuperados con éxito!")
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                col1, col2, col3 = st.columns(3)
                
                if version_a:
                    with col1:
                        zip_a = create_version_zip(version_a, 'a')
                        st.download_button(
                            "⬇️ Descargar versión A",
                            data=zip_a,
                            file_name=f"recovered_versionA_{timestamp}.zip",
                            mime="application/zip",
                            key="download_recovered_a"
                        )
                
                if version_b:
                    with col2:
                        zip_b = create_version_zip(version_b, 'b')
                        st.download_button(
                            "⬇️ Descargar versión B",
                            data=zip_b,
                            file_name=f"recovered_versionB_{timestamp}.zip",
                            mime="application/zip",
                            key="download_recovered_b"
                        )
                
                if version_c:
                    with col3:
                        zip_c = create_version_zip(version_c, 'c')
                        st.download_button(
                            "⬇️ Descargar versión C",
                            data=zip_c,
                            file_name=f"recovered_versionC_{timestamp}.zip",
                            mime="application/zip",
                            key="download_recovered_c"
                        )

if __name__ == "__main__":
    recover_audio_files()
