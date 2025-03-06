import os
from input_handler import get_website_inputs
import config


# Function xác định đường dẫn cài đặt Laragon
def get_laragon_path():
    laragon_path = config.laragon_path
    laragon_sites_path = os.path.join(laragon_path, "www")
    cached_path = os.path.join(laragon_path, "tmp", "cached")
    if not os.path.exists(laragon_path):
        print(f"Đường dẫn Laragon: '{laragon_path}' không tồn tại, vui lòng kiểm tra lại!")
        exit(1)
    return laragon_path, laragon_sites_path, cached_path


def main():
    laragon_path, laragon_sites_path, _ = get_laragon_path()

    inputs = get_website_inputs(laragon_path, laragon_sites_path)    

    if inputs.restore_method['is_restore']:
        from restore import Restore
        wp_restore = Restore(inputs)
        wp_restore.handle_restore_method()

    else:
        from wp_installer import WPInstaller
        wp_install = WPInstaller(inputs)
        selected_plugins = wp_install.choose_install_plugin() if inputs.is_install_plugins else None
        wp_install.create_new_website(selected_plugins)

if __name__ == "__main__":
    main()
