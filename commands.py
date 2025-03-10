import subprocess
import asyncio


async def run_command(command, print_output=False, print_text=None):
    """ Chạy lệnh """

    try:
        if print_text:
            print(print_text)

        result = await asyncio.to_thread(subprocess.run, command, shell=True, capture_output=True, text=True, encoding='utf-8', errors='replace')

        if print_output:
            print(result.stdout)

        if result.stderr:
            print(result.stderr)
            
        return result
    
    except Exception as e:
        print(f'Đã xảy ra lỗi không xác định: {e}')
        return None

# async def run_command(cmd, print_output=False, print_text=None):
#     if print_text:
#         print(print_text)

#     process = await asyncio.create_subprocess_shell(cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
#     stdout, stderr = await process.communicate()
#     if print_output:
#         print(stdout.decode())
#     if stderr:
#         print(stderr.decode())
#     return stdout


async def run_sql_command(command, print_text=None):
    """ Chạy lệnh SQL """

    mysql_cmd = f'mysql -u root {command}'    

    try:
        if print_text:
            print(print_text)

        result = await asyncio.to_thread(subprocess.run, mysql_cmd, shell=True, capture_output=True, text=True, encoding='utf-8', errors='replace')

        if result.stderr:
            print(result.stderr)
            exit(1)
        return result
    except Exception as e:
        print(f'Đã xảy ra lỗi không xác định: {e}')
        exit(1)