import sys
import os
import csv
import time
import pandas as pd
import requests
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from datetime import datetime
from collections import Counter
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QComboBox, QTextEdit, QMessageBox, QFileDialog, QProgressBar, QDoubleSpinBox
)
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

# 로그인 정보
username = ''
password = ''

class CutyKidsExtractor(QWidget):
    def __init__(self):
        super().__init__()
        self.driver = None
        self.setup_ui()
        self.last_csv_folder = ""  # CSV 파일 저장 경로를 저장하는 변수
        self.product_data = []  # 추출된 제품 데이터를 저장하는 리스트

    def setup_ui(self):
        """UI 구성 및 초기화"""
        self.setWindowTitle("큐티키즈 제품 정보 추출기")
        layout = QVBoxLayout()

        # 로그인 UI
        layout.addWidget(QLabel("아이디"))
        self.username_input = QLineEdit()
        layout.addWidget(self.username_input)

        layout.addWidget(QLabel("비밀번호"))
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.password_input)

        self.login_button = QPushButton("로그인")
        self.login_button.clicked.connect(self.login)
        layout.addWidget(self.login_button)

        # 브랜드 선택 및 추가 UI
        self.brand_combo = QComboBox()
        self.brand_combo.addItems(["디그린", "미니봉봉", "벨라밤비나"])
        layout.addWidget(QLabel("브랜드 선택"))
        layout.addWidget(self.brand_combo)

        self.brand_input = QLineEdit()
        self.brand_input.setPlaceholderText("원하는 브랜드가 없을 시 여기에 입력")
        layout.addWidget(self.brand_input)

        self.add_brand_button = QPushButton("브랜드 추가")
        self.add_brand_button.clicked.connect(self.add_brand)
        layout.addWidget(self.add_brand_button)

        # 갯수 추출 및 카운트 결과 표시 UI
        self.extract_count_button = QPushButton("갯수 추출")
        self.extract_count_button.clicked.connect(self.extract_counts)
        layout.addWidget(self.extract_count_button)

        self.count_result_text = QTextEdit()
        self.count_result_text.setReadOnly(True)
        layout.addWidget(QLabel("카운트 결과"))
        layout.addWidget(self.count_result_text)

        # 추출 항목 선택 및 추출 UI
        self.select_input = QLineEdit()
        self.select_input.setPlaceholderText("추출할 번호를 입력하세요")
        layout.addWidget(QLabel("추출할 제품 번호 선택"))
        layout.addWidget(self.select_input)

        # 가격 조정 옵션 UI
        layout.addWidget(QLabel("시장가에 곱할 숫자 또는 더할 금액 입력"))
        self.percentage_input = QDoubleSpinBox()
        self.percentage_input.setRange(0.0, 100.0)
        self.percentage_input.setValue(1.0)  # 기본값을 1로 설정
        layout.addWidget(self.percentage_input)

        self.addition_input = QLineEdit()
        self.addition_input.setPlaceholderText("추가할 금액 (원)")
        layout.addWidget(self.addition_input)

        self.extract_button = QPushButton("추출")
        self.extract_button.clicked.connect(self.extract_data)
        layout.addWidget(self.extract_button)

        # 진행 바
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        # 이미지 다운로드 UI
        self.select_file_button = QPushButton("CSV 파일 선택 및 이미지 다운로드")
        self.select_file_button.clicked.connect(self.open_file_dialog)
        layout.addWidget(self.select_file_button)

        self.status_label = QLabel("파일이 선택되지 않았습니다.")
        layout.addWidget(self.status_label)

        self.setLayout(layout)

    def login(self):
        """웹 드라이버를 초기화하고 큐티키즈 웹사이트에 로그인"""
        if not self.driver:
            self.driver = webdriver.Chrome()
        self.driver.get("http://www.cutykids.com/index.php")
        WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.NAME, "am_id")))

        self.driver.find_element(By.NAME, "am_id").send_keys(self.username_input.text())
        self.driver.find_element(By.NAME, "am_pwd").send_keys(self.password_input.text())
        self.driver.find_element(By.NAME, "am_pwd").send_keys(Keys.RETURN)
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//a[contains(@href, 'order_out_list.php')]")))

        QMessageBox.information(self, "로그인 완료", "로그인이 완료되었습니다.")

    def add_brand(self):
        """브랜드 입력 후 추가 기능"""
        new_brand = self.brand_input.text().strip()
        if new_brand and new_brand not in [self.brand_combo.itemText(i) for i in range(self.brand_combo.count())]:
            self.brand_combo.addItem(new_brand)
            self.brand_input.clear()
            QMessageBox.information(self, "브랜드 추가", f"{new_brand}이(가) 추가되었습니다.")
        else:
            QMessageBox.warning(self, "브랜드 추가 오류", "유효한 브랜드명을 입력하세요.")

    def extract_counts(self):
        """브랜드별 등록일 및 계절별 제품 갯수 추출 및 표시"""
        brand_name = self.get_selected_brand_name()
        dates, seasons, product_names, product_links = self.collect_dates_and_seasons(brand_name)

        date_count, season_count = Counter(dates), Counter(seasons)
        self.display_counts(date_count, season_count)

    def get_selected_brand_name(self):
        """선택된 브랜드 이름을 가져옴"""
        return self.brand_input.text() if self.brand_input.text() else self.brand_combo.currentText()

    def collect_dates_and_seasons(self, brand_name):
        """등록일 및 계절 데이터를 웹에서 수집"""
        dates, seasons, product_names, product_links = [], [], [], []
        page_num = 1

        while True:
            url = f"http://www.cutykids.com/main.php?ai_id=&ai_no=&ac_id=&comp_no=&mode=&comp_name_s=&all_search=&all_search2=&search_price=&sort=&ary=&s_date=&gigan=&comp_head={brand_name}&pg={page_num}"
            self.driver.get(url)
            WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "small")))

            date_elements = self.driver.find_elements(By.XPATH,
                                                      "//div[@class='small' and contains(@style, 'color:#6a6a6a')]")
            season_elements = self.driver.find_elements(By.XPATH, "//font[@color='#383838']")
            name_elements = self.driver.find_elements(By.XPATH, "//font[@color='#6a6a6a']")
            link_elements = self.driver.find_elements(By.XPATH, "//a[contains(@href, 'list.php')]")

            if not date_elements and not season_elements and not name_elements:
                print(f"\n모든 페이지를 탐색 완료. 마지막 페이지: {page_num - 1}")
                break

            dates.extend([e.text.strip() for e in date_elements])
            seasons.extend([e.text.strip() for e in season_elements])
            product_names.extend([e.text.strip() for e in name_elements])
            product_links.extend([e.get_attribute("href") for e in link_elements if
                                  e.get_attribute("href").startswith("http://www.cutykids.com/list.php?ai_id=")])

            print(f"{page_num} 페이지 정보를 추출했습니다.")
            page_num += 1
            time.sleep(1)

        return dates, seasons, product_names, product_links

    def display_counts(self, date_count, season_count):
        """카운트 결과를 UI에 표시"""
        self.count_result_text.clear()
        self.count_mapping = {}
        count_index = 1

        for date, count in date_count.items():
            self.count_result_text.append(f"{count_index}. {date}: {count}개")
            self.count_mapping[count_index] = (date, count, 'date')
            count_index += 1

        for season, count in season_count.items():
            self.count_result_text.append(f"{count_index}. {season}: {count}개")
            self.count_mapping[count_index] = (season, count, 'season')
            count_index += 1

    def extract_data(self):
        """선택된 항목의 제품 정보를 추출하고 CSV 파일로 저장"""
        selected_index = self.get_selected_index()
        if selected_index is None:
            return

        selected_item, selected_count, item_type = self.count_mapping[selected_index]
        QMessageBox.information(self, "추출 시작", f"{selected_item} ({selected_count}개) 제품을 추출합니다.")

        selected_product_links = self.collect_product_links(selected_item, item_type, selected_count)
        self.progress_bar.setMaximum(len(selected_product_links))

        # 기존 데이터를 초기화하여 덮어쓰기 방식으로 변경
        self.product_data = []

        for i, product_link in enumerate(selected_product_links, 1):
            self.product_data.append(self.collect_product_data([product_link])[0])
            self.progress_bar.setValue(i)
            QApplication.processEvents()  # 진행 상황 업데이트

        self.adjust_prices(self.product_data)
        self.save_data_to_csv(self.product_data)
        self.progress_bar.setValue(len(selected_product_links))

    def get_selected_index(self):
        """선택된 번호를 가져옴"""
        try:
            return int(self.select_input.text())
        except (ValueError, KeyError):
            QMessageBox.warning(self, "추출 오류", "유효한 번호를 입력하세요.")
            return None

    def collect_product_links(self, selected_item, item_type, selected_count):
        """선택된 항목에 해당하는 제품 링크 수집"""
        dates, seasons, product_names, product_links = self.collect_dates_and_seasons(self.brand_combo.currentText())
        selected_product_links = []

        for date, season, name, link in zip(dates, seasons, product_names, product_links):
            if (item_type == 'date' and date == selected_item) or (item_type == 'season' and season == selected_item):
                selected_product_links.append(link)

        return selected_product_links[:selected_count]

    def collect_product_data(self, product_links):
        """제품 정보를 웹에서 수집"""
        product_data = []

        for i, url in enumerate(product_links, 1):
            try:
                print(f"\n{i}번째 제품 처리 중... URL: {url}")
                self.driver.get(url)
                time.sleep(2)

                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                product_data.append(self.parse_product_data(soup))
            except Exception as e:
                print(f"{i}번째 제품 처리 중 오류 발생: {e}")

        return product_data

    def parse_product_data(self, soup):
        """HTML 소스에서 제품 정보를 파싱"""
        product_name = soup.find('font', class_="text13").b.text.strip() if soup.find('font',
                                                                                      class_="text13") else "정보 없음"
        market_price = soup.find(string="공급가 :").find_next('font', color="ff6100").b.text.strip() if soup.find(
            string="공급가 :") else "정보 없음"
        size = soup.find(string="사이즈 :").find_next('td').text.strip() if soup.find(string="사이즈 :") else "정보 없음"
        color = soup.find('select', {'name': 'color'}).find('option').text.strip() if soup.find('select', {
            'name': 'color'}) else "정보 없음"
        registration_date = soup.find(string="등록일 :").find_next('td').text.strip() if soup.find(
            string="등록일 :") else "정보 없음"
        season_info = soup.find('div', style="float:left;")
        season = season_info.text.strip().split('(')[-1][:-1] if season_info else "정보 없음"
        center_div = soup.find('div', align="center")
        image_tags = center_div.find_all('img') if center_div else []
        image_url = image_tags[0]['src'] if image_tags else ""
        detail_image_count = len(image_tags)
        out_of_stock = "품절" if soup.find(string="품절") else "판매중"

        return {
            '브랜드': self.brand_combo.currentText(),
            '상품명': product_name,
            '시장가': market_price,
            '사이즈': size,
            '색상': color,
            '등록일': registration_date,
            '계절': season,
            '품절': out_of_stock,
            '이미지 링크': image_url,
            '이미지 총 갯수': detail_image_count
        }

    def adjust_prices(self, data):
        """시장가에 숫자를 곱하고 추가 금액을 더하여 판매가를 계산"""
        multiplier = self.percentage_input.value()
        try:
            addition = float(self.addition_input.text()) if self.addition_input.text() else 0.0
        except ValueError:
            QMessageBox.warning(self, "입력 오류", "추가할 금액은 숫자여야 합니다.")
            return

        for item in data:
            try:
                market_price = int(item['시장가'].replace(',', '').replace('원', '').strip())
                adjusted_price = market_price * multiplier + addition
                item['판매가'] = f"{adjusted_price:,.0f} 원"
            except ValueError:
                item['판매가'] = "정보 없음"

    def save_data_to_csv(self, data):
        """수집한 제품 정보를 CSV 파일로 저장"""
        today_date = time.strftime("%Y-%m-%d")
        brand_name = self.brand_combo.currentText()
        csv_folder = os.path.join(os.getcwd(), 'CUTYKIDS', 'CUTYKIDS_Data', 'CSV', brand_name)
        os.makedirs(csv_folder, exist_ok=True)
        csv_file_path = os.path.join(csv_folder, f"{brand_name}_{self.select_input.text()}_{today_date}.csv")

        # 파일 저장 경로 출력 (디버깅용)
        print(f"CSV 파일 저장 경로: {csv_file_path}")

        with open(csv_file_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
            fieldnames = ['브랜드', '상품명', '시장가', '판매가', '사이즈', '색상', '등록일', '계절', '품절', '이미지 링크', '이미지 총 갯수']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for row in data:
                writer.writerow(row)

        self.last_csv_folder = csv_folder  # 마지막 CSV 파일 경로 저장
        QMessageBox.information(self, "CSV 저장 완료", f"{csv_file_path} 파일로 저장되었습니다.")

    def open_file_dialog(self):
        default_directory = self.last_csv_folder if self.last_csv_folder else ""
        csv_file_path, _ = QFileDialog.getOpenFileName(self, "CSV 파일 선택", default_directory, "CSV files (*.csv)")
        if csv_file_path:
            self.status_label.setText(f"선택된 파일: {csv_file_path}")
            self.process_csv(csv_file_path)
        else:
            self.status_label.setText("파일이 선택되지 않았습니다.")

    def process_csv(self, csv_file_path):
        try:
            data = pd.read_csv(csv_file_path)

            today = datetime.today().strftime('%Y%m%d')
            brand_name = os.path.splitext(os.path.basename(csv_file_path))[0].split('_')[0]
            brand_folder = f"{brand_name}_{today}"
            output_folder = os.path.join("CUTYKIDS", "Image", brand_name, brand_folder)
            os.makedirs(output_folder, exist_ok=True)

            for index, row in data.iterrows():
                image_url = row.get('이미지 링크')
                if pd.notna(image_url):
                    try:
                        response = requests.get(image_url)
                        response.raise_for_status()
                        img = Image.open(BytesIO(response.content)).convert('RGBA')

                        img_width, img_height = img.size
                        font_size = int(min(img_width, img_height) * (3 / 100))
                        font_path = 'C:\\Windows\\Fonts\\malgunsl.ttf'
                        font = ImageFont.truetype(font_path, font_size)

                        draw = ImageDraw.Draw(img)
                        product_info = f"{row['상품명']}\n{row['판매가']}\n{row['사이즈']}\n{row['색상']}"
                        text_bbox = draw.textbbox((0, 0), product_info, font=font, spacing=5)
                        text_width = text_bbox[2] - text_bbox[0]
                        text_height = text_bbox[3] - text_bbox[1]
                        text_position = (img.width - text_width - 30, img.height - text_height - 30)

                        background_color = (255, 255, 240, 255)
                        draw.rectangle(
                            [text_position[0] - 5, text_position[1] - 5, text_position[0] + text_width + 5,
                             text_position[1] + text_height + 5],
                            fill=background_color
                        )
                        draw.multiline_text(text_position, product_info, fill='black', font=font, spacing=5)

                        output_image_path = os.path.join(output_folder, f"{row['상품명']}_{index}.png")
                        img.save(output_image_path, format='PNG')
                        print(f"이미지가 저장되었습니다: {output_image_path}")
                    except Exception as e:
                        print(f"이미지를 불러오는 중 오류가 발생했습니다 ({image_url}): {e}")

            QMessageBox.information(self, "작업 완료", f"이미지가 저장된 폴더: {output_folder}")
            os.startfile(output_folder)

        except Exception as e:
            QMessageBox.critical(self, "오류", f"파일을 처리하는 중 오류가 발생했습니다: {e}")

    def closeEvent(self, event):
        """위젯 종료 시 크롬 드라이버 종료"""
        if self.driver:
            self.driver.quit()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CutyKidsExtractor()
    window.show()
    sys.exit(app.exec())
