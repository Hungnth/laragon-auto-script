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
        self.restore_method = {
            "is_restore": False,
            "method": "",
            "source_path": "",
            "db_path": "",
        }

def validate_input(prompt: str, pattern: str = r'^[a-zA-Z0-9_-]+$') -> str:
    """Validate user input against a regex pattern"""
    while True:
        value = input(prompt).strip()
        if not re.match(pattern, value):
            print("Chỉ chấp nhận ký tự chữ cái, số, dấu gạch dưới và dấu gạch ngang!")
            continue
        return value


def validate_yes_no_input(prompt: str, default: bool = False) -> bool:
    """Handle yes/no input validation with default value"""
    while True:
        user_input = input(f'{prompt} (y/n) (Mặc định: "{"yes" if default else "no"}"): ').lower().strip()
        if user_input in ['y', 'yes']:
            return True
        elif user_input in ['n', 'no', '']:
            return False
        print('Vui lòng chỉ nhập y/n hoặc yes/no hoặc nhấn "Enter" để sử dụng mặc định.')


def validate_website_path(website_name: str, laragon_path: str) -> str:
    """Validate website path and check for conflicts"""
    website_path = os.path.join(laragon_path, 'www', website_name)
    
    if os.path.exists(website_path):
        print(f'Thư mục / website "{website_name}" đã tồn tại!')
        sys.exit(1)

    if check_database_exists(website_name):
        print(f'Database "{website_name}" đã tồn tại!')
        sys.exit(1)
        
    return website_path


def parse_arguments() -> argparse.Namespace:
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


def handle_restore_args(args: argparse.Namespace, inputs: WebsiteInputs) -> WebsiteInputs:
    """Handle restore-related arguments"""
    
    if args.ai1 and os.path.exists(args.ai1):
        inputs.restore_method.update({
            'is_restore': True,
            'method': 'ai1',
            'source_path': args.ai1
        })
    elif args.dup and os.path.exists(args.dup):
        inputs.restore_method.update({
            'is_restore': True,
            'method': 'dup',
            'source_path': args.dup
        })
    elif args.wpcontent:
        if not args.db:
            print('Bạn chưa nhập đường dẫn tới file database!')
            sys.exit(1)
        if os.path.exists(args.wpcontent) and os.path.exists(args.db):
            inputs.restore_method.update({
                'is_restore': True,
                'method': 'wpcontent',
                'source_path': args.wpcontent,
                'db_path': args.db
            })
    elif args.wp and os.path.exists(args.wp):
        inputs.restore_method.update({
            'is_restore': True,
            'method': 'wp',
            'source_path': args.wp
        })

    return inputs


def handle_command_line_input(args: argparse.Namespace, laragon_path: str) -> WebsiteInputs:
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

        inputs.website_path = validate_website_path(inputs.website_name, laragon_path)
        
        # Handle optional arguments
        inputs.ssl = args.ssl
        inputs.is_install_plugins = args.plugins
        inputs.apply_options = not args.option
        inputs.language = args.language if args.language else inputs.language
        
        # Handle restore methods
        return handle_restore_args(args, inputs)
    
    return None


def handle_interactive_input(laragon_path: str) -> WebsiteInputs:
    """Handle interactive user input"""
    inputs = WebsiteInputs()
    
    # Get website name
    while True:
        inputs.website_name = validate_input("Nhập tên thư mục website: ").replace(" ", "_")
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
        inputs.admin_username = validate_input("Nhập admin_username: ").replace(" ", "_")
        if inputs.admin_username:
            break
        print("Admin username không được để trống!")

    while True:
        inputs.admin_password = input("Nhập admin_password: ")
        if inputs.admin_password:
            break
        print("Admin password không được để trống!")

    # Get SSL preference
    inputs.ssl = validate_yes_no_input("Cài đặt SSL cho website")
    
    # Get plugins preference
    inputs.is_install_plugins = validate_yes_no_input("\nBạn có muốn cài đặt plugin không?")

    return inputs


def get_website_inputs(laragon_path: str, laragon_sites_path: str):
    """Main function to get all website inputs"""
    
    bulk_restore_file = config.bulk_restore_path
    args = parse_arguments()

    if args.bulk_restore is not None:        
        if not args.bulk_restore:
            print("Bạn chưa nhập đường dẫn tới file CSV, dùng file mặc định!")
            args.bulk_restore = bulk_restore_file
        else:
            args.bulk_restore = args.bulk_restore

        from bulk_restore import BulkRestore
        bulk_restore = BulkRestore(args.bulk_restore)
        bulk_restore.restore_from_csv()
        sys.exit(0)

    elif args.delete is not None:
        from delete_website import delete_website_by_name, delete_website_interactive

        if args.delete:
            delete_website_by_name(args.delete, laragon_path, laragon_sites_path)
        else:
            delete_website_interactive(laragon_path, laragon_sites_path)
        sys.exit(0) 
        
    # Try command line input for normal website creation
    inputs = handle_command_line_input(args, laragon_path)
    if inputs:
        return inputs
        
    # Only fall back to interactive input if no arguments were provided
    if len(sys.argv) == 1:
        return handle_interactive_input(laragon_path)