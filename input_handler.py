import argparse, os, re, sys
from database_handler import check_database_exists
import config


class WebsiteInputs:
    """Class to store website input data"""
    def __init__(self):
        self.website_name = ""
        self.website_path = ""
        self.admin_username = config.admin_username # Username mặc định
        self.admin_password = config.admin_password # Password mặc định
        self.admin_email = config.admin_email # Email mặc định
        self.ssl = False
        self.is_install_plugins = False
        self.language = config.language  # Ngôn ngữ mặc định
        self.apply_options = True


async def validate_input(prompt: str, pattern: str = r'^[a-zA-Z0-9_-]+$') -> str:
    """Validate user input against a regex pattern"""
    while True:
        value = input(prompt).strip()
        if not re.match(pattern, value):
            print("Chỉ chấp nhận ký tự chữ cái, số, dấu gạch dưới và dấu gạch ngang!")
            continue
        return value


async def validate_yes_no_input(prompt: str, default: bool = False) -> bool:
    """Handle yes/no input validation with default value"""
    while True:
        user_input = input(f'{prompt} (y/n) (Mặc định: "{"yes" if default else "no"}"): ').lower().strip()
        if user_input in ['y', 'yes']:
            return True
        elif user_input in ['n', 'no', '']:
            return False
        print('Vui lòng chỉ nhập y/n hoặc yes/no hoặc nhấn "Enter" để sử dụng mặc định.')


async def validate_website_path(website_name: str, laragon_path: str) -> str:
    """Validate website path and check for conflicts"""
    website_path = os.path.join(laragon_path, 'www', website_name)
    
    if os.path.exists(website_path):
        print(f'Thư mục / website "{website_name}" đã tồn tại!')
        sys.exit(1)

    if await check_database_exists(website_name):
        print(f'Database "{website_name}" đã tồn tại!')
        sys.exit(1)
        
    return website_path


async def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Cài đặt WordPress tự động trên Laragon')

    # Named arguments
    parser.add_argument('-n', '--name', help='Tên website/thư mục')
    parser.add_argument('-u', '--username', help='Admin username')
    parser.add_argument('-p', '--password', help='Admin password')
    parser.add_argument('-l', '--language', help='Ngôn ngữ website')
    parser.add_argument('-o', '--option', action='store_true', help='Không cài đặt gì cả, phù hợp dùng cho import website')

    # Restore website
    parser.add_argument('--ai1', help='Sử dụng plugin All-in-One WP Migration và restore website')
    parser.add_argument('--dup', help='Sử dụng plugin Duplicator Pro và restore website')
    parser.add_argument('--wpcontent', help='Restore website thủ công bằng "wp-content"')
    parser.add_argument('--db', help='Database path')
    parser.add_argument('--wp', help='Restore website thủ công bằng source code đầy đủ')

    # Bulk restore website
    parser.add_argument('--bulk_restore', nargs='?', const='', help='Restore website hàng loạt từ file csv')

    # Delete website
    parser.add_argument('--delete', nargs='?', const='', help='Xóa website (để trống để xóa trong chế độ tương tác hoặc nhập tên website để xóa trực tiếp)')

    # Positional arguments
    parser.add_argument('args', nargs='*', help='[Website Name] [Admin Username] [Admin Password]')

    # Optional flags
    parser.add_argument('-s', '--ssl', action='store_true', help='Cài đặt SSL cho website')
    parser.add_argument('-i', '--plugins', action='store_true', help='Hiện danh sách plugins để cài đặt')
    parser.add_argument('-t', '--theme', help='Theme (Hiện chưa dùng được)')

    return parser.parse_args()


async def handle_restore_args(args: argparse.Namespace, inputs: WebsiteInputs) -> WebsiteInputs:
    """Handle restore-related arguments"""
    
    from restore import Restore
    wp_restore = Restore(inputs)

    if args.ai1:
        if not os.path.exists(args.ai1):
            print(f"File '{args.ai1}' không tồn tại!")
            sys.exit(1)
        else:
            await wp_restore.restore_ai1(args.ai1)
            sys.exit(0)

    elif args.dup:
        if not os.path.exists(args.dup):
            print(f"File '{args.dup}' không tồn tại!")
            sys.exit(1)
        else:
            await wp_restore.restore_dup(args.dup)
            sys.exit(0)

    elif args.wpcontent:
        if not args.db:
            print('Bạn chưa nhập đường dẫn tới file database!')
            sys.exit(1)
        else:
            await wp_restore.restore_wpcontent(args.wpcontent, args.db)
            sys.exit(0)

    elif args.wp:
        if not os.path.exists(args.wp):
            print(f"Thư mục '{args.wp}' không tồn tại!")
            sys.exit(1)
        else:
            await wp_restore.restore_wp(args.wp)
            sys.exit(0)

    return inputs


async def handle_command_line_input(args: argparse.Namespace, laragon_path: str) -> WebsiteInputs:
    """Handle command line input arguments"""

    inputs = WebsiteInputs()
    
    # Handle website name and credentials
    if (args.name and args.username and args.password) or len(args.args) >= 3:
        if args.name and args.username and args.password:
            inputs.website_name = args.name.replace(' ', '_')
            inputs.admin_username = args.username.replace(' ', '_')
            inputs.admin_password = args.password
        else:
            inputs.website_name = args.args[0].replace(' ', '_')
            inputs.admin_username = args.args[1].replace(' ', '_')
            inputs.admin_password = args.args[2]

        inputs.website_path = await validate_website_path(inputs.website_name, laragon_path)
        
        # Handle optional arguments
        inputs.ssl = args.ssl
        inputs.is_install_plugins = args.plugins
        inputs.apply_options = not args.option
        inputs.language = args.language if args.language else inputs.language
        
        # Handle restore methods
        return await handle_restore_args(args, inputs)
    
    return None


async def handle_interactive_input(laragon_path: str) -> WebsiteInputs:
    """Handle interactive user input"""
    inputs = WebsiteInputs()
    
    # Get website name
    while True:
        inputs.website_name = await validate_input("Nhập tên thư mục website: ").replace(" ", "_")
        if not inputs.website_name:
            print("Tên website không được để trống!")
            continue
            
        inputs.website_path = os.path.join(laragon_path, "www", inputs.website_name)
        if os.path.exists(inputs.website_path):
            print("Thư mục đã tồn tại, vui lòng nhập tên website khác!")
            continue
            
        if check_database_exists(inputs.website_name):
            print("Database đã tồn tại, vui lòng nhập tên website khác!")
            continue
            
        break

    # Get admin credentials
    while True:
        inputs.admin_username = await validate_input("Nhập admin_username: ").replace(" ", "_")
        if inputs.admin_username:
            break
        print("Admin username không được để trống!")

    while True:
        inputs.admin_password = input("Nhập admin_password: ")
        if inputs.admin_password:
            break
        print("Admin password không được để trống!")

    # Get SSL preference
    inputs.ssl = await validate_yes_no_input("Cài đặt SSL cho website")
    
    # Get plugins preference
    inputs.is_install_plugins = await validate_yes_no_input("\nBạn có muốn cài đặt plugin không?")

    return inputs


async def get_website_inputs(laragon_path: str, laragon_sites_path: str):
    """Main function to get all website inputs"""
    
    bulk_restore_file = config.bulk_restore_path
    args = await parse_arguments()

    if args.bulk_restore is not None:  
        if not args.bulk_restore:
            print("Bạn chưa nhập đường dẫn tới file CSV, dùng file mặc định!")
            args.bulk_restore = bulk_restore_file
        else:
            args.bulk_restore = args.bulk_restore

        from bulk_restore import BulkRestore
        bulk_restore = BulkRestore(args.bulk_restore)
        await bulk_restore.restore_from_csv()
        sys.exit(0)

    elif args.delete is not None:
        from delete_website import delete_website_by_name, delete_website_interactive

        if args.delete:
            await delete_website_by_name(args.delete, laragon_path, laragon_sites_path)
        else:
            await delete_website_interactive(laragon_path, laragon_sites_path)
        sys.exit(0) 
        
    else:
        inputs = await handle_command_line_input(args, laragon_path)
        if inputs:
            return inputs
            
    # Only fall back to interactive input if no arguments were provided
    if len(sys.argv) == 1:
        return await handle_interactive_input(laragon_path)
    else:
        return None