import os
import time
from src.scraper import CopernicusScraper

def crawl_recursive(bot):
    print(f"\n[*] Scanning page: {bot.driver.current_url}")
    bot.debug_page_content() # TRIGGER DEBUG

    # 1. Cek apakah ada file yang bisa di-download
    if bot.has_files():
        print("   [!] File ditemukan! Mencoba proses download...")
        if bot.click_select_all():
            bot.click_download_button()
        else:
            print("   [!] Tombol 'All' tidak ditemukan atau disabled.")
        return

    # 2. Jika tidak ada file, cari folder
    folders = bot.get_folder_names()
    if not folders:
        print("   [!] Halaman kosong (tidak ada folder/file).")
        return

    # Salin list folder agar tidak bermasalah saat navigasi back
    folder_list = list(folders)
    for folder in folder_list:
        print(f"   Entering folder: {folder}")
        try:
            bot.click_folder(folder)
            crawl_recursive(bot)
            print(f"   Going back from: {folder}")
            bot.driver.back()
            time.sleep(3)
        except Exception as e:
            print(f"   [Error] Gagal masuk ke folder {folder}: {e}")
            bot.driver.refresh() # Coba refresh jika stuck

def main():
    root_url = input("Masukkan Link Root: ").strip()
    start_year = input("Dari Tahun: ").strip()
    end_year = input("Sampai Tahun: ").strip()

    download_dir = "data"
    if not os.path.exists(download_dir): os.makedirs(download_dir)

    bot = CopernicusScraper(download_dir)
    
    try:
        bot.driver.get(root_url)
        time.sleep(5) # Tunggu loading awal
        
        all_entries = bot.get_folder_names()
        target_years = [y for y in all_entries if y.isdigit() and int(start_year) <= int(y) <= int(end_year)]
        
        print(f"Target Tahun: {target_years}")

        for year in target_years:
            print(f"\n=== PROCESSING YEAR {year} ===")
            bot.click_folder(year)
            crawl_recursive(bot)
            bot.driver.get(root_url)
            time.sleep(3)

    finally:
        bot.quit()

if __name__ == "__main__":
    main()