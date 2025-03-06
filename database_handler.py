import os
import sys
import re
from commands import run_sql_command


# Function kiểm tra database đã tồn tại chưa
def check_database_exists(db_name):
    try:
        result = run_sql_command(f'-e "SHOW DATABASES LIKE \'{db_name}\';"')
        return db_name in result.stdout
    except Exception as e:
        print(f'Lỗi khi kiểm tra database: {e}')
        return False


# Function tạo database
def create_database(db_name):
    try:
        result = run_sql_command(f'-e "CREATE DATABASE IF NOT EXISTS {db_name}; GRANT ALL PRIVILEGES ON {db_name}.* TO root@localhost WITH GRANT OPTION; FLUSH PRIVILEGES;"')
        print(f'Đã tạo database: "{db_name}"\n')
    except Exception as e:
        print(f'Lỗi khi tạo database "{db_name}": {e}')
        sys.exit(1)


# Function xóa database
def drop_database(db_name):
    try:
        result = run_sql_command(f'-e "DROP DATABASE IF EXISTS {db_name};"')
        print(f'Đã xóa database: "{db_name}"')
    except Exception as e:
        print(f'Lỗi khi xóa database "{db_name}": {e}')
        sys.exit(1)


# Function tìm file SQL
def find_sql_file(dir):
    for file in os.listdir(dir):
        if file.endswith('.sql'):
            return file
    return None


# Function tìm prefix của database và cập nhật wp-config.php
def update_table_prefix(db_name, website_path):
    """ Tìm prefix của database và cập nhật wp-config.php """
    print(f'Kiểm tra prefix của database {db_name}...')
    
    # Query để lấy tên bảng từ database (Ví dụ: wp_options)
    result = run_sql_command(f'--silent --skip-column-names -e "SELECT table_name FROM information_schema.tables WHERE table_schema = \'{db_name}\' AND table_name LIKE \'%options\'"')
    
    if result.stdout and result.stderr == '':
        # Trích xuất tên bảng từ kết quả
        table_names = result.stdout.strip().split('\n')

        # Bảng đầu tiên có tên kết thúc bằng 'options'
        for table in table_names:
            table = table.strip()
            if table.endswith('options'):
                # Trích xuất prefix từ tên bảng
                prefix = table[:-len('options')]
                if prefix == 'wp_':
                    return prefix
                else:
                    print(f'Đã phát hiện prefix: "{prefix}"')
                    
                    # Cập nhật wp-config.php với prefix
                    wp_config_path = os.path.join(website_path, 'wp-config.php')
                    try:
                        if os.path.exists(wp_config_path):
                            with open(wp_config_path, 'r', encoding='utf-8') as f:
                                config_content = f.read()
                            
                            # Thay thế hoặc thêm dòng prefix
                            if "$table_prefix" in config_content:
                                updated_content = re.sub(
                                    r"\$table_prefix\s*=\s*'[^']*';",
                                    f"$table_prefix = '{prefix}';",
                                    config_content
                                )
                            else:
                                updated_content = config_content + f"\n$table_prefix = '{prefix}';\n"
                            
                            with open(wp_config_path, 'w', encoding='utf-8') as f:
                                f.write(updated_content)
                            
                            print(f'Đã cập nhật prefix trong wp-config.php thành: "{prefix}"')
                            return prefix
                        else:
                            print(f'Không tìm thấy file wp-config.php tại: {wp_config_path}')
                            return False
                    except IOError as e:
                        print(f'Lỗi khi đọc/ghi file wp-config.php: {e}')
                        return False
    else:
        print(f'Không thể phát hiện prefix của database. Lỗi: {result.stderr}')
        return False
