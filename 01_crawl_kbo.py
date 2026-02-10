"""
KBO 공식 사이트에서 2024 / 2025 시즌 SSG 랜더스 타자 기록 수집
playwright를 이용한 크롤링 코드

실행 방법:
    pip install playwright pandas
    playwright install chromium
    python 01_crawl_kbo.py
"""

import asyncio
import os
import pandas as pd
from playwright.async_api import async_playwright


BASE_URL = "https://www.koreabaseball.com/Record/Player/HitterBasic/Basic1.aspx"
YEARS    = ["2024", "2025"]
TEAM     = "SSG"


async def select_filters(page, year: str):
    """연도, 팀 필터 선택"""
    await page.select_option('select:nth-of-type(1)', year)
    await page.wait_for_timeout(800)
    await page.select_option('select:nth-of-type(3)', TEAM)
    await page.wait_for_timeout(1000)


async def parse_table(page, year: str) -> list[dict]:
    """현재 페이지의 타자 기록 테이블 파싱"""
    rows = await page.query_selector_all('table tbody tr')
    records = []

    for row in rows:
        cells = await row.query_selector_all('td')
        if len(cells) < 14:
            continue

        texts = [await c.inner_text() for c in cells]
        records.append({
            'season': year,
            '선수명':  texts[1].strip(),
            '팀':      texts[2].strip(),
            'AVG':     texts[3].strip(),
            'G':       texts[4].strip(),
            'PA':      texts[5].strip(),
            'AB':      texts[6].strip(),
            'R':       texts[7].strip(),
            'H':       texts[8].strip(),
            '2B':      texts[9].strip(),
            '3B':      texts[10].strip(),
            'HR':      texts[11].strip(),
            'TB':      texts[12].strip(),
            'RBI':     texts[13].strip(),
        })

    return records


async def crawl_all_pages(page, year: str) -> list[dict]:
    """전체 페이지 순회 수집 (최대 5페이지)"""
    records = await parse_table(page, year)

    for page_num in range(2, 6):
        btn = await page.query_selector(f'a[href*="btnNo{page_num}"]')
        if not btn:
            break
        await btn.click()
        await page.wait_for_timeout(1200)
        new_records = await parse_table(page, year)
        if not new_records:
            break
        records += new_records

    return records


async def crawl_season(browser, year: str) -> pd.DataFrame:
    """특정 시즌 데이터 수집 및 전처리"""
    page = await browser.new_page()
    print(f"\n[{year}] KBO 사이트 접속 중...")
    await page.goto(BASE_URL, wait_until="domcontentloaded")
    await page.wait_for_timeout(1000)

    print(f"[{year}] 필터 설정 (팀: {TEAM})...")
    await select_filters(page, year)

    print(f"[{year}] 데이터 수집 중...")
    records = await crawl_all_pages(page, year)
    await page.close()

    # DataFrame 변환 및 SSG 필터링
    df = pd.DataFrame(records)
    df = df[df['팀'] == 'SSG'].reset_index(drop=True)

    # 숫자형 변환
    num_cols = ['AVG', 'G', 'PA', 'AB', 'R', 'H', '2B', '3B', 'HR', 'TB', 'RBI']
    for col in num_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    print(f"[{year}] ✅ SSG 선수 {len(df)}명 수집 완료")
    return df


async def main():
    os.makedirs("data", exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        all_dfs = []
        for year in YEARS:
            df = await crawl_season(browser, year)
            df.to_csv(f'data/ssg_hitters_{year}_raw.csv', index=False, encoding='utf-8-sig')
            all_dfs.append(df)

        await browser.close()

    # 두 시즌 합치기
    df_all = pd.concat(all_dfs, ignore_index=True)
    df_all.to_csv('data/ssg_hitters_all.csv', index=False, encoding='utf-8-sig')

    # 200타석 이상 필터
    df_qualified = df_all[df_all['PA'] >= 200].copy()
    df_qualified.to_csv('data/ssg_hitters_qualified.csv', index=False, encoding='utf-8-sig')

    print("\n" + "="*50)
    print("📊 수집 결과 요약")
    print("="*50)
    for year in YEARS:
        subset = df_qualified[df_qualified['season'] == year]
        print(f"\n▶ {year} 시즌 (200타석 이상: {len(subset)}명)")
        print(subset[['선수명', 'G', 'PA', 'AVG', 'HR', 'RBI']].to_string(index=False))

    print("\n💾 data/ 폴더에 CSV 저장 완료")
    print("  - ssg_hitters_2024_raw.csv")
    print("  - ssg_hitters_2025_raw.csv")
    print("  - ssg_hitters_all.csv")
    print("  - ssg_hitters_qualified.csv")


if __name__ == "__main__":
    asyncio.run(main())
