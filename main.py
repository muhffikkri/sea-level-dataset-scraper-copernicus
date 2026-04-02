import os
import time
import shutil
import argparse
import logging
from src.scraper import CopernicusScraper
from src.utils import (get_base_data_path, is_download_finished, move_files_to_target, 
                       check_exists, recover_orphaned_files, get_downloaded_dates, get_missing_dates)

def setup_year_logger(year):
    from datetime import datetime
    logs_dir = "logs"
    os.makedirs(logs_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    logger_name = f"copernicus_scraper_{year}_{timestamp}"
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if logger.handlers:
        for handler in list(logger.handlers):
            logger.removeHandler(handler)

    log_filename = f"scraper_{timestamp}_year_{year}.log"
    log_path = os.path.join(logs_dir, log_filename)
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger, log_path


def crawl_recursive(bot, root_data_dir, current_subpath, args, logger):
    # Path tujuan: data/[output]/[tahun]/[bulan] atau data/[output]/
    if args.flat:
        target_path = os.path.join(root_data_dir, args.output)
    else:
        target_path = os.path.join(root_data_dir, args.output, current_subpath)

    # 1. Smart Resume Logic (Hanya jika tidak flat)
    if not args.flat and os.path.exists(target_path) and os.listdir(target_path):
        # Folder sudah ada dan berisi file
        # Cek apakah ada file yang belum didownload (resume case)
        if bot.has_files():
            available_dates = bot.get_file_dates()
            downloaded_dates = get_downloaded_dates(target_path)
            missing_dates = get_missing_dates(available_dates, downloaded_dates)
            
            if not missing_dates:
                # Semua sudah ada, skip sepenuhnya
                print(f"   [Skip] {current_subpath} sudah lengkap ({len(downloaded_dates)} file).")
                logger.info("Skip path fully downloaded: %s (%d files)", current_subpath, len(downloaded_dates))
                return
            else:
                # Ada yang belum, resume download
                print(f"   [Resume] {current_subpath}: {len(downloaded_dates)}/{len(available_dates)} file sudah ada")
                print(f"           Akan download {len(missing_dates)} file yang masih kurang...")
                logger.info("Resume partial download: %s (have %d/%d, missing %d)", 
                           current_subpath, len(downloaded_dates), len(available_dates), len(missing_dates))
        else:
            # Folder ada tapi tidak ada file di website (subfolder kasus)
            print(f"   [Info] {current_subpath} sudah ada, melanjutkan ke subfolder...")
            logger.info("Path already exists with data, checking subfolders: %s", current_subpath)

    # 2. Logika Download (baru atau resume)
    if bot.has_files():
        print(f"   [!] File ditemukan di {current_subpath}. Mendownload...")
        logger.info("File ditemukan pada path: %s", current_subpath)
        if bot.click_select_all():
            if not bot.click_download_button(retries=3, backoff_seconds=2):
                logger.error("Gagal klik tombol download setelah retry pada path: %s", current_subpath)
                return
            
            # Tunggu teks "Downloading" hilang dari UI
            if not bot.wait_until_download_ready():
                logger.warning("Timeout saat menunggu status download UI pada path: %s", current_subpath)
            
            # Tunggu fisik file selesai di folder data/
            if is_download_finished(root_data_dir):
                # Smart move: skip file yang sudah ada, pindahkan yang baru
                os.makedirs(target_path, exist_ok=True)
                
                moved_new = 0
                skipped_existing = 0
                
                for item in os.listdir(root_data_dir):
                    s_path = os.path.join(root_data_dir, item)
                    if os.path.isfile(s_path) and item.endswith('.nc'):
                        t_path = os.path.join(target_path, item)
                        
                        if os.path.exists(t_path):
                            # File sudah ada, skip
                            try:
                                os.remove(s_path)
                                skipped_existing += 1
                            except:
                                pass
                        else:
                            # File baru, pindahkan
                            try:
                                shutil.move(s_path, t_path)
                                moved_new += 1
                            except Exception as e:
                                logger.error("Gagal pindahkan %s: %s", item, str(e))
                
                print(f"   [Done] {moved_new} file baru, {skipped_existing} file existing (skip)")
                logger.info("Download done: %d new files moved, %d existing files skipped, path: %s", 
                           moved_new, skipped_existing, target_path)
            else:
                logger.warning("Timeout menunggu file fisik selesai pada path: %s", current_subpath)
        else:
            logger.error("Gagal klik tombol Select All pada path: %s", current_subpath)
        return

    # 3. Rekursi (jika tidak ada file, telusuri subfolder)
    folders = bot.get_folder_names()
    for folder in folders:
        bot.click_folder(folder)
        logger.info("Masuk folder: %s", folder)
        # Kirim current_subpath yang diupdate (misal: "1993/01")
        next_subpath = os.path.join(current_subpath, folder)
        crawl_recursive(bot, root_data_dir, next_subpath, args, logger)
        bot.driver.back()
        time.sleep(3)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", help="Nama subfolder di dalam data/", default="results")
    parser.add_argument("--flat", action="store_true", help="Simpan langsung di data/[output]/ tanpa subfolder tahun/bulan")
    parser.add_argument("--headless", action="store_true", help="Jalankan browser di latar belakang")
    args = parser.parse_args()

    root_url = input("Masukkan Link Root: ").strip()
    start_year = input("Dari Tahun: ").strip()
    end_year = input("Sampai Tahun: ").strip()

    # Root download selalu di folder data/
    root_data_dir = get_base_data_path()
    
    bot = CopernicusScraper(root_data_dir, headless=args.headless)
    
    try:
        bot.driver.get(root_url)
        time.sleep(5)
        bot.hide_intrusive_elements()
        
        # [RECOVERY] Sebelum crawl, cek dan pulihkan file yang tertinggal dari crash sebelumnya
        print("\n[Recovery] Memeriksa file tertinggal dari proses sebelumnya...")
        if recover_orphaned_files(root_data_dir, args.output):
            print("[Recovery] File berhasil dipulihkan dan dipindahkan ke folder tujuan")
        else:
            print("[Recovery] Tidak ada file tertinggal, sistem siap dimulai")
        
        all_years = bot.get_folder_names()
        target_years = [y for y in all_years if y.isdigit() and int(start_year) <= int(y) <= int(end_year)]

        for year in target_years:
            logger, log_path = setup_year_logger(year)
            print(f"\n>>> Memproses Tahun: {year}")
            print(f"   [Log] Menulis log ke: {log_path}")
            logger.info("Mulai proses tahun %s", year)
            bot.click_folder(year)
            # Mulai rekursi dengan path awal adalah tahun
            crawl_recursive(bot, root_data_dir, year, args, logger)
            bot.driver.get(root_url)
            time.sleep(2)
            logger.info("Selesai proses tahun %s", year)

    finally:
        # Safety wait sebelum kill script
        print("\n[*] Sinkronisasi terakhir...")
        is_download_finished(root_data_dir, timeout=600)
        bot.quit()

if __name__ == "__main__":
    main()