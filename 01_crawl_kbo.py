"""
KBO 공식 사이트에서 2025 시즌 SSG 랜더스 타자 기록 수집
playwright를 이용한 크롤링 코드

실행 방법:
    pip install playwright pandas
    playwright install chromium
    python 01_crawl_kbo.py
"""

import asyncio
import pandas as pd
from playwright.async_api import async_playwright


BASE_URL = "https://www.koreabaseball.com/Record/Player/HitterBasic/Basic1.aspx"
YEAR = "2025"
TEAM = "SSG"


async def select_filters(page):
    """연도, 팀 필터 선택"""
    # 연도 선택
    await page.select_option('select:nth-of-type(1)', YEAR)
    await page.wait_for_timeout(800)

    # 팀 선택 (SSG)
    await page.select_option('select:nth-of-type(3)', TEAM)
    await page.wait_for_timeout(1000)


async def parse_table(page) -> list[dict]:
    """현재 페이지의 타자 기록 테이블 파싱"""
    rows = await page.query_selector_all('table tbody tr')
    records = []

    for row in rows:
        cells = await row.query_selector_all('td')
        if len(cells) < 14:
            continue

        texts = [await c.inner_text() for c in cells]
        records.append({
            '순위':   texts[0].strip(),
            '선수명': texts[1].strip(),
            '팀':     texts[2].strip(),
            'AVG':    texts[3].strip(),
            'G':      texts[4].strip(),
            'PA':     texts[5].strip(),
            'AB':     texts[6].strip(),
            'R':      texts[7].strip(),
            'H':      texts[8].strip(),
            '2B':     texts[9].strip(),
            '3B':     texts[10].strip(),
            'HR':     texts[11].strip(),
            'TB':     texts[12].strip(),
            'RBI':    texts[13].strip(),
        })

    return records


async def crawl_page2(page) -> list[dict]:
    """2페이지 이동 후 파싱"""
    next_btn = await page.query_selector('a[href*="btnNo2"]')
    if next_btn:
        await next_btn.click()
        await page.wait_for_timeout(1200)
        return await parse_table(page)
    return []


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        print(f"[1/4] KBO 사이트 접속 중...")
        await page.goto(BASE_URL, wait_until="domcontentloaded")
        await page.wait_for_timeout(1000)

        print(f"[2/4] 필터 설정 (연도: {YEAR}, 팀: {TEAM})...")
        await select_filters(page)

        print(f"[3/4] 1페이지 데이터 수집 중...")
        records = await parse_table(page)

        print(f"[4/4] 2페이지 데이터 수집 중...")
        records += await crawl_page2(page)

        await browser.close()

    # SSG 선수만 필터링
    df = pd.DataFrame(records)
    df = df[df['팀'] == 'SSG'].reset_index(drop=True)

    # 숫자형 변환
    num_cols = ['AVG', 'G', 'PA', 'AB', 'R', 'H', '2B', '3B', 'HR', 'TB', 'RBI']
    for col in num_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # 최소 타석 필터 (규정 타석: 경기수 × 3.1 ≈ 144 × 3.1 = 446)
    df_qualified = df[df['PA'] >= 200].copy()  # 분석 포함 기준은 200타석 이상

    print(f"\n✅ 수집 완료: SSG 선수 총 {len(df)}명 (200타석 이상: {len(df_qualified)}명)")
    print(df_qualified[['선수명', 'G', 'PA', 'AB', 'AVG', 'HR', 'RBI', 'TB']].to_string(index=False))

    # CSV 저장
    df.to_csv('data/ssg_hitters_raw.csv', index=False, encoding='utf-8-sig')
    df_qualified.to_csv('data/ssg_hitters_qualified.csv', index=False, encoding='utf-8-sig')
    print("\n💾 data/ 폴더에 CSV 저장 완료")


if __name__ == "__main__":
    import os
    os.makedirs("data", exist_ok=True)
    asyncio.run(main())
