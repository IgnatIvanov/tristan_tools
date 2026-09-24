import mimetypes
import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ==================== НАСТРОЙКИ ====================
# https://drive.google.com/drive/folders/1NHs1AIwbexyHiXUqL314xgY27amQjdlr?usp=sharing
GOOGLE_ROOT_ID = "1LPQ_o2J7eIUhxoa0aytAPWsV0catPQ2A"  # ID папки на Google Диске
# GOOGLE_ROOT_ID = "1NHs1AIwbexyHiXUqL314xgY27amQjdlr"  # ID папки на Google Диске
# CLIENT_SECRET_FILE  = os.path.join('.', 'google', 'oauth_creds.json')
CLIENT_SECRET_FILE  = os.path.join('services', 'google', 'access', 'oauth_creds.json')
TOKEN_FILE = "services/google/access/token.json"  # Сюда скрипт сам сохранит токен доступа

SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets",  # Доступ к таблицам
        "https://www.googleapis.com/auth/drive",  # Доступ к файлам Диска
    ]
# ===================================================


def get_drive_service():
    """Авторизация от имени вашего ЛИЧНОГО аккаунта (решает проблему квоты)"""
    creds = None
    # Если токен уже существует, берем его
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    # Если токена нет или он устарел, создаем новый/обновляем
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Этот блок сработает ОДИН РАЗ, открыв браузер для авторизации
            flow = InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRET_FILE, SCOPES
            )
            creds = flow.run_local_server(port=0)

        # Сохраняем токен для последующих автоматических запусков на сервере
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    return build("drive", "v3", credentials=creds)


def get_items_in_folder(service, folder_id):
    query = f"'{folder_id}' in parents and trashed = false"
    results = (
        service.files()
        .list(q=query, fields="files(id, name, mimeType)")
        .execute()
    )
    return {
        f["name"]: {"id": f["id"], "mimeType": f["mimeType"]}
        for f in results.get("files", [])
    }


def create_remote_folder(service, name, parent_id):
    file_metadata = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id],
    }
    folder = (
        service.files().create(body=file_metadata, fields="id").execute()
    )
    return folder.get("id")


def sync_directory(service, local_dir, remote_folder_id):
    print(f"\n-- Синхронизация папки: {local_dir}")
    remote_items = get_items_in_folder(service, remote_folder_id)

    local_items = os.listdir(local_dir)
    local_files = [
        f for f in local_items if os.path.isfile(os.path.join(local_dir, f))
    ]
    local_subdirs = [
        d for d in local_items if os.path.isdir(os.path.join(local_dir, d))
    ]

    # Удаление старого
    for remote_name, info in remote_items.items():
        is_folder = info["mimeType"] == "application/vnd.google-apps.folder"
        if is_folder and (remote_name not in local_subdirs):
            print(f"-- Удаление папки с Диска: {remote_name}")
            service.files().delete(fileId=info["id"]).execute()
        elif not is_folder and (remote_name not in local_files):
            print(f"-- Удаление файла с Диска: {remote_name}")
            service.files().delete(fileId=info["id"]).execute()

    # Загрузка/Обновление файлов
    for file_name in local_files:
        local_path = os.path.join(local_dir, file_name)
        mime_type, _ = mimetypes.guess_type(local_path)
        if not mime_type:
            mime_type = "application/octet-stream"

        media = MediaFileUpload(local_path, mimetype=mime_type, resumable=True)

        if (
            file_name in remote_items
            and remote_items[file_name]["mimeType"]
            != "application/vnd.google-apps.folder"
        ):
            file_id = remote_items[file_name]["id"]
            print(f"-- Обновление файла: {file_name}")
            service.files().update(fileId=file_id, media_body=media).execute()
        else:
            print(f"-- Загрузка нового файла: {file_name}")
            file_metadata = {"name": file_name, "parents": [remote_folder_id]}
            service.files().create(body=file_metadata, media_body=media).execute()

    # Синхронизация подпапок
    for subdir_name in local_subdirs:
        local_subdir_path = os.path.join(local_dir, subdir_name)

        if (
            subdir_name in remote_items
            and remote_items[subdir_name]["mimeType"]
            == "application/vnd.google-apps.folder"
        ):
            subdir_remote_id = remote_items[subdir_name]["id"]
        else:
            print(f"-- Создание папки в облаке: {subdir_name}")
            subdir_remote_id = create_remote_folder(
                service, subdir_name, remote_folder_id
            )

        sync_directory(service, local_subdir_path, subdir_remote_id)

def main():
    # Синхронизация содержимого папки с папкой в google drive
    src_dir = os.path.join('documents_out', 'google_drive_out', 'dolphin_1')
    if not os.path.exists(src_dir):
        print(f"Указанный локальный путь {src_dir} не найден!")
        return

    print("\n-- Запуск процесса зеркалирования с подпапками (OAuth2)...")
    service = get_drive_service()

    try:
        sync_directory(service, src_dir, GOOGLE_ROOT_ID)
        print("\n-- Зеркалирование структуры папок успешно завершено!")
    except Exception as e:
        print(f"\n-- Критическая ошибка во время выполнения: {e}")



if __name__ == "__main__":
    main()
    