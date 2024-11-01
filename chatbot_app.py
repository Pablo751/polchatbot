# chatbot_app.py

import streamlit as st
import openai
import pandas as pd
from typing import Optional, Dict
from openai import OpenAIError

# -------------------------------
# 1. Cargar de Forma Segura la Clave API de OpenAI
# -------------------------------

# Accede al secreto desde la gestión de secretos de Streamlit
openai.api_key = st.secrets["OPENAI_API_KEY"]

# -------------------------------
# 2. Configuración de la Aplicación Streamlit
# -------------------------------

# Configuración de la página
st.set_page_config(
    page_title="💬 Chatbot de Productos",
    page_icon="💬",
    layout="centered",
    initial_sidebar_state="expanded",
)

# Título de la aplicación
st.title("💬 Chatbot de Productos")

# -------------------------------
# 3. Cargar y Cachear los Datos de Productos
# -------------------------------

@st.cache_data
def load_product_data(file_path: str) -> pd.DataFrame:
    """
    Cargar y preprocesar los datos de productos desde un archivo Excel.

    Args:
        file_path (str): Ruta al archivo Excel.

    Returns:
        pd.DataFrame: Datos de productos procesados.
    """
    df = pd.read_excel(file_path)
    # Asegurar que las columnas estén correctamente nombradas
    df.columns = ["Index", "Producto", "Descripción", "Beneficios", "Aplicación", "Recomendaciones de Uso"]
    # Eliminar la primera fila si contiene datos no deseados
    df = df.drop(0).reset_index(drop=True)
    return df

# -------------------------------
# 4. Funciones Auxiliares
# -------------------------------

def get_product_info(product_name: str, data: pd.DataFrame) -> Optional[Dict[str, str]]:
    """
    Recuperar información del producto basado en el nombre del producto.

    Args:
        product_name (str): Nombre del producto a buscar.
        data (pd.DataFrame): DataFrame que contiene la información de los productos.

    Returns:
        Optional[Dict[str, str]]: Diccionario con los detalles del producto si se encuentra, de lo contrario None.
    """
    product_row = data[data['Producto'].str.contains(product_name, case=False, na=False)]
    if not product_row.empty:
        return product_row.iloc[0].to_dict()
    else:
        return None

def generate_chatbot_response(product_info: Dict[str, str], user_question: str) -> str:
    """
    Generar una respuesta del chatbot utilizando la API de OpenAI.

    Args:
        product_info (Dict[str, str]): Información sobre el producto seleccionado.
        user_question (str): La pregunta del usuario.

    Returns:
        str: La respuesta del chatbot.
    """
    # Construir el prompt
    prompt = (
        f"Eres un asistente que ayuda a responder preguntas sobre productos. "
        f"Usa únicamente la siguiente información para tu respuesta en español.\n\n"
        f"**Nombre del Producto**: {product_info['Producto']}\n"
        f"**Descripción**: {product_info['Descripción']}\n"
        f"**Beneficios**: {product_info['Beneficios']}\n"
        f"**Aplicación**: {product_info['Aplicación']}\n"
        f"**Recomendaciones de Uso**: {product_info['Recomendaciones de Uso']}\n\n"
        f"**Pregunta del Usuario**: {user_question}\n"
        f"**Respuesta**:"
    )

    try:
        # Llamar a la API de OpenAI con GPT-4o
        response = openai.ChatCompletion.create(
            model="gpt-4o-2024-08-06",  # Asegúrate de usar el modelo GPT-4o correcto
            messages=[
                {"role": "system", "content": "Eres un asistente útil y responde siempre en español."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,  # Puedes ajustar esto según tus necesidades
            temperature=0.7  # Puedes ajustar la temperatura para más creatividad o precisión
        )
        # Acceder correctamente al contenido de la respuesta
        return response.choices[0].message['content'].strip()
    except openai.OpenAIError as e:
        return f"Ocurrió un error al procesar tu solicitud: {e}"
    except Exception as e:
        return f"Ocurrió un error inesperado: {e}"

# -------------------------------
# 5. Cargar los Datos de Productos
# -------------------------------

# Barra lateral para la carga de archivos
st.sidebar.header("📂 Cargar Datos de Productos")

# Permitir que los usuarios carguen su propio archivo Excel
uploaded_file = st.sidebar.file_uploader("Sube tu archivo Excel de productos:", type=["xlsx", "xls"])

if uploaded_file is not None:
    try:
        product_data = load_product_data(uploaded_file)
        st.sidebar.success("¡Datos de productos cargados exitosamente!")
    except Exception as e:
        st.sidebar.error(f"Error al cargar el archivo: {e}")
        st.stop()
else:
    # Si no se carga un archivo, usar la ruta del archivo por defecto
    default_file_path = 'Matriz_Edificacion.xlsx'  # Asegúrate de que este archivo esté en el mismo directorio que chatbot_app.py
    try:
        product_data = load_product_data(default_file_path)
        st.sidebar.info("Datos de productos por defecto cargados.")
    except FileNotFoundError:
        st.sidebar.error("Archivo de producto por defecto no encontrado. Por favor, sube un archivo Excel.")
        st.stop()
    except Exception as e:
        st.sidebar.error(f"Error al cargar el archivo por defecto: {e}")
        st.stop()

# -------------------------------
# 6. Sección de Interacción del Usuario
# -------------------------------

st.sidebar.header("🤖 Pregunta al Chatbot")

# Selección de producto
product_names = product_data['Producto'].tolist()
selected_product = st.sidebar.selectbox("Selecciona un producto:", product_names)

# Entrada de pregunta del usuario
user_question = st.sidebar.text_input("Ingresa tu pregunta sobre el producto:")

# Inicializar el estado de la sesión para el historial de conversación
if 'conversation' not in st.session_state:
    st.session_state['conversation'] = []

# Botón de envío
if st.sidebar.button("Obtener Respuesta"):
    if not user_question:
        st.sidebar.warning("Por favor, ingresa una pregunta para obtener una respuesta.")
    else:
        with st.spinner("Generando respuesta..."):
            product_info = get_product_info(selected_product, product_data)
            if not product_info:
                st.sidebar.error("Información del producto no encontrada. Por favor, selecciona un producto válido.")
            else:
                answer = generate_chatbot_response(product_info, user_question)
                # Agregar al historial de conversación
                st.session_state['conversation'].append((user_question, answer))
                st.sidebar.success("¡Respuesta generada!")

# Limitar el historial de conversación a las últimas 5 interacciones
MAX_HISTORY = 5
if len(st.session_state['conversation']) > MAX_HISTORY:
    st.session_state['conversation'].pop(0)

# -------------------------------
# 7. Mostrar el Historial de Conversación
# -------------------------------

if st.session_state['conversation']:
    st.header("🗨️ Historial de Conversación")
    for i, (question, answer) in enumerate(st.session_state['conversation'], 1):
        st.markdown(f"**Q{i}:** {question}")
        st.markdown(f"**A{i}:** {answer}")
        st.markdown("---")
