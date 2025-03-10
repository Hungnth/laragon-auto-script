import csv, os, sys, subprocess, aiofiles, asyncio
from main import get_laragon_path
from datetime import datetime
from database_handler import check_database_exists


laragon_path, laragon_sites_path, cached_path = get_laragon_path()

class BulkRestore:
    """ Handle bulk restore from CSV file """
    
    def __init__(self, csv_path):
        self.laragon_path = laragon_path
        self.laragon_sites_path = laragon_sites_path
        self.cached_path = cached_path

        self.csv_path = csv_path
        self.protocol = "http://"  # Default protocol
        self.results = []  # Store results of each website restore

    async def _check_website_exists(self, website_name: str, website_path: str) -> tuple[bool, str]:
        """Kiểm tra website đã tồn tại hay chưa"""
        if os.path.exists(website_path):
            return True, "Thư mục website đã tồn tại"
        if await check_database_exists(website_name):
            return True, "Database đã tồn tại"
        return False, ""

    async def restore_from_csv(self):
        """ Restore multiple websites from CSV file """
        
        if not os.path.exists(self.csv_path):
            print(f"Tệp '{self.csv_path}' không tồn tại. Vui lòng kiểm tra lại đường dẫn!")
            sys.exit(1)
        if not self.csv_path.endswith(".csv"):
            print(f"Tệp '{self.csv_path}' không phải là file csv! Script chỉ hoạt động với file csv!")
            sys.exit(1)

        print(f"\nĐọc file CSV: {self.csv_path}")
        
        # Thử đọc file với các encoding khác nhau
        encodings = ['utf-8', 'utf-8-sig', 'utf-16', 'cp1258']
        content = None
        
        for encoding in encodings:
            try:
                async with aiofiles.open(self.csv_path, 'r', encoding=encoding) as f:
                    content = await f.read()
                    break
            except UnicodeDecodeError:
                continue
        
        if content is None:
            print("Không thể đọc file CSV. Vui lòng đảm bảo file được mã hóa UTF-8 hoặc UTF-16.")
            sys.exit(1)
            
        # Đọc nội dung CSV từ string
        reader = csv.DictReader(content.splitlines())
            
        # Kiểm tra các cột bắt buộc
        required_columns = ["website_name", "source_path", "restore_method"]
        missing_columns = [col for col in required_columns if col not in reader.fieldnames]
        if missing_columns:
            print(f"Thiếu các cột bắt buộc trong file CSV: {', '.join(missing_columns)}")
            print("File CSV phải có các cột: website_name, source_path, restore_method")
            sys.exit(1)

        tasks = []

        for index, row in enumerate(reader):
            task = self._restore_website(row, index)
            tasks.append(task)

        await asyncio.gather(*tasks)

        await self._export_results()
        await self._print_summary()

    async def _restore_website(self, row, index):
        """ Xử lý restore một website cụ thể (chạy song song) """

        result = {
            "website_name": row["website_name"].strip(),
            "restore_method": row["restore_method"].strip().lower(),
            "source_path": row["source_path"].strip(),
            "db_path": row["db_path"].strip() if "db_path" in row else None,
            "status": "Failed",
            "error_message": "",
            "missing_requirements": []
        }

        try:
            print(f"\n{'='*50}")
            print(f"Đang restore website: {result['website_name']}")

            from input_handler import WebsiteInputs
            inputs = WebsiteInputs()
            inputs.website_name = result["website_name"]
            inputs.website_path = os.path.join(self.laragon_sites_path, inputs.website_name)

            # Kiểm tra website đã tồn tại chưa
            exists, error_message = await self._check_website_exists(inputs.website_name, inputs.website_path)
            if exists:
                result["error_message"] = error_message
                print(f"{result['error_message']}")
                self.results.append(result)
                return
            
            # Cập nhật thông tin admin nếu có
            if "admin_username" in row and row["admin_username"].strip():
                inputs.admin_username = row["admin_username"].strip()
            if "admin_password" in row and row["admin_password"].strip():
                inputs.admin_password = row["admin_password"].strip()
            if "admin_email" in row and row["admin_email"].strip():
                inputs.admin_email = row["admin_email"].strip()
            if "ssl" in row and row["ssl"].strip().lower() in ['true', '1', 'yes']:
                inputs.ssl = True

            # Kiểm tra phương thức restore và source path
            required_restore_method = ["ai1", "dup", "wpcontent", "wp"]
            restore_method = result["restore_method"]
            if restore_method not in required_restore_method:
                result["error_message"] = f"Phương thức restore không hợp lệ: {restore_method}"
                print(result["error_message"])
                self.results.append(result)
                return
            
            # Kiểm tra source path
            if not os.path.exists(result["source_path"]):
                result["error_message"] = f"Đường dẫn source path không tồn tại: {result['source_path']}"
                print(result["error_message"])
                self.results.append(result)
                return
            
            # Tạo instance Restore
            from restore import Restore
            restore = Restore(inputs, True)

            if restore_method == "ai1":
                await restore.restore_ai1(result["source_path"])
            elif restore_method == "dup":
                await restore.restore_dup(result["source_path"])
            
            elif restore_method == "wp":
                await restore.restore_wp(result["source_path"])

            elif restore_method == "wpcontent":
                if not result["db_path"]:
                    result["error_message"] = "Không tìm thấy đường dẫn database"
                    result["missing_requirements"].append("db_path")
                    print(result["error_message"])
                    self.results.append(result)
                    return
                db_path = result["db_path"].strip()

                if not os.path.exists(db_path):
                    result["error_message"] = "Đường dẫn database không tồn tại"
                    print(result["error_message"])
                    self.results.append(result)
                    return
                
                await restore.restore_wpcontent(result["source_path"], db_path)

            result["status"] = "Success"
            self.results.append(result)
            print(f"Website {result['website_name']} đã được restore thành công!")
            
        except Exception as e:
            result["error_message"] = str(e)
            print(f"Lỗi khi restore website {result['website_name']}: {e}")
            self.results.append(result)
            return               
                

    async def _export_results(self):
        """Export results to a CSV file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")        
        log_dir = os.path.join(os.path.dirname(self.csv_path), "logs")
        
        os.makedirs(log_dir, exist_ok=True)
        output_file = os.path.join(log_dir, f"bulk_restore_results_{timestamp}.csv")
        
        fieldnames = ["website_name", "restore_method", "source_path", "db_path", "status", "error_message", "missing_requirements"]
        
        # Ghi file với UTF-8-SIG để Excel có thể đọc được tiếng Việt
        async with aiofiles.open(output_file, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            await writer.writeheader()
            for result in self.results:
                # Make a copy of the result to avoid modifying the original
                row = result.copy()
                # Join the missing requirements list properly
                if isinstance(row["missing_requirements"], list):
                    row["missing_requirements"] = ", ".join(row["missing_requirements"])
                await writer.writerow(row)
                
        print(f"\nKết quả đã được xuất ra file: {output_file}")

    async def _print_summary(self):
        """Print a summary of the restoration results"""
        total = len(self.results)
        successful = sum(1 for r in self.results if r["status"] == "Success")
        failed = total - successful
        
        print("\n" + "="*50)
        print("TÓM TẮT KẾT QUẢ RESTORE:")
        print(f"Tổng số website: {total}")
        print(f"Thành công: {successful}")
        print(f"Thất bại: {failed}")
        
        if failed > 0:
            print("\nDanh sách website thất bại:")
            for result in self.results:
                if result["status"] == "Failed":
                    print(f"- {result['website_name']}: {result['error_message']}")
                    if result["missing_requirements"]:
                        print(f"Thiếu yêu cầu: {', '.join(result['missing_requirements'])}")

        # Reload Apache Server
        await asyncio.to_thread(subprocess.run, f'{os.path.join(self.laragon_path, "laragon.exe")} reload apache', shell=True)
        print("\nHoàn tất quá trình bulk restore!") 


    