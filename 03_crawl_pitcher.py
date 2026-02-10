"""
KBO 공식 사이트에서 2024 / 2025 시즌 SSG 랜더스 투수 기록 수집
playwright를 이용한 크롤링 코드

실행 방법:
    python 03_crawl_pitcher.py
"""

import asyncio
import os
import pandas as pd
from playwright.async_api import async_playwright


BASE_URL = "https://www.koreabaseball.com/Record/Player/PitcherBasic/Basic1.aspx"
YEARS    = ["2024", "2025"]
TEAM     = "SSG"


def parse_ip(ip_str: str) -> float:
    """'180 2/3' → 180.67 형식으로 변환"""
    ip_str = str(ip_str).strip()
    if ' ' in ip_str:
        parts = ip_str.split()
        whole = float(parts[0])
        frac_map = {'1/3': 0.33, '2/3': 0.67}
        return whole + frac_map.get(parts[1], 0)
    return float(ip_str) if ip_str else 0.0


async def select_filters(page, year: str):
    """연도, 팀 필터 선택"""
    await page.select_option('select:nth-of-type(1)', year)
    await page.wait_for_timeout(800)
    await page.select_option('select:nth-of-type(3)', TEAM)
    await page.wait_for_timeout(1000)


async def parse_table(page, year: str) -> list[dict]:
    """현재 페이지 투수 기록 파싱"""
    rows = await page.query_selector_all('table tbody tr')
    records = []

    for row in rows:
        cells = await row.query_selector_all('td')
        if len(cells) < 18:
            continue

        texts = [await c.inner_text() for c in cells]
        records.append({
            'season': year,
            '선수명': texts[1].strip(),
            '팀':     texts[2].strip(),
            'ERA':    texts[3].strip(),
            'G':      texts[4].strip(),
            'W':      texts[5].strip(),
            'L':      texts[6].strip(),
            'SV':     texts[7].strip(),
            'HLD':    texts[8].strip(),
            'WPCT':   texts[9].strip(),
            'IP':     texts[10].strip(),
            'H':      texts[11].strip(),
            'HR':     texts[12].strip(),
            'BB':     texts[13].strip(),
            'HBP':    texts[14].strip(),
            'SO':     texts[15].strip(),
            'R':      texts[16].strip(),
            'ER':     texts[17].strip(),
            'WHIP':   texts[18].strip() if len(texts) > 18 else '',
        })

    return records


async def crawl_all_pages(page, year: str) -> list[dict]:
    """전체 페이지 순회 (최대 5페이지)"""
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
    """특정 시즌 투수 데이터 수집"""
    page = await browser.new_page()
    print(f"\n[{year}] 투수 기록 수집 중...")
    await page.goto(BASE_URL, wait_until="domcontentloaded")
    await page.wait_for_timeout(1000)

    await select_filters(page, year)
    records = await crawl_all_pages(page, year)
    await page.close()

    df = pd.DataFrame(records)
    df = df[df['팀'] == 'SSG'].reset_index(drop=True)

    # 숫자형 변환
    num_cols = ['ERA', 'G', 'W', 'L', 'SV', 'HLD', 'WPCT',
                'H', 'HR', 'BB', 'HBP', 'SO', 'R', 'ER', 'WHIP']
    for col in num_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # IP 변환 ('180 2/3' → 180.67)
    df['IP'] = df['IP'].apply(parse_ip)

    print(f"[{year}] ✅ SSG 투수 {len(df)}명 수집 완료")
    return df


async def main():
    os.makedirs("data", exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        all_dfs = []
        for year in YEARS:
            df = await crawl_season(browser, year)
            df.to_csv(f'data/ssg_pitchers_{year}_raw.csv', index=False, encoding='utf-8-sig')
            all_dfs.append(df)

        await browser.close()

    df_all = pd.concat(all_dfs, ignore_index=True)
    df_all.to_csv('data/ssg_pitchers_all.csv', index=False, encoding='utf-8-sig')

    # 최소 이닝 필터 (선발: 30이닝+, 불펜: 15이닝+)
    df_qualified = df_all[df_all['IP'] >= 15].copy()
    df_qualified.to_csv('data/ssg_pitchers_qualified.csv', index=False, encoding='utf-8-sig')

    print("\n" + "="*50)
    print("📊 수집 결과 요약")
    print("="*50)
    for year in YEARS:
        subset = df_qualified[df_qualified['season'] == int(year)]
        print(f"\n▶ {year} 시즌 (15이닝 이상: {len(subset)}명)")
        print(subset[['선수명', 'G', 'IP', 'ERA', 'W', 'L', 'SV', 'HLD']].to_string(index=False))

    print("\n💾 data/ 폴더에 CSV 저장 완료")
    print("  - ssg_pitchers_2024_raw.csv")
    print("  - ssg_pitchers_2025_raw.csv")
    print("  - ssg_pitchers_all.csv")
    print("  - ssg_pitchers_qualified.csv")


if __name__ == "__main__":
    asyncio.run(main())
