import os
import time
import shutil
        
def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)

def get_base_data_path():
    """Memastikan folder data/ ada dan mengembalikan path absolutnya"""
    base = os.path.join(os.getcwd(), "data")
    os.makedirs(base, exist_ok=True)
    return base

def is_download_finished(folder_path, timeout=1200):
    """Menunggu sampai semua file dalam batch selesai didownload"""
    print("      [Monitor] Memulai pemantauan antrean download...")
    
    # Beri jeda awal agar browser sempat memicu semua popup download (jika ada)
    # dan membuat file .crdownload di folder
    time.sleep(10) 

    start_time = time.time()
    while time.time() - start_time < timeout:
        # Cek apakah masih ada file temporary Chrome
        temp_files = [f for f in os.listdir(folder_path) if f.endswith('.crdownload')]
        
        if len(temp_files) > 0:
            print(f"      [Monitor] {len(temp_files)} file masih dalam proses...")
        else:
            # Jika tidak ada .crdownload, cek apakah ada file baru yang masuk
            # Beri buffer 5 detik untuk memastikan tidak ada download baru yang 'telat' mulai
            time.sleep(5)
            if not [f for f in os.listdir(folder_path) if f.endswith('.crdownload')]:
                print("      [Monitor] Semua download dalam batch ini selesai.")
                return True
        
        time.sleep(10) # Cek setiap 10 detik agar tidak membebani CPU
        
    return False

def check_if_folder_has_data(folder_path):
    """Cek apakah folder sudah berisi file (selain folder lain)"""
    if not os.path.exists(folder_path):
        return False
    files = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]
    return len(files) > 0

def move_files_to_target(source_dir, target_dir):
    """Memindahkan file dari folder data/ ke subfolder tujuan dengan error handling"""
    if source_dir == target_dir:
        return
    
    os.makedirs(target_dir, exist_ok=True)
    moved_count = 0
    
    for item in os.listdir(source_dir):
        s_path = os.path.join(source_dir, item)
        # Pindahkan hanya file (bukan folder tahun/bulan lain)
        if os.path.isfile(s_path):
            try:
                t_path = os.path.join(target_dir, item)
                shutil.move(s_path, t_path)
                moved_count += 1
            except Exception as e:
                print(f"   [Error] Gagal memindahkan {item}: {e}")
    
    if moved_count > 0:
        print(f"      [Move] Berhasil memindahkan {moved_count} file ke: {target_dir}")

def get_orphaned_files_in_root(root_data_dir):
    """Deteksi file NetCDF yang tertinggal di folder data/ (belum dipindahkan)
    
    Return: dict dengan mapping path_folder_bulan -> [files]
    Contoh: {'2020/01': ['file1.nc', 'file2.nc']}
    """
    orphaned = {}
    
    if not os.path.exists(root_data_dir):
        return orphaned
    
    # Cek hanya file .nc di root data/
    for item in os.listdir(root_data_dir):
        item_path = os.path.join(root_data_dir, item)
        
        # Kita hanya peduli dengan file NetCDF, bukan folder
        if os.path.isfile(item_path) and item.endswith('.nc'):
            # Ekstrak tahun dan bulan dari nama file
            # Format nama file: dt_global_allsat_phy_l4_YYYYMMDD_*.nc
            if '_' in item and len(item) > 15:
                parts = item.split('_')
                if len(parts) >= 6:
                    date_part = parts[5]  # YYYYMMDD
                    if date_part.isdigit() and len(date_part) == 8:
                        year = date_part[0:4]
                        month = date_part[4:6]
                        folder_key = f"{year}/{month}"
                        
                        if folder_key not in orphaned:
                            orphaned[folder_key] = []
                        orphaned[folder_key].append(item)
    
    return orphaned

def recover_orphaned_files(root_data_dir, output_folder):
    """Pindahkan file yang tertinggal di root data/ ke folder tujuan yang sesuai
    
    Berguna saat ada gangguan (crash/mati listrik) dan proses move belum selesai.
    Return: True jika ada file yang dipindahkan, False jika tidak ada
    """
    orphaned = get_orphaned_files_in_root(root_data_dir)
    
    if not orphaned:
        return False
    
    print("\n   [Recovery] Ditemukan file tertinggal di folder data/:")
    total_moved = 0
    
    for folder_key, files in orphaned.items():
        target_path = os.path.join(root_data_dir, output_folder, folder_key)
        os.makedirs(target_path, exist_ok=True)
        
        for file in files:
            src_path = os.path.join(root_data_dir, file)
            dst_path = os.path.join(target_path, file)
            
            try:
                shutil.move(src_path, dst_path)
                print(f"   [Recovery] Pindah {file} ke {folder_key}/")
                total_moved += 1
            except Exception as e:
                print(f"   [Recovery] Gagal pindah {file}: {e}")
    
    if total_moved > 0:
        print(f"   [Recovery] Total {total_moved} file berhasil dipulihkan")
    
    return total_moved > 0

def check_exists(path):
    """Cek apakah folder sudah ada dan berisi file"""
    return os.path.exists(path) and len(os.listdir(path)) > 0