import os
import time
import argparse
from src.scraper import CopernicusScraper
from src.utils import get_base_data_path, is_download_finished, move_files_to_target, check_exists

def crawl_recursive(bot, root_data_dir, current_subpath, args):
    # Path tujuan: data/[output]/[tahun]/[bulan] atau data/[output]/
    if args.flat:
        target_path = os.path.join(root_data_dir, args.output)
    else:
        target_path = os.path.join(root_data_dir, args.output, current_subpath)

    # 1. Skip logic (Hanya jika tidak flat)
    if not args.flat and check_exists(target_path):
        print(f"   [Skip] {current_subpath} sudah ada.")
        return

    # 2. Logika Download
    if bot.has_files():
        print(f"   [!] File ditemukan di {current_subpath}. Mendownload...")
        if bot.click_select_all():
            bot.click_download_button()
            
            # Tunggu teks "Downloading" hilang dari UI
            bot.wait_until_download_ready()
            
            # Tunggu fisik file selesai di folder data/
            if is_download_finished(root_data_dir):
                # Pindahkan dari data/ ke folder tujuan (misal data/results/1993/01)
                move_files_to_target(root_data_dir, target_path)
                print(f"   [Done] Tersimpan di: {target_path}")
        return

    # 3. Rekursi
    folders = bot.get_folder_names()
    for folder in folders:
        bot.click_folder(folder)
        # Kirim current_subpath yang diupdate (misal: "1993/01")
        next_subpath = os.path.join(current_subpath, folder)
        crawl_recursive(bot, root_data_dir, next_subpath, args)
        bot.driver.back()
        time.sleep(3)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", help="Nama subfolder di dalam data/", default="results")
    parser.add_argument("--flat", action="store_true", help="Simpan langsung di data/[output]/ tanpa subfolder tahun/bulan")
    args = parser.parse_args()

    root_url = input("Masukkan Link Root: ").strip()
    start_year = input("Dari Tahun: ").strip()
    end_year = input("Sampai Tahun: ").strip()

    # Root download selalu di folder data/
    root_data_dir = get_base_data_path()
    
    bot = CopernicusScraper(root_data_dir)
    
    try:
        bot.driver.get(root_url)
        time.sleep(5)
        
        all_years = bot.get_folder_names()
        target_years = [y for y in all_years if y.isdigit() and int(start_year) <= int(y) <= int(end_year)]

        for year in target_years:
            print(f"\n>>> Memproses Tahun: {year}")
            bot.click_folder(year)
            # Mulai rekursi dengan path awal adalah tahun
            crawl_recursive(bot, root_data_dir, year, args)
            bot.driver.get(root_url)
            time.sleep(2)

    finally:
        # Safety wait sebelum kill script
        print("\n[*] Sinkronisasi terakhir...")
        is_download_finished(root_data_dir, timeout=600)
        bot.quit()

if __name__ == "__main__":
    main()