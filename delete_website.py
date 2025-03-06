import os
import sys
import shutil
import subprocess

def get_website_list(laragon_sites_path):
    """Lấy danh sách thư mục website"""
    website_folders = [f for f in os.listdir(laragon_sites_path) if os.path.isdir(os.path.join(laragon_sites_path, f))]
    return website_folders

def print_websites(websites):
    """In ra danh sách website"""
    if not websites:
        print('Không có website nào để xóa!')
        sys.exit(1)
    
    print('\nDanh sách website:')
    print('0. Xóa tất cả website')
    for index, folder in enumerate(websites, start=1):
        if folder.startswith('.'):
            continue
        print(f'{index}. {folder}')

def choose_website(websites):
    """Chọn website để xóa"""
    while True:
        try:
            delete_index = int(input('\nChọn website cần xóa (0 để xóa tất cả): '))
            if 0 <= delete_index <= len(websites):
                break
            print(f'Vui lòng nhập số từ 0 đến {len(websites)}!')
        except ValueError:
            print('Vui lòng nhập một số!')
    return delete_index

def delete_website(website_name, laragon_sites_path):
    """Hàm xóa một website cụ thể"""
    website_path = os.path.join(laragon_sites_path, website_name)
    try:
        # Xóa thư mục website
        print(f'\nĐang xóa thư mục: {website_path}')
        shutil.rmtree(website_path)
        print(f'Đã xóa thư mục: {website_path}')

        # Xóa database
        print(f'Đang xóa database: {website_name}')
        mysql_cmd = f'mysql -u root -e "DROP DATABASE IF EXISTS {website_name};"'
        result = subprocess.run(mysql_cmd, shell=True, capture_output=True, text=True)
        
        if result.stderr:
            print(f'Lỗi khi xóa database: {result.stderr}')
        else:
            print(f'Đã xóa database: {website_name}')
        
        return True
    except Exception as e:
        print(f'Lỗi khi xóa website {website_name}: {e}')
        return False

def delete_website_interactive(laragon_path, laragon_sites_path):
    """Xóa website trong chế độ tương tác"""
    websites = get_website_list(laragon_sites_path)
    print_websites(websites)
    try:
        delete_index = choose_website(websites)
        if delete_index == 0:
            # Xác nhận xóa tất cả
            confirm = input(f'\nBạn có chắc chắn muốn xóa TẤT CẢ {len(websites)} website không? (yes/no): ').lower()
            if confirm != 'yes':
                print('Đã hủy xóa website!')
                return False
            
            # Xóa từng website một
            success_count = 0
            for website in websites:
                if delete_website(website, laragon_sites_path):
                    success_count += 1
            
            # Thông báo kết quả
            print(f'\nĐã xóa thành công {success_count}/{len(websites)} website')
        else:
            # Xóa một website
            website_name = websites[delete_index - 1]
            confirm = input(f'\nBạn có chắc chắn muốn xóa website "{website_name}" không? (y/n): ').lower()
            if confirm not in ['y', 'yes']:
                print('Đã hủy xóa website!')
                return False
                            
            if delete_website(website_name, laragon_sites_path):
                print('\nĐã xóa website thành công!')

        # Reload Apache Server
        print('\nReload Apache Server...')
        subprocess.run(f'{os.path.join(laragon_path, "laragon.exe")} reload apache', shell=True)
        return True

    except Exception as e:
        print(f'Lỗi không xác định: {e}')
        return False

def delete_website_by_name(website_name, laragon_path, laragon_sites_path):
    """Xóa website theo tên được chỉ định"""
    if not website_name:
        print("Tên website không được để trống!")
        return False

    websites = get_website_list(laragon_sites_path)
    if website_name not in websites:
        print(f'Website "{website_name}" không tồn tại!')
        return False

    if delete_website(website_name, laragon_sites_path):
        print('\nĐã xóa website thành công!')
        # Reload Apache Server
        print('\nReload Apache Server...')
        subprocess.run(f'{os.path.join(laragon_path, "laragon.exe")} reload apache', shell=True)
        return True
    return False

# if __name__ == '__main__':
#     # Xác định đường dẫn cài đặt Laragon
#     laragon_path = r'F:\laragon'
#     laragon_sites_path = os.path.join(laragon_path, 'www')

#     # Kiểm tra đường dẫn Laragon có tồn tại không
#     if not os.path.exists(laragon_path):
#         print(f'Đường dẫn Laragon: "{laragon_path}" không tồn tại, vui lòng kiểm tra lại!')
#         sys.exit(1)

#     delete_website_interactive(laragon_path, laragon_sites_path)
