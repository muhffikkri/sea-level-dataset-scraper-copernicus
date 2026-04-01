import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

class CopernicusScraper:
    def __init__(self, download_path):
        options = webdriver.ChromeOptions()
        prefs = {
            "download.default_directory": download_path,
            "download.prompt_for_download": False,
            "directory_upgrade": True
        }
        options.add_experimental_option("prefs", prefs)
        # options.add_argument("--headless") 
        
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        self.wait = WebDriverWait(self.driver, 10)

    def navigate_to(self, url):
        self.driver.get(url)

    def get_folder_names(self):
        """Mengambil nama-nama folder yang ada di halaman saat ini"""
        try:
            # Menunggu sampai entry muncul
            xpath = "//div[contains(@class, 'entry') and contains(@class, 'dir')]"
            self.wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
            elements = self.driver.find_elements(By.XPATH, xpath)
            # Ambil text dari span di dalam folder entry
            return [el.text.strip() for el in elements if el.text.strip() != ""]
        except:
            return []

    def is_download_page(self):
        """Cek apakah tombol Download sudah aktif (bukan disabled)"""
        try:
            # Mencari tombol download yang tidak memiliki class 'disabled'
            # Kita cari teks yang mengandung 'Download'
            btn_xpath = "//div[contains(@class, 'wk-button') and contains(text(), 'Download') and not(contains(@class, 'disabled'))]"
            elements = self.driver.find_elements(By.XPATH, btn_xpath)
            return len(elements) > 0
        except:
            return False

    def click_folder(self, folder_name):
        """Klik folder berdasarkan teks namanya"""
        xpath = f"//div[contains(@class, 'entry')]//span[text()='{folder_name}']"
        folder = self.wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
        folder.click()
        time.sleep(2) # Beri jeda loading transisi halaman

    def click_download_all(self):
        """Klik tombol Download Utama"""
        btn_xpath = "//div[contains(@class, 'wk-button') and contains(text(), 'Download') and not(contains(@class, 'disabled'))]"
        btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, btn_xpath)))
        print(f"   --> Menemukan tombol: {btn.text}. Mengunduh...")
        btn.click()
        # Tunggu sebentar agar proses download mulai sebelum pindah halaman
        time.sleep(5) 

    def go_back(self):
        self.driver.back()
        time.sleep(2)

    def quit(self):
        self.driver.quit()