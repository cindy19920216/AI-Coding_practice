# -*- coding: utf-8 -*-
import asyncio
import csv
from telethon import TelegramClient
from datetime import datetime, timezone, timedelta
from dateutil.relativedelta import relativedelta
import os
import pandas as pd
import requests
from bs4 import BeautifulSoup
from collections import Counter
import re
import time

# 1. API 정보
API_ID = 31550175
API_HASH = '99c242608a502e055c984bc5898c8a3f'

# 로컬 저장 경로
SAVE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'telegram_data')

SESSION_NAME = os.path.join(SAVE_PATH, 'stock_test_session')

# 2. 분석할 채널 리스트
CHANNELS = [
    'Yeouido_Lab', 'corevalue', 'gaoshoukorea', 'bornlupin',
    'ym_research', 'bufkr', 'one_going', 'bumgore',
    'HS_academy', 'jeilstock'
]

# 3. 수집 기간 설정 (2025년 6월부터 현재까지 월 단위)
start_base = datetime(2025, 6, 1, tzinfo=timezone.utc)
end_base = datetime.now(timezone.utc)

monthly_ranges = []
current = start_base
while current < end_base:
    month_start = current
    month_end = current + relativedelta(months=1)
    monthly_ranges.append((month_start, month_end))
    current = month_end

async def crawl_monthly():
    os.makedirs(SAVE_PATH, exist_ok=True)

    async with TelegramClient(SESSION_NAME, API_ID, API_HASH) as client:
        for m_start, m_end in monthly_ranges:
            month_str = m_start.strftime('%Y-%m')
            print(f"\n[{month_str}] 데이터 수집 시작...")

            file_name = os.path.join(SAVE_PATH, f'telegram_data_{month_str}.csv')

            with open(file_name, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Channel', 'Date', 'Message'])

                for channel_username in CHANNELS:
                    print(f"  - @{channel_username} 수집 중...", end=" ")
                    count = 0
                    try:
                        async for message in client.iter_messages(
                            channel_username,
                            offset_date=m_end
                        ):
                            if message.date < m_start:
                                break
                            if message.text:
                                clean_text = message.text.replace('\n', ' ').strip()
                                writer.writerow([
                                    channel_username,
                                    message.date.strftime('%Y-%m-%d %H:%M:%S'),
                                    clean_text
                                ])
                                count += 1
                        print(f"({count}건 완료)")
                        await asyncio.sleep(0.5)

                    except Exception as e:
                        print(f"(오류: {e})")

            print(f"[완료] {month_str} 파일 저장: {file_name}")
            await asyncio.sleep(2)

# ── 네이버 테마 분석 ──────────────────────────────────────

def get_naver_themes():
    print("네이버 증권에서 최신 테마 리스트 수집 중...")
    theme_list = []
    headers = {'User-Agent': 'Mozilla/5.0'}
    for page in range(1, 8):
        url = f"https://finance.naver.com/sise/theme.naver?&page={page}"
        res = requests.get(url, headers=headers)  # 수정: 잘못된 'html.parser' 인자 제거
        soup = BeautifulSoup(res.text, 'html.parser')
        tags = soup.select('td.col_type1 a')
        if not tags:
            break
        for tag in tags:
            name = re.sub(r'\(.*\)', '', tag.text).strip()
            if name:
                theme_list.append(name)
    return list(set(theme_list))

def run_basic_analysis():
    theme_keywords = get_naver_themes()
    print(f"총 {len(theme_keywords)}개의 테마 키워드 로드 완료.")

    try:
        all_files = [
            os.path.join(SAVE_PATH, f)
            for f in os.listdir(SAVE_PATH)
            if f.startswith('telegram_data_') and f.endswith('.csv')
        ]

        if not all_files:
            raise FileNotFoundError("텔레그램 데이터 파일을 찾을 수 없습니다.")

        list_df = [pd.read_csv(file) for file in all_files]
        df = pd.concat(list_df, ignore_index=True)
        df['Date'] = pd.to_datetime(df['Date'])

        all_messages = " ".join(df['Message'].astype(str))

        found_themes = []
        for theme in theme_keywords:
            count = all_messages.count(theme)
            if count > 0:
                found_themes.extend([theme] * count)

        top_5 = Counter(found_themes).most_common(5)

        print("\n" + "="*40)
        print("최근 수집 데이터 기반 주도 테마 TOP 5")
        print("="*40)
        for i, (name, count) in enumerate(top_5):
            print(f"{i+1}위: {name} ({count}회 언급)")
        print("="*40)

    except FileNotFoundError as e:
        print(e)
        print("크롤링 코드가 먼저 성공적으로 실행되었는지 확인하세요.")
    except Exception as e:
        print(f"데이터 분석 중 오류 발생: {e}")

# ── 종목명 매칭 정밀 테마 분석 ───────────────────────────

def get_advanced_theme_map():
    print("네이버 증권에서 테마 및 종목 정보를 수집 중입니다...")
    headers = {'User-Agent': 'Mozilla/5.0'}
    theme_to_stocks = {}

    for page in range(1, 8):
        url = f"https://finance.naver.com/sise/theme.naver?&page={page}"
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        links = soup.select('td.col_type1 a')

        for link in links:
            theme_name = re.sub(r'\(.*\)', '', link.text).strip()
            detail_url = "https://finance.naver.com/sise/" + link['href']

            try:
                d_res = requests.get(detail_url, headers=headers)
                d_soup = BeautifulSoup(d_res.text, 'html.parser')
                stocks = [s.text.strip() for s in d_soup.select('td.name a')]
                theme_to_stocks[theme_name] = stocks
                time.sleep(0.2)
            except Exception:
                continue
    return theme_to_stocks

def run_advanced_analysis():
    theme_map = get_advanced_theme_map()

    try:
        all_files = [
            os.path.join(SAVE_PATH, f)
            for f in os.listdir(SAVE_PATH)
            if f.startswith('telegram_data_') and f.endswith('.csv')
        ]

        if not all_files:
            raise FileNotFoundError("텔레그램 데이터 파일을 찾을 수 없습니다.")

        list_df = [pd.read_csv(file) for file in all_files]
        df = pd.concat(list_df, ignore_index=True)
        df['Message'] = df['Message'].astype(str)

        results = []
        for msg in df['Message']:
            matched_themes = []
            for theme, stocks in theme_map.items():
                if theme in msg:
                    matched_themes.append(theme)
                for stock in stocks:
                    if len(stock) > 1 and stock in msg:
                        matched_themes.append(theme)
                        break
            results.extend(matched_themes)

        stopwords = ['증권']
        final_counts = Counter([t for t in results if t not in stopwords])

        print("\n" + "="*45)
        print("종목명 매칭을 적용한 정밀 테마 분석 결과")
        print("="*45)
        for i, (name, count) in enumerate(final_counts.most_common(10)):
            print(f"{i+1}위: {name} ({count}회 포착)")
        print("="*45)

    except FileNotFoundError as e:
        print(e)
        print("크롤링 코드가 먼저 성공적으로 실행되었는지 확인하세요.")
    except Exception as e:
        print(f"데이터 분석 중 오류 발생: {e}")


if __name__ == '__main__':
    # Step 1: 텔레그램 데이터 수집
    asyncio.run(crawl_monthly())

    # Step 2: 기본 테마 분석
    run_basic_analysis()

    # Step 3: 종목 매칭 정밀 분석
    run_advanced_analysis()
