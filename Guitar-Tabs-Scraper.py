
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import os
import re

# 創建資料夾
folder_name = "songs"
if not os.path.exists(folder_name):
    os.makedirs(folder_name)

# 設置 Selenium WebDriver
options = webdriver.ChromeOptions()
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# 要抓取的網站起點
base_url = "https://www.91pu.com.tw"

# 訪問該網站
driver.get(base_url)

# 等待頁面加載完成，確保關鍵元素存在
WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.XPATH, "//a[@href]")))

# 獲取頁面源碼
html = driver.page_source
soup = BeautifulSoup(html, 'html.parser')

# 假設歌手列表頁面有每個歌手的鏈接
singer_links = soup.find_all('a', href=True)
valid_singer_links = [
    link['href'] for link in singer_links if 'singer' in link['href'] or 'song' in link['href']
]

# 寫入成功和失敗的 URL 檔案
with open("success_urls.txt", "a", encoding="utf-8") as success_file, \
     open("failed_urls.txt", "a", encoding="utf-8") as failed_file:

    def extract_sheet_music_links(page_html):
        """從列表頁面提取樂譜連結"""
        soup = BeautifulSoup(page_html, 'html.parser')
        music_links = [
            link['href'] for link in soup.find_all('a', href=True)
            if 'song' in link['href'] or 'sheet' in link['href']
        ]
        return music_links

    # 遍歷每個歌手的連結
    for singer_url in valid_singer_links:
        if not singer_url.startswith('http'):
            singer_url = base_url + singer_url

        driver.get(singer_url)

        # 獲取歌手頁面的 HTML
        try:
            WebDriverWait(driver, 50).until(EC.presence_of_element_located((By.XPATH, "//a[@href]")))
            page_html = driver.page_source
        except Exception as e:
            failed_file.write(f"無法加載歌手頁面: {singer_url} - Error: {str(e)}\n")
            print(f"無法加載歌手頁面: {singer_url} - Error: {str(e)}")
            continue

        # 提取樂譜列表中的連結
        sheet_music_links = extract_sheet_music_links(page_html)

        # 逐一抓取每個樂譜
        for song_url in sheet_music_links:
            if not song_url.startswith('http'):
                song_url = base_url + song_url

            driver.get(song_url)
            try:
                WebDriverWait(driver, 50).until(EC.presence_of_element_located((By.CLASS_NAME, 'tone')))
                song_html = driver.page_source
            except Exception as e:
                failed_file.write(f"無法加載樂譜頁面: {song_url} - Error: {str(e)}\n")
                print(f"無法加載樂譜頁面: {song_url} - Error: {str(e)}")
                failed_file.write(song_url + "\n")
                continue

            song_soup = BeautifulSoup(song_html, 'html.parser')

            # 標題和樂譜信息提取
            song_title = song_soup.find('h1', id='mtitle')
            if song_title:
                song_title = song_title.text.strip()
            else:
                failed_file.write(f"未能獲取歌曲標題: {song_url} - Error: No Title Found\n")
                print(f"未能獲取歌曲標題: {song_url}")
                failed_file.write(song_url + "\n")
                continue

            singer_name = "Unknown Singer"
            singer_tag = song_soup.find('p', string=lambda t: t and "演唱：" in t)
            if singer_tag:
                singer_name = singer_tag.text.split('：')[-1].strip()

            # 如果歌手名稱是 "Unknown Singer"，跳過並只記錄 URL
            if singer_name == "Unknown Singer":
                failed_file.write(f"歌手名稱為 'Unknown Singer': {song_url}\n")
                print(f"歌手名稱為 'Unknown Singer': {song_url}")
                failed_file.write(song_url + "\n")
                continue

            tone_info = song_soup.find('div', class_='tone')
            if tone_info:
                # 儲存為 HTML 文件
                safe_song_title = re.sub(r'[\/:*?"<>|]', '_', song_title)
                safe_singer_name = re.sub(r'[\/:*?"<>|]', '_', singer_name)
                filename = f'{safe_singer_name}_{safe_song_title}.html'

                song_filepath = os.path.join(folder_name, filename)
                with open(song_filepath, 'w', encoding='utf-8') as f:
                    f.write(f'''<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>{song_title}</title></head>
<body><h1>{song_title}</h1><p>演唱：{singer_name}</p>{tone_info}</body>
</html>''')

                success_file.write(song_url + "\n")
                print(f"儲存成功: {filename}")
            else:
                failed_file.write(f"未找到樂譜信息: {song_url} - Error: No Tone Info\n")
                print(f"未找到樂譜信息: {song_url}")
                failed_file.write(song_url + "\n")

# 關閉瀏覽器
driver.quit()
print("資料抓取完成！")
