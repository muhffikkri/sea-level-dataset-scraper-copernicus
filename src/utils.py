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
    """Memindahkan file dari folder data/ ke subfolder tujuan"""
    if source_dir == target_dir:
        return
    
    os.makedirs(target_dir, exist_ok=True)
    for item in os.listdir(source_dir):
        s_path = os.path.join(source_dir, item)
        # Pindahkan hanya file (bukan folder tahun/bulan lain)
        if os.path.isfile(s_path):
            try:
                shutil.move(s_path, os.path.join(target_dir, item))
            except Exception as e:
                print(f"   [Error] Gagal memindahkan {item}: {e}")

def check_exists(path):
    return os.path.exists(path) and len(os.listdir(path)) > 0