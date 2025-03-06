import subprocess


# Function chạy lệnh
def run_command(command):
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, encoding='utf-8', errors='replace')            
        if result.stderr:
            print(result.stderr)
            
        return result
    except Exception as e:
        print(f'Đã xảy ra lỗi không xác định: {e}')
        return None


# Function chạy lệnh SQL
def run_sql_command(command):
    mysql_cmd = f'mysql -u root {command}'    

    try:
        result = subprocess.run(mysql_cmd, shell=True, capture_output=True, text=True, encoding='utf-8', errors='replace')
        if result.stderr:
            print(result.stderr)
            exit(1)
        return result
    except Exception as e:
        print(f'Đã xảy ra lỗi không xác định: {e}')
        exit(1)