import os
import sys
import urllib.request
import shutil
import subprocess

def check_and_download_file(url, file_path):
    """ Kiểm tra tệp có tồn tại không và tải tệp xuống """
    if not os.path.exists(file_path):
        print(f"Tệp {file_path} không tồn tại, đang tải tệp xuống...\n")
        try:
            urllib.request.urlretrieve(url, file_path)
        except Exception as e:
            print(f"Lỗi khi tải tệp: {e}")
            sys.exit(1)
    else:
        print(f"Tệp {file_path} đã tồn tại, không cần tải xuống.")

def copy_file_folder(source_path, destination_path):
    """ Copy file, folder """

    # Nếu destination_path không tồn tại, tạo thư mục
    if not os.path.exists(destination_path):
        os.makedirs(destination_path)

    # Nếu source_path là file
    if os.path.isfile(source_path):
        try:
            file_name = os.path.basename(source_path)
            folder_name = os.path.dirname(source_path)
            source_path = os.path.join(folder_name, file_name)
            shutil.copy2(source_path, destination_path)
            print(f"Đã sao chép tệp thành công!\n")
            return file_name, folder_name
        except (OSError, IOError) as e:
            print(f"Cảnh báo: Không thể sao chép tệp {source_path}: {e}")
            sys.exit(1)

    # Nếu source_path là thư mục
    try:
        for item in os.listdir(source_path):
            s = os.path.join(source_path, item)
            d = os.path.join(destination_path, item)
            try:
                if os.path.isdir(s):
                    shutil.copytree(s, d, dirs_exist_ok=True)
                else:
                    shutil.copy2(s, d)
            except (OSError, IOError) as e:
                print(f"Cảnh báo: Không thể sao chép {s}: {e}")
                sys.exit(1)
        print(f"Đã sao chép các tệp thành công!\n")
    except Exception as e:
        print(f"Lỗi khi sao chép tệp: {e}")
        sys.exit(1)

def save_wp_credentials(website_path, website_url, wp_admin, wp_admin_password, wp_admin_email):
    """ Lưu thông tin đăng nhập WordPress vào file. """

    file_path = os.path.join(website_path, "wp_credentials.txt")

    credentials_content = f"""Wordpress Login Credentials:
------------------------------------------
Login URL: {website_url}/wp-admin/
Username: {wp_admin}
Password: {wp_admin_password}
Email: {wp_admin_email}
------------------------------------------
    """

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(credentials_content)
        print(f"Thông tin đăng nhập đã được lưu vào {os.path.abspath(file_path)}\n")
    except IOError as e:
        print(f"Lỗi khi ghi file {file_path}: {e}")

def print_info(website_url, wp_admin, wp_admin_password, wp_admin_email):
    print(f"""Wordpress Login Credentials:
------------------------------------------
Login URL: {website_url}/wp-admin/
Username: {wp_admin}
Password: {wp_admin_password}
Email: {wp_admin_email}
------------------------------------------
    """)
    print('Bấm "Reload Apache Server" nếu nhận lỗi 500 (Internal Server Error), SSL Error hoặc bất cứ lỗi nào khác!')

def reload_laragon(laragon_path, website_url, custom_slug=None):
    """ Reload Apache Server """
    # Reload Apache Server
    subprocess.run(f'{os.path.join(laragon_path, "laragon.exe")} reload apache', shell=True)

    # Truy cập website  
    slug = custom_slug if custom_slug else "wp-admin"
    subprocess.run(f'start "" "{website_url}/{slug}"', shell=True)
