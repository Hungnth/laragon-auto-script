from input_handler import WebsiteInputs
from utilities import check_and_download_file, copy_file_folder, extract_zip_file
from commands import run_command, run_sql_command
import os
import json
from main import get_laragon_path
from utilities import save_wp_credentials, print_info, reload_laragon
from database_handler import create_database
import config
import asyncio, aiofiles


# Tải tài nguyên từ file resource.json
try:
    with open(config.resource_path, 'r', encoding='utf-8') as f:
        resource = json.load(f)
        plugins = resource['plugins']
        themes = resource['themes']
except Exception as e:
    print(f"Không thể đọc file resource.json: {e}")


laragon_path, laragon_sites_path, cached_path = get_laragon_path()

class WPInstaller :
    """Install WordPress"""

    def __init__(self, inputs: WebsiteInputs):
        
        self.laragon_path = laragon_path
        self.laragon_sites_path = laragon_sites_path
        self.cached_path = cached_path

        self.website_name = inputs.website_name
        self.wp_admin = inputs.admin_username
        self.wp_admin_password = inputs.admin_password
        self.wp_admin_email = inputs.admin_email
        self.ssl = inputs.ssl
        self.language = inputs.language
        self.apply_options = inputs.apply_options

        self.protocol = "https://" if self.ssl else "http://"
        self.website_url = f"{self.protocol}{self.website_name}.test"
        
        self.website_path = os.path.join(self.laragon_sites_path, self.website_name)

        self.wp_cli_cmd = f'wp --path=\"{self.website_path}\"'        

    async def install_wp_core(self):
        """ Cài đặt WordPress Core """

        # Copy WordPress Core từ thư mục cached
        wp_core_file = os.path.join(self.cached_path, "wordpress.latest.zip")
        await check_and_download_file("https://wordpress.org/latest.zip", wp_core_file)

        wp_core_dir = os.path.join(self.cached_path, "wordpress")

        if not os.path.exists(wp_core_dir):
            await extract_zip_file(wp_core_file, self.cached_path)

        print(f"Sao chép tệp {wp_core_dir} vào {self.website_path}...")
        await copy_file_folder(wp_core_dir, self.website_path)

    async def edit_wp_config(self):
        """ Tạo file wp-config.php """
        wp_config_cmd = f"config create --dbname={self.website_name} --dbuser=root --dbpass= --dbhost=localhost"
        await run_command(f"{self.wp_cli_cmd} {wp_config_cmd}", print_text=f"Tạo file wp-config.php")

    async def install_wordpress(self):
        """ Cài đặt WordPress """
        wp_install_cmd = f'core install --url="{self.website_url}/" --admin_user="{self.wp_admin}" --admin_password="{self.wp_admin_password}" --title="{self.website_name}" --admin_email="{self.wp_admin_email}"'
        await run_command(f"{self.wp_cli_cmd} {wp_install_cmd}", print_text=f"Cài đặt WordPress")

    async def choose_install_plugin(self, plugin_choices=None):
        """ Chọn plugins để cài đặt """

        # In danh sách plugin để người dùng chọn nếu không có argument
        if plugin_choices is None:
            print("\nDanh sách plugins:\n")
            for index, plugin in enumerate(plugins, start=1):
                print(f"{index}. {plugin['name']}")

            # Nhập và tách chuỗi đầu vào
            plugin_choices = input("Chọn plugin cần cài đặt, mỗi plugin cách nhau bởi dấu ',' hoặc ' ' (Ví dụ: 1,2,3 hoặc 1 2 3): ")

        # Xử lý chuỗi input thành list các lựa chọn
        choose_plugins = plugin_choices.replace(" ", ",").split(",")
        choose_plugins = [x.strip() for x in choose_plugins if x.strip()]

        print(f"Chọn plugin: {choose_plugins}")

        selected_plugins_dict = {}

        # Duyệt qua từng lựa chọn và tìm plugin tương ứng
        for choice in choose_plugins:
            for index, plugin in enumerate(plugins, start=1):
                if str(index) == choice:
                    selected_plugins_dict[plugin["id"]] = {
                        "file_name": plugin["file_name"],
                        "url": plugin["url"]
                    }
                    break

        return selected_plugins_dict

    async def install_plugins(self, selected_plugins=None):
        """ Xóa plugin mặc định và cài đặt plugin theo danh sách (nếu có) """

        await asyncio.gather(
            run_command(f"{self.wp_cli_cmd} plugin delete hello"),
            run_command(f"{self.wp_cli_cmd} plugin delete akismet"),
        )        

        # Nếu không có danh sách plugin, dừng lại
        if not selected_plugins:
            return

        # Tải file plugin song song
        download_tasks = []
        plugins_list = []

        for _, details in selected_plugins.items():
            local_path = os.path.join(self.cached_path, details["file_name"])
            download_tasks.append(check_and_download_file(details["url"], local_path))
            plugins_list.append(local_path)

        await asyncio.gather(*download_tasks)

        plugins_path = os.path.join(self.website_path, "wp-content", "plugins")
        tasks = []
        for plugin in plugins_list:
            if "wordfence" in plugin:
                tasks.append(self.wordfence_activate())   
            tasks.append(extract_zip_file(plugin, plugins_path))

        await asyncio.gather(*tasks)

        await run_command(f"{self.wp_cli_cmd} plugin activate --all")


    async def wordfence_activate(self):
        """ Kích hoạt plugin Wordfence """

        wordfence_activate_file = os.path.join(self.cached_path, "nth-wordfence-activator.php")
        await check_and_download_file("https://d3cav5r4mkyokm.cloudfront.net/staging/c9a7aebb-5ab3-41de-8e76-a5685f399a81/660230e0cffab0005b80c518/A-ME-2025-235V-1740714655634.php", wordfence_activate_file)
        mu_plugins_path = os.path.join(self.website_path, "wp-content", "mu-plugins")
        await copy_file_folder(wordfence_activate_file, mu_plugins_path)

    async def install_themes(self, condition=True):
        """ Nếu 'True' thì cài đặt Flatsome và xóa các theme mặc định, nếu 'False' thì chỉ cài đặt Flatsome """

        flatsome_file = os.path.join(self.cached_path, themes[0]["file_name"])
        if not os.path.exists(flatsome_file):
            await check_and_download_file(themes[0]["url"], flatsome_file)

        theme_path = os.path.join(self.website_path, "wp-content", "themes")
        if condition:
            await extract_zip_file(flatsome_file, theme_path)
            await run_command(f'{self.wp_cli_cmd} theme activate flatsome', print_text=f"Cài đặt theme Flatsome")

        default_themes_cmds = [
            "theme delete twentytwentythree",
            "theme delete twentytwentyfour",
            "theme delete twentytwentyfive",
        ]

        tasks= [run_command(f"{self.wp_cli_cmd} {theme_cmd}") for theme_cmd in default_themes_cmds]        

        await asyncio.gather(*tasks)

    async def install_languages(self):
        """ Cấu hình ngôn ngữ website """

        print(f"Cấu hình ngôn ngữ website: {self.language}")
        language_cmds = [
            f"language core install {self.language}",
            f"site switch-language {self.language}"
            ]
        
        for language_cmd in language_cmds:
            await run_command(f"{self.wp_cli_cmd} {language_cmd}")

    async def install_options(self):
        """ Cấu hình options """

        print("Cấu hình options")
        if self.apply_options:
            option_cmds = [
                'config set WP_MEMORY_LIMIT 256M',
                'rewrite structure "/%category%/%postname%/"',
                'option update timezone_string "Asia/Ho_Chi_Minh"',
                'option update time_format "H:i"',
                'option update date_format "d/m/Y"',
                'option update large_size_w 0',
                'option update large_size_h 0',
                'option update medium_large_size_w 0',
                'option update medium_large_size_h 0',
                'option update medium_size_w 0',
                'option update medium_size_h 0',
                'option update thumbnail_size_w 0',
                'option update thumbnail_size_h 0',
                'option update thumbnail_crop 0',
                'option update comment_moderation 1',
                'option update default_ping_status closed',
                'option update posts_per_page 30',
                'option update posts_per_rss 210',
                'option update rss_use_excerpt 1',
                'option update avatar_default identicon'
            ]

            tasks = []
            for cmd in option_cmds:
                try:
                    full_cmd = f"{self.wp_cli_cmd} {cmd}"
                    tasks.append(run_command(full_cmd, print_output=True))
                except Exception as e:
                    print(f"Lỗi khi thực thi lệnh '{cmd}': {e}")
                    continue

            await asyncio.gather(*tasks)

    async def edit_htaccess(self):
        """ Chỉnh sửa file .htaccess để thêm quy tắc chuyển hướng từ HTTP sang HTTPS. """

        htaccess_path = os.path.join(self.website_path, '.htaccess')
        print(f'Tạo file .htaccess: {htaccess_path}\n')

        # Nội dung gốc của .htaccess (nếu file chưa tồn tại)
        default_htaccess = """# BEGIN WordPress
# The directives (lines) between "BEGIN WordPress" and "END WordPress" are
# dynamically generated, and should only be modified via WordPress filters.
# Any changes to the directives between these markers will be overwritten.

<IfModule mod_rewrite.c>
RewriteEngine On
RewriteRule .* - [E=HTTP_AUTHORIZATION:%{HTTP:Authorization}]
RewriteBase /
RewriteRule ^index\.php$ - [L]
RewriteCond %{REQUEST_FILENAME} !-f
RewriteCond %{REQUEST_FILENAME} !-d
RewriteRule . /index.php [L]
</IfModule>

# END WordPress
"""

        # Đoạn mã chuyển hướng HTTP sang HTTPS
        ssl_redirect = """RewriteEngine On
RewriteBase /
RewriteCond %{HTTPS} off
RewriteRule (.*) https://%{HTTP_HOST}%{REQUEST_URI} [L,R=301,NE]
"""
        try:
            # Ghi nội dung vào file
            async with aiofiles.open(htaccess_path, 'w') as f:
                if self.ssl:
                    content = f'{default_htaccess}\n{ssl_redirect}'
                    await f.write(content)
                else:
                    await f.write(default_htaccess)

        except PermissionError:
            print(f"Không có quyền ghi file tại {htaccess_path}")
        except IOError as e:
            print(f"Lỗi khi ghi file {htaccess_path}: {e}")
        except Exception as e:
            print(f"Lỗi không xác định: {e}")
    
    async def change_url(self, prefix="wp_"):
        """ Thay đổi url website """        

        print(f'\nThay đổi url website thành: "{self.website_url}"')

        await asyncio.gather(
            run_sql_command(f'{self.website_name} -e "UPDATE {prefix}options SET option_value = \'{self.website_url}\' WHERE option_name = \'home\';"'),
            run_sql_command(f'{self.website_name} -e "UPDATE {prefix}options SET option_value = \'{self.website_url}\' WHERE option_name = \'siteurl\';"')
        )

    async def change_admin_info(self, prefix="wp_"):
        """Thay đổi thông tin admin"""

        # Lấy ID của admin user đầu tiên
        result = await run_sql_command(f'{self.website_name} --skip-column-names --silent -e "SELECT ID FROM {prefix}users;"')
        user_id = result.stdout.replace('\n', ',').split(',')
        print(f'\nDanh sách ID: {user_id if user_id else "Không tìm thấy ID"}')
        
        tasks = [run_sql_command(f'{self.website_name} -e "UPDATE {prefix}options SET option_value = \'{self.wp_admin_email}\' WHERE option_name = \'admin_email\';"', print_text=f"Thay đổi admin email")]
        if user_id:
            commands = [
                run_sql_command(f'{self.website_name} -e "UPDATE {prefix}users SET user_pass = MD5(\'{self.wp_admin_password}\') WHERE ID = {user_id[0]};"', print_text=f"Đặt lại mật khẩu admin"),
                run_sql_command(f'{self.website_name} -e "UPDATE {prefix}users SET user_login = \'{self.wp_admin}\' WHERE ID = {user_id[0]};"', print_text=f"Đặt lại admin username"),
                run_sql_command(f'{self.website_name} -e "UPDATE {prefix}users SET user_email = \'{self.wp_admin_email}\' WHERE ID = {user_id[0]};"', print_text=f"Thay đổi user email"),
            ]
            tasks.extend(commands)

        await asyncio.gather(*tasks)

        # Flush rewrite rules, cache
        await asyncio.gather(
            run_command(f'{self.wp_cli_cmd} rewrite flush'),
            run_command(f'{self.wp_cli_cmd} cache flush')
        )

    async def create_new_website(self, selected_plugins=None):
        """ Tạo website mới """        
        
        # Chạy tuần tự
        await create_database(self.website_name)
        await self.install_wp_core()
        await self.edit_wp_config()
        await self.install_wordpress()

        await asyncio.gather(
            self.install_themes(),
            self.install_plugins(selected_plugins),
            self.install_languages(),
            self.install_options(),
            self.edit_htaccess(),
            save_wp_credentials(self.website_path, self.website_url, self.wp_admin, self.wp_admin_password, self.wp_admin_email)
        )

        await print_info(self.website_url, self.wp_admin, self.wp_admin_password, self.wp_admin_email)
        await reload_laragon(self.laragon_path, self.website_url)

