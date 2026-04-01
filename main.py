import os
from src.scraper import CopernicusScraper

def crawl_recursive(bot):
    """
    Fungsi rekursif untuk masuk ke semua subfolder 
    sampai menemukan tombol download yang aktif.
    """
    # 1. Cek apakah di halaman ini kita bisa download
    if bot.is_download_page():
        bot.click_download_all()
        return # Selesai di cabang ini, kembali ke level atas

    # 2. Jika tidak bisa download, cari folder yang bisa dimasuki
    folders = bot.get_folder_names()
    
    if not folders:
        print("   [!] Tidak ada folder atau tombol download di halaman ini.")
        return

    for folder in folders:
        print(f"   Entering folder: {folder}")
        bot.click_folder(folder)
        
        # Rekursi: Masuk lebih dalam lagi
        crawl_recursive(bot)
        
        # Setelah selesai di dalam, kembali ke folder induk
        print(f"   Going back from: {folder}")
        bot.go_back()

def main():
    root_url = input("Masukkan Link Root Copernicus: ")
    start_year = int(input("Dari Tahun (e.g. 1997): "))
    end_year = int(input("Sampai Tahun (e.g. 2000): "))
    
    download_dir = os.path.join(os.getcwd(), "data")
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)

    bot = CopernicusScraper(download_dir)
    
    try:
        print(f"\n[*] Membuka Root URL: {root_url}")
        bot.navigate_to(root_url)
        
        # Ambil daftar tahun di root
        all_years = bot.get_folder_names()
        target_years = [y for y in all_years if y.isdigit() and start_year <= int(y) <= end_year]
        
        print(f"[*] Tahun yang akan diproses: {target_years}")

        for year in target_years:
            print(f"\n--- Memulai pemrosesan tahun: {year} ---")
            bot.click_folder(year)
            
            # Mulai penggalian otomatis ke dalam (Bulan -> Hari -> dst)
            crawl_recursive(bot)
            
            # Kembali ke Root untuk ganti tahun
            bot.navigate_to(root_url)
            print(f"--- Selesai tahun: {year} ---")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        print("\n[*] Scraper selesai. Menutup browser...")
        bot.quit()

if __name__ == "__main__":
    main()