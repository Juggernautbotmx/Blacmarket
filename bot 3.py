import logging
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import requests
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, CallbackContext

# Configura el log para el bot
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Token de tu bot de Telegram (lo obtuviste de BotFather)
TOKEN = '8124172139:AAE__DVaqBn0YEQtscyevki8d44-66SBRPE'
# ID del canal donde enviarás las imágenes (ej. '@mi_canal')
CHANNEL_ID = '-1002049917773'

# Función para añadir la marca de agua (imagen PNG con transparencia)
def add_watermark(image_bytes: BytesIO, watermark_url: str) -> BytesIO:
    # Cargar la imagen original
    image = Image.open(image_bytes).convert("RGBA")  # Convertimos a RGBA para manejar la transparencia

    # Descargar la imagen de la marca de agua desde el enlace
    response = requests.get(watermark_url)

    # Verificar si la respuesta fue exitosa y contiene una imagen
    if response.status_code != 200:
        raise Exception(f"Error al descargar la imagen de la marca de agua. Status code: {response.status_code}")
    
    # Verificar que el contenido es una imagen
    if 'image' not in response.headers['Content-Type']:
        raise Exception("La URL no apunta a una imagen válida.")
    
    try:
        # Intentamos abrir la imagen de la marca de agua
        watermark = Image.open(BytesIO(response.content)).convert("RGBA")  # Convertir la marca de agua a RGBA
    except Exception as e:
        # Si no se puede identificar la imagen, mostramos el error
        raise Exception(f"No se pudo identificar la imagen de la marca de agua: {e}")
    
    # Redimensionar la marca de agua para cubrir toda la imagen
    watermark = watermark.resize(
        (image.width, image.height),
        Image.Resampling.LANCZOS  # Usamos LANCZOS para redimensionar la imagen
    )

    # Ajustar la transparencia de la marca de agua al 50%
    watermark_with_transparency = watermark.copy()
    watermark_with_transparency.putalpha(128)  # 50% de transparencia (128 es la mitad de 255)

    # Pegar la marca de agua sobre la imagen
    image.paste(watermark_with_transparency, (0, 0), watermark_with_transparency)

    # Guardar la imagen con la marca de agua en un buffer
    output = BytesIO()
    image.save(output, format='PNG')
    output.seek(0)

    return output

# Función para manejar el mensaje que contiene la imagen
async def handle_image(update: Update, context: CallbackContext) -> None:
    # Descargar el archivo de la imagen
    photo = update.message.photo[-1]
    file = await photo.get_file()  # Obtener el archivo

    # Crear un buffer para la descarga
    photo_file = BytesIO()
    
    # Usar el método correcto para descargar el archivo en memoria
    await file.download_to_memory(photo_file)  # Descargar el archivo en memoria

    # Obtener la URL de la marca de agua (esta debería ser enviada por el usuario como texto)
    watermark_url = context.user_data.get("watermark_url")
    
    if not watermark_url:
        await context.bot.send_message(chat_id=update.message.chat_id, text="Por favor, proporciona una URL válida para la marca de agua.")
        return

    # Abrir la imagen y añadir la marca de agua
    photo_file.seek(0)  # Asegúrate de que el puntero esté al principio del archivo
    try:
        watermarked_image = add_watermark(photo_file, watermark_url)
    except Exception as e:
        logger.error(f"Error al agregar la marca de agua: {e}")
        await context.bot.send_message(chat_id=update.message.chat_id, text=f"Error al procesar la imagen: {e}")
        return

    # Enviar la imagen con marca de agua al canal
    await context.bot.send_photo(chat_id=CHANNEL_ID, photo=watermarked_image)

# Función para manejar los mensajes de texto que contienen la URL de la marca de agua
async def handle_text(update: Update, context: CallbackContext) -> None:
    # Obtener la URL de la marca de agua desde el mensaje de texto
    watermark_url = update.message.text.strip()  # El usuario envía la URL en texto

    # Validar si la URL es válida
    if not watermark_url:
        await context.bot.send_message(chat_id=update.message.chat_id, text="Por favor, proporciona una URL válida para la marca de agua.")
        return

    # Guardar la URL de la marca de agua en los datos del usuario
    context.user_data["watermark_url"] = watermark_url
    await context.bot.send_message(chat_id=update.message.chat_id, text="¡URL de la marca de agua guardada! Ahora, por favor, envía una imagen para procesarla.")

# Función principal para iniciar el bot
def main() -> None:
    # Crear la aplicación y pasarle el token del bot
    application = Application.builder().token(TOKEN).build()

    # Manejador para recibir imágenes
    application.add_handler(MessageHandler(filters.PHOTO, handle_image))
    
    # Manejador para recibir texto (URL de la marca de agua)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Iniciar el bot
    application.run_polling()

if __name__ == '__main__':
    main()
