import os
import time
import argparse
import logging
from src.scraper import CopernicusScraper
from src.utils import get_base_data_path, is_download_finished, move_files_to_target, check_exists

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

    # 1. Skip logic (Hanya jika tidak flat)
    if not args.flat and check_exists(target_path):
        print(f"   [Skip] {current_subpath} sudah ada.")
        logger.info("Skip path existing: %s", current_subpath)
        return

    # 2. Logika Download
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
                # Pindahkan dari data/ ke folder tujuan (misal data/results/1993/01)
                move_files_to_target(root_data_dir, target_path)
                print(f"   [Done] Tersimpan di: {target_path}")
                logger.info("Download selesai dan dipindahkan ke: %s", target_path)
            else:
                logger.warning("Timeout menunggu file fisik selesai pada path: %s", current_subpath)
        else:
            logger.error("Gagal klik tombol Select All pada path: %s", current_subpath)
        return

    # 3. Rekursi
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