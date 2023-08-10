
import telegram
from telegram import Update
from telegram.ext import Updater, MessageHandler, Filters, CallbackContext
import dropbox
from dropbox.exceptions import AuthError
import time
import uuid
import os
from requests.auth import HTTPBasicAuth
import requests


app_key = "ggxoww23zilygpi"
app_secret = "f8j90kgorkpypk1"
refresh_token = "S8LrOmLPY-4AAAAAAAAAAaxvLp3twlsgCOBh51auwiSWhRIZyFn90RkXOJDIl4Jw"
data = {'refresh_token': refresh_token, 'grant_type': 'refresh_token'}

def refresh_access_token(updater: Updater):
    r = requests.post('https://api.dropbox.com/oauth2/token', data=data,
                      auth=HTTPBasicAuth(app_key, app_secret))
    result = r.json()
    new_access_token = result["access_token"]
    expiration_time = result["expires_in"]

    # Update the Dropbox client with the new access token
    global dropbox_client, token_expiration, access_token
    access_token = new_access_token
    dropbox_client = dropbox.Dropbox(access_token)
    token_expiration = time.time() + expiration_time

    # Reschedule the token refresh job
    setup_token_refresh(updater)

def setup_token_refresh(updater: Updater):
    job_queue = updater.job_queue

    # Calculate the time interval until the access token expires
    current_time = time.time()
    time_until_expiration = token_expiration - current_time

    # Schedule the refresh_access_token function to run when the token expires
    job_queue.run_once(lambda context: refresh_access_token(context.job.context), time_until_expiration, context=updater)


bot_token = "6035302009:AAEzwtRNL8QgE7WkzxtXTvWqXcGzgifaoZo"
bot = telegram.Bot(token=bot_token)

# Dropbox Setup
access_token = ""
dropbox_client = None
dropbox_folder = "/aftabnet"  # Adjust the folder path as needed
token_expiration = 0

def receive_file(update: Update, context: CallbackContext):
    if update.message.document:
        # Handling document file
        file = context.bot.get_file(update.message.document.file_id)
        file_extension = update.message.document.file_name.split('.')[-1]
    elif update.message.photo:
        # Handling photo image
        file = context.bot.get_file(update.message.photo[-1].file_id)
        file_extension = os.path.splitext(file.file_path)[1][1:]  # Extract file extension
    elif update.message.video:
        # Handling video file
        file = context.bot.get_file(update.message.video.file_id)
        file_extension = os.path.splitext(file.file_path)[1][1:]  # Extract file extension

    # Generate a unique file name with timestamp
    timestamp = int(time.time())
    unique_filename = f"{timestamp}_{str(uuid.uuid4())}.{file_extension}"

    try:
        # Download the file as bytes
        file_data = file.download_as_bytearray()

        # Convert bytearray to bytes
        file_bytes = bytes(file_data)

        # Upload the file to Dropbox
        dropbox_path = f"{dropbox_folder}/{unique_filename}"
        dropbox_client.files_upload(file_bytes, dropbox_path)

        context.bot.send_message(chat_id=update.effective_chat.id, text="File uploaded successfully.")
    except AuthError:
        context.bot.send_message(chat_id=update.effective_chat.id, text="Dropbox authentication error.")
    except Exception as e:
        context.bot.send_message(chat_id=update.effective_chat.id, text=f"Error uploading file: {str(e)}")

def main():
    global access_token, dropbox_client, token_expiration
    updater = Updater(token=bot_token, use_context=True)
    dispatcher = updater.dispatcher

    file_handler = MessageHandler(Filters.document | Filters.photo | Filters.video, receive_file)
    dispatcher.add_handler(file_handler)

    # Initial access token
    refresh_access_token(updater)

    updater.start_polling()

    while True:
        try:
            time.sleep(10)  # Pause the loop for 10 seconds
        except KeyboardInterrupt:
            updater.stop()
            break


if __name__ == '__main__':
    main()

