from input_handler import WebsiteInputs
from wp_installer import WPInstaller
from database_handler import create_database, update_table_prefix, find_sql_file
from utilities import print_info, save_wp_credentials, copy_file_folder, reload_laragon
from commands import run_command, run_sql_command
import os, sys, shutil, subprocess
from main import get_laragon_path


class Restore:
    """ Restore website """

    def __init__(self, inputs: WebsiteInputs, bulk_restore: bool = False):
        
        self.laragon_path, self.laragon_sites_path, self.cached_path = get_laragon_path()

        self.website_name = inputs.website_name        
        self.wp_admin = inputs.admin_username
        self.wp_admin_password = inputs.admin_password
        self.wp_admin_email = inputs.admin_email
        self.ssl = inputs.ssl
        self.language = inputs.language
        self.apply_options = inputs.apply_options
        self.restore_method = inputs.restore_method        
        self.bulk_restore = bulk_restore
        self.protocol = "https://" if self.ssl else "http://"
        self.website_url = f"{self.protocol}{self.website_name}.test"
        self.website_path = os.path.join(self.laragon_sites_path, self.website_name)

        self.wp_cli_cmd = f'wp --path=\"{self.website_path}\"'
    
        self.wp_install = WPInstaller(inputs)

    def handle_restore_method(self):
        """ Restore website method """

        restore_plugin = self.restore_method["method"]
        source_path = self.restore_method["source_path"]

        if restore_plugin == "ai1":
            self.restore_ai1(source_path)
        elif restore_plugin == "dup":
            self.restore_dup(source_path)
        elif restore_plugin == "wpcontent":
            db_path = self.restore_method.get("db_path")
            if not db_path:
                print("Thiếu đường dẫn database cho phương thức wp-content")
                return
            self.restore_wpcontent(source_path, db_path)
        elif restore_plugin == "wp":
            self.restore_wp(source_path)

    def restore_ai1(self, ai1_source_path):
        """Restore website bằng plugin All-in-One WP Migration"""

        # Tạo thư mục website
        os.makedirs(self.website_path, exist_ok=True)
        print(f"\nThư mục {self.website_path} đã được tạo thành công!")

        # Tạo database
        create_database(self.website_name)

        # Tải / giải nén / copy Wordpress core
        self.wp_install.install_wp_core()

        # Tạo file wp-config.php
        self.wp_install.edit_wp_config()

        # Cài đặt website Wordpress
        self.wp_install.install_wordpress()

        # Tạo .htaccess
        self.wp_install.edit_htaccess()
        
        # Cài đặt plugin All-in-One WP Migration và Unlimited Extension
        self.wp_install.install_plugins(self.wp_install.choose_install_plugin("2, 3"))

        ai1_path = os.path.join(self.website_path, "wp-content", "ai1wm-backups")
        
        # Copy file backup vào thư mục wp-content/ai1wm-backups
        print(f"Copy file backup vào thư mục {ai1_path}")
        file_name, _ = copy_file_folder(ai1_source_path, ai1_path)
        
        # Restore website
        print(f"Restore website từ file: {file_name}")
        run_command(f'{self.wp_cli_cmd} ai1wm restore "{file_name}" --yes')

        # Update table prefix in wp-config.php
        prefix = update_table_prefix(self.website_name, self.website_path)

        # Thay đổi thông tin admin
        self.wp_install.change_admin_info(prefix)

        # Lưu thông tin đăng nhập vào file
        save_wp_credentials(self.website_path, self.website_url, self.wp_admin, self.wp_admin_password, self.wp_admin_email)

        if not self.bulk_restore:
            # In kết quả
            print_info(self.website_url, self.wp_admin, self.wp_admin_password, self.wp_admin_email)

            # Reload Apache Server
            reload_laragon(self.laragon_path, self.website_url)

    def restore_dup(self, dup_source_path):
        """ Restore website bằng plugin Duplicator Pro """

        # Tạo thư mục website
        os.makedirs(self.website_path, exist_ok=True)
        print(f"\nThư mục {self.website_path} đã được tạo thành công!")

        # Tạo database
        create_database(self.website_name)

        # Copy file backup vào thư mục website
        print(f"Copy file backup vào thư mục {self.website_path}")
        copy_file_folder(dup_source_path, self.website_path)

        if not self.bulk_restore:
            # Reload Apache Server
            reload_laragon(self.laragon_path, self.website_url, "installer.php")

            # Hỏi lại sau khi cài đặt xong
            confirm = input("Bạn đã cài đặt xong và muốn thay đổi thông tin admin? (y/n): ").lower().strip()
            if confirm == "y" or confirm == "yes":
                prefix = update_table_prefix(self.website_name, self.website_path)
                self.wp_install.change_admin_info(prefix)

    def restore_wpcontent(self, wpcontent_source_path, db_path):
        """ Restore website thủ công """

        # Tạo thư mục website
        os.makedirs(self.website_path, exist_ok=True)
        print(f"\nThư mục {self.website_path} đã được tạo thành công!")

        create_database(self.website_name)

        self.wp_install.install_wp_core()

        self.wp_install.edit_wp_config()

        self.wp_install.install_wordpress()

        self.wp_install.edit_htaccess()

        print(f"Copy 'wp-content' vào thư mục {self.website_path}")
        wp_content_path = os.path.join(self.website_path, "wp-content")
        if os.path.exists(wp_content_path):
            try:
                shutil.rmtree(wp_content_path)

                try:
                    result = subprocess.run(
                        f'robocopy "{wpcontent_source_path}" "{wp_content_path}" /E',
                        shell=True,
                        capture_output=True,
                        text=True
                    )
                    if result.stderr:
                        print(result.stderr)
                except Exception as e:
                    print(f"Lỗi khi copy thư mục: {e}")
                    sys.exit(1)

            except Exception as e:
                print(f"Lỗi khi xóa thư mục {wp_content_path}: {e}")
                sys.exit(1)

        print(f"Copy database vào thư mục {self.website_path}")
        file_name, _ = copy_file_folder(db_path, self.website_path)
        db_copied_path = os.path.join(self.website_path, file_name)

        print(f"Import database: {file_name}")
        run_sql_command(f'{self.website_name} < "{db_copied_path}"')
        
        prefix = update_table_prefix(self.website_name, self.website_path)

        self.wp_install.change_url(prefix)

        self.wp_install.change_admin_info(prefix)
        
        save_wp_credentials(self.website_path, self.website_url, self.wp_admin, self.wp_admin_password, self.wp_admin_email)

        if not self.bulk_restore:
            print_info(self.website_url, self.wp_admin, self.wp_admin_password, self.wp_admin_email)

            reload_laragon(self.laragon_path, self.website_url)

    def restore_wp(self, wp_source_path):
        """ Restore website thủ công bằng source code đầy đủ """

        # Tạo thư mục website
        os.makedirs(self.website_path, exist_ok=True)
        print(f"\nThư mục {self.website_path} đã được tạo thành công!")

        # Copy source code vào thư mục website
        print(f"Copy source code vào thư mục {self.website_path}")
        try:
            # Sử dụng robocopy để copy với full quyền
            result = subprocess.run(
                f'robocopy "{wp_source_path}" "{self.website_path}" /E',
                shell=True,
                capture_output=True,
                text=True
            )
            if result.stderr:
                print(result.stderr)
        except Exception as e:
            print(f"Lỗi khi copy thư mục: {e}")
            sys.exit(1)

        # Tạo database
        create_database(self.website_name)

        # Tạo file wp-config.php
        self.wp_install.edit_wp_config()

        # Kiểm tra file SQL có tồn tại không:
        sql_file = find_sql_file(self.website_path)
        if sql_file:
            wp_db_path = os.path.join(self.website_path, sql_file)
        else:
            print(f"Không tìm thấy file SQL trong thư mục {self.website_path}")
            sys.exit(1)
        
        # Import database
        print(f"Import database: {sql_file}")
        result = run_sql_command(f'{self.website_name} < "{wp_db_path}"')
        
        # Update table prefix in wp-config.php
        prefix = update_table_prefix(self.website_name, self.website_path)

        # Thay đổi url website
        self.wp_install.change_url(prefix)

        # Thay đổi thông tin admin
        self.wp_install.change_admin_info(prefix)
        
        # Lưu thông tin đăng nhập vào file
        save_wp_credentials(self.website_path, self.website_url, self.wp_admin, self.wp_admin_password, self.wp_admin_email)

        if not self.bulk_restore:
            # In kết quả
            print_info(self.website_url, self.wp_admin, self.wp_admin_password, self.wp_admin_email)

            # Reload Apache Server
            reload_laragon(self.laragon_path, self.website_url)

        