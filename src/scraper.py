import time
import os
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

class CopernicusScraper:
    def __init__(self, download_path, headless=False):
        options = webdriver.ChromeOptions()
        # Masukkan path binary chrome jika masih error "binary not found"
        # options.binary_location = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        
        # Path absolut sangat disarankan untuk Windows
        abs_download_path = os.path.abspath(download_path)
        self.download_path = abs_download_path
        self.headless = headless

        # Headless mode untuk menjalankan browser di background
        if headless:
            options.add_argument("--headless=new")
            options.add_argument("--window-size=1920,1080")
            options.add_argument("--disable-gpu")
        
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

        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), 
            options=options
        )

        # Chrome headless baru membutuhkan CDP command ini agar proses download diizinkan
        if headless:
            self.driver.execute_cdp_cmd("Page.setDownloadBehavior", {
                "behavior": "allow",
                "downloadPath": abs_download_path
            })

        self.wait = WebDriverWait(self.driver, 15)

    def hide_intrusive_elements(self):
        """Menghapus widget/popup yang berpotensi menghalangi klik elemen UI."""
        script = """
        var selectors = [
            'iframe[name="intercom-banner-frame"]',
            '.intercom-lightweight-app',
            '.intercom-launcher-frame',
            '#intercom-container'
        ];
        selectors.forEach(function(selector) {
            var elements = document.querySelectorAll(selector);
            elements.forEach(function(el) { el.remove(); });
        });
        """
        try:
            self.driver.execute_script(script)
        except Exception:
            pass

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
        """Klik tombol 'All' menggunakan JavaScript agar lebih tahan popup overlay."""
        self.hide_intrusive_elements()
        try:
            xpath = "//div[contains(@class, 'wk-button') and (text()='All' or text()='Select all') and not(contains(@class, 'disabled'))]"
            btn_all = self.wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
            print("   [Action] Klik tombol 'All'...")
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn_all)
            time.sleep(1)
            self.driver.execute_script("arguments[0].click();", btn_all)
            time.sleep(2) # Tunggu tombol Download aktif
            return True
        except Exception:
            return False

    def wait_until_download_ready(self):
        """Menunggu sampai teks 'Downloading' hilang dari tombol.

        Return True bila selesai/berpindah halaman, False bila timeout.
        """
        print("   [Wait] Menunggu proses download browser selesai...")
        
        # 1. Tunggu tombol tidak lagi berkata 'Downloading'
        start_wait = time.time()
        while time.time() - start_wait < 1200: # Max 20 menit
            try:
                btn = self.driver.find_element(By.XPATH, "//div[contains(@class, 'wk-button') and contains(@class, 'primary')]")
                if "Downloading" not in btn.text:
                    return True
            except:
                # Tombol mungkin hilang/berubah saat pindah page
                return True
            time.sleep(10)

        print("   [Timeout] Tombol masih berstatus downloading setelah 20 menit.")
        if self.headless:
            screenshot_path = self.save_timeout_screenshot(prefix="download_timeout")
            if screenshot_path:
                print(f"   [Debug] Screenshot timeout tersimpan: {screenshot_path}")
        return False
        
        # 2. Cek fisik file di folder (menggunakan helper dari utils)
        # Kita panggil di main.py saja agar lebih clean

    def click_download_button(self, retries=3, backoff_seconds=2):
        """Klik tombol Download dengan retry otomatis dan backoff eksponensial."""
        xpath = "//div[contains(@class, 'wk-button') and contains(text(), 'Download') and not(contains(@class, 'disabled'))]"

        for attempt in range(1, retries + 1):
            self.hide_intrusive_elements()
            try:
                btn_download = self.wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
                print(f"   [Action] Klik {btn_download.text}... (attempt {attempt}/{retries})")
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn_download)
                time.sleep(1)
                self.driver.execute_script("arguments[0].click();", btn_download)
                time.sleep(10) # Beri waktu lebih lama untuk inisiasi download file besar
                return True
            except Exception as e:
                print(f"   [Warn] Gagal klik download attempt {attempt}/{retries}: {e}")
                if attempt == retries:
                    break
                sleep_duration = backoff_seconds * (2 ** (attempt - 1))
                print(f"   [Retry] Coba lagi dalam {sleep_duration} detik...")
                time.sleep(sleep_duration)

        print("   [Error] Semua percobaan klik download gagal.")
        return False

    def save_timeout_screenshot(self, prefix="timeout"):
        """Simpan screenshot saat proses timeout untuk debugging mode headless."""
        try:
            screenshot_dir = os.path.join(self.download_path, "debug_screenshots")
            os.makedirs(screenshot_dir, exist_ok=True)
            filename = f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            full_path = os.path.join(screenshot_dir, filename)
            self.driver.save_screenshot(full_path)
            return full_path
        except Exception:
            return None

    def click_folder(self, folder_name):
        self.hide_intrusive_elements()
        xpath = f"//div[contains(@class, 'entry')]//span[text()='{folder_name}']"
        folder = self.wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", folder)
        time.sleep(1)
        self.driver.execute_script("arguments[0].click();", folder)
        time.sleep(3)

    def quit(self):
        self.driver.quit()