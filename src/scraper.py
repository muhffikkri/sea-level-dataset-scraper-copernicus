import time
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

class CopernicusScraper:
    def __init__(self, download_path):
        options = webdriver.ChromeOptions()
        # Masukkan path binary chrome jika masih error "binary not found"
        # options.binary_location = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        
        # Path absolut sangat disarankan untuk Windows
        abs_download_path = os.path.abspath(download_path)
        
        prefs = {
            "download.default_directory": abs_download_path,
            "download.prompt_for_download": False,
            "directory_upgrade": True,
            "safebrowsing.enabled": True,
            "profile.default_content_setting_values.automatic_downloads": 1, 
        }
    
        options.add_experimental_option("prefs", prefs)
        
        # Tambahkan argumen agar Chrome tidak memunculkan info bar "Chrome is being controlled..."
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)

        self.driver.execute_cdp_cmd("Page.setDownloadBehavior", {
            "behavior": "allow",
            "downloadPath": abs_download_path
        })
        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), 
            options=options
        )
        self.wait = WebDriverWait(self.driver, 15)

    def debug_page_content(self):
        """Mencetak status elemen di halaman untuk debugging"""
        print("\n--- DEBUG PAGE STATE ---")
        entries = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'entry')]")
        print(f"Total Entries ditemukan: {len(entries)}")
        
        for i, entry in enumerate(entries[:5]): # Tampilkan 5 pertama saja
            print(f"Entry {i}: Class='{entry.get_attribute('class')}' | Text='{entry.text.splitlines()[0] if entry.text else 'EMPTY'}'")
        
        buttons = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'wk-button')]")
        for btn in buttons:
            print(f"Button: '{btn.text}' | Disabled: {'disabled' in btn.get_attribute('class')}")
        print("------------------------\n")

    def get_folder_names(self):
        # Cari elemen yang punya class 'entry' dan 'dir'
        xpath = "//div[contains(@class, 'entry') and contains(@class, 'dir')]"
        elements = self.driver.find_elements(By.XPATH, xpath)
        return [el.text.strip() for el in elements if el.text.strip() != ""]

    def has_files(self):
        """Cek apakah ada file (bukan folder) di halaman ini"""
        xpath = "//div[contains(@class, 'entry') and contains(@class, 'file')]"
        return len(self.driver.find_elements(By.XPATH, xpath)) > 0

    def click_select_all(self):
        """Klik tombol 'All' untuk memilih semua file"""
        try:
            btn_all = self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//div[contains(@class, 'wk-button') and (text()='All' or text()='Select all') and not(contains(@class, 'disabled'))]")
            ))
            print("   [Action] Klik tombol 'All'...")
            btn_all.click()
            time.sleep(2) # Tunggu tombol Download aktif
            return True
        except:
            return False

    def wait_until_download_ready(self):
        """Menunggu sampai teks 'Downloading' hilang dari tombol"""
        print("   [Wait] Menunggu proses download browser selesai...")
        
        # 1. Tunggu tombol tidak lagi berkata 'Downloading'
        start_wait = time.time()
        while time.time() - start_wait < 1200: # Max 20 menit
            try:
                btn = self.driver.find_element(By.XPATH, "//div[contains(@class, 'wk-button') and contains(@class, 'primary')]")
                if "Downloading" not in btn.text:
                    break
            except:
                break # Tombol mungkin hilang/berubah saat pindah page
            time.sleep(10)
        
        # 2. Cek fisik file di folder (menggunakan helper dari utils)
        # Kita panggil di main.py saja agar lebih clean

    def click_download_button(self):
        """Klik tombol Download yang sudah aktif"""
        try:
            # Mencari tombol yang mengandung teks 'Download' dan tidak disabled
            xpath = "//div[contains(@class, 'wk-button') and contains(text(), 'Download') and not(contains(@class, 'disabled'))]"
            btn_download = self.wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
            print(f"   [Action] Klik {btn_download.text}...")
            btn_download.click()
            time.sleep(10) # Beri waktu lebih lama untuk inisiasi download file besar
            return True
        except Exception as e:
            print(f"   [Error] Gagal klik tombol download: {e}")
            return False

    def click_folder(self, folder_name):
        xpath = f"//div[contains(@class, 'entry')]//span[text()='{folder_name}']"
        folder = self.wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
        folder.click()
        time.sleep(3)

    def quit(self):
        self.driver.quit()