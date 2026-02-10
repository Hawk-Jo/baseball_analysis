"""
2024 vs 2025 SSG 랜더스 투수진 분석
- 선발 / 불펜 자동 분류
- FIP 계산 (ERA에서 운 요소 제거)
- ERA vs FIP 비교
- 이닝 소화 효율 분석
- 2024 vs 2025 시즌 비교
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import os

plt.rcParams['font.family'] = 'Malgun Gothic'  # macOS: 'AppleGothic'
plt.rcParams['axes.unicode_minus'] = False

os.makedirs("output", exist_ok=True)

# KBO 2024 FIP 상수 (리그 평균 ERA 기반 근사치)
FIP_CONST = 3.20


# ════════════════════════════════════════════════
# 1. 데이터 로드 및 지표 계산
# ════════════════════════════════════════════════

def classify_role(row) -> str:
    """선발 / 불펜 분류
    - SV or HLD >= 1 → 불펜
    - G 대비 IP가 많고 (평균 5이닝+) → 선발
    """
    if row['SV'] >= 1 or row['HLD'] >= 1:
        return '불펜'
    if row['G'] > 0 and (row['IP'] / row['G']) >= 4.0:
        return '선발'
    return '불펜'


def calc_pitcher_metrics(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # 역할 분류
    df['역할'] = df.apply(classify_role, axis=1)

    # K/9: 9이닝당 삼진
    df['K9'] = df['SO'] / df['IP'] * 9

    # BB/9: 9이닝당 볼넷
    df['BB9'] = df['BB'] / df['IP'] * 9

    # K/BB: 삼진/볼넷 비율
    df['KBB'] = df['SO'] / df['BB'].replace(0, np.nan)

    # FIP = (13×HR + 3×(BB+HBP) - 2×SO) / IP + FIP_CONST
    df['FIP'] = (
        (13 * df['HR'] + 3 * (df['BB'] + df['HBP']) - 2 * df['SO'])
        / df['IP']
    ) + FIP_CONST

    # ERA - FIP: 양수면 ERA가 FIP보다 나쁨 (운이 나빴거나 수비 영향)
    df['ERA_FIP_diff'] = df['ERA'] - df['FIP']

    # 경기당 이닝 (이닝 소화 효율)
    df['IP_per_G'] = df['IP'] / df['G']

    return df


df_all = pd.read_csv("data/ssg_pitchers_qualified.csv")
df_all = calc_pitcher_metrics(df_all)

df_2024 = df_all[df_all['season'] == 2024].copy()
df_2025 = df_all[df_all['season'] == 2025].copy()

print(f"2024: {len(df_2024)}명 / 2025: {len(df_2025)}명")
print(df_all[['선수명', 'season', '역할', 'ERA', 'FIP', 'K9', 'BB9', 'IP_per_G']].to_string(index=False))


# ════════════════════════════════════════════════
# 2. 시각화 1: ERA vs FIP 비교 (운 요소 분석)
# ════════════════════════════════════════════════

for year, df_sub in [('2024', df_2024), ('2025', df_2025)]:
    if df_sub.empty:
        continue

    fig, ax = plt.subplots(figsize=(10, max(5, len(df_sub) * 0.55 + 1)))

    df_plot = df_sub.sort_values('ERA')
    x = np.arange(len(df_plot))
    width = 0.35

    bars1 = ax.bar(x - width/2, df_plot['ERA'], width,
                   label='ERA', color='#C8102E', alpha=0.85)
    bars2 = ax.bar(x + width/2, df_plot['FIP'], width,
                   label='FIP', color='#003087', alpha=0.85)

    ax.set_xticks(x)
    ax.set_xticklabels(
        [f"{n}\n({'선' if r=='선발' else '불'})" 
         for n, r in zip(df_plot['선수명'], df_plot['역할'])],
        fontsize=9
    )
    ax.set_title(f'{year} SSG 랜더스 투수 ERA vs FIP\n(FIP < ERA: 실제보다 운이 나빴던 투수)',
                 fontsize=13, fontweight='bold')
    ax.set_ylabel('방어율')
    ax.legend(fontsize=10)
    ax.axhline(y=df_sub['ERA'].mean(), color='#C8102E', linestyle='--',
               alpha=0.5, linewidth=1, label=f'ERA 평균 {df_sub["ERA"].mean():.2f}')

    # ERA-FIP 차이 표시
    for i, (era, fip) in enumerate(zip(df_plot['ERA'], df_plot['FIP'])):
        diff = era - fip
        color = 'red' if diff > 0.3 else ('blue' if diff < -0.3 else 'gray')
        ax.text(i, max(era, fip) + 0.05, f'{diff:+.2f}',
                ha='center', fontsize=8, color=color, fontweight='bold')

    plt.tight_layout()
    plt.savefig(f'output/pitcher_01_era_fip_{year}.png', dpi=150, bbox_inches='tight')
    plt.close()
    print(f"✅ output/pitcher_01_era_fip_{year}.png 저장 완료")


# ════════════════════════════════════════════════
# 3. 시각화 2: 이닝 소화 효율 (경기당 이닝)
# ════════════════════════════════════════════════

for year, df_sub in [('2024', df_2024), ('2025', df_2025)]:
    if df_sub.empty:
        continue

    df_starters = df_sub[df_sub['역할'] == '선발'].sort_values('IP_per_G', ascending=True)
    if df_starters.empty:
        continue

    fig, ax = plt.subplots(figsize=(9, max(4, len(df_starters) * 0.6 + 1)))

    colors = ['#C8102E' if v >= df_starters['IP_per_G'].mean() else '#A9A9A9'
              for v in df_starters['IP_per_G']]
    ax.barh(df_starters['선수명'], df_starters['IP_per_G'], color=colors, alpha=0.85)
    ax.axvline(x=df_starters['IP_per_G'].mean(), color='black', linestyle='--',
               linewidth=1.2, label=f'평균: {df_starters["IP_per_G"].mean():.2f}이닝')
    ax.axvline(x=5.0, color='navy', linestyle=':', linewidth=1,
               alpha=0.6, label='QS 기준 (6이닝 근사: 5.0)')

    for i, val in enumerate(df_starters['IP_per_G']):
        ax.text(val + 0.03, i, f'{val:.2f}', va='center', fontsize=9)

    ax.set_title(f'{year} SSG 선발진 경기당 이닝 소화\n(높을수록 불펜 부담 감소)',
                 fontsize=13, fontweight='bold')
    ax.set_xlabel('경기당 평균 투구 이닝 (IP/G)')
    ax.legend(fontsize=9)

    plt.tight_layout()
    plt.savefig(f'output/pitcher_02_ip_per_game_{year}.png', dpi=150, bbox_inches='tight')
    plt.close()
    print(f"✅ output/pitcher_02_ip_per_game_{year}.png 저장 완료")


# ════════════════════════════════════════════════
# 4. 시각화 3: K9 vs BB9 산점도 (제구 vs 탈삼진)
# ════════════════════════════════════════════════

fig, axes = plt.subplots(1, 2, figsize=(14, 6))

for ax, df_sub, year in zip(axes, [df_2024, df_2025], ['2024', '2025']):
    if df_sub.empty:
        ax.set_visible(False)
        continue

    colors_role = ['#C8102E' if r == '선발' else '#003087' for r in df_sub['역할']]
    ax.scatter(df_sub['BB9'], df_sub['K9'], c=colors_role,
               s=df_sub['IP'] * 0.8, alpha=0.75, edgecolors='gray', linewidth=0.5)

    for _, row in df_sub.iterrows():
        ax.annotate(row['선수명'], (row['BB9'], row['K9']),
                    textcoords="offset points", xytext=(5, 3), fontsize=8)

    ax.axvline(x=df_sub['BB9'].mean(), color='gray', linestyle=':', alpha=0.5)
    ax.axhline(y=df_sub['K9'].mean(), color='gray', linestyle=':', alpha=0.5)

    ax.set_xlabel('BB/9 (볼넷 — 낮을수록 좋음)', fontsize=10)
    ax.set_ylabel('K/9 (삼진 — 높을수록 좋음)', fontsize=10)
    ax.set_title(f'{year} SSG 투수 제구 vs 탈삼진\n(원 크기 = 이닝 수)', fontsize=12, fontweight='bold')

    legend_elements = [mpatches.Patch(color='#C8102E', label='선발'),
                       mpatches.Patch(color='#003087', label='불펜')]
    ax.legend(handles=legend_elements, fontsize=9)

plt.tight_layout()
plt.savefig('output/pitcher_03_k9_bb9.png', dpi=150, bbox_inches='tight')
plt.close()
print("✅ output/pitcher_03_k9_bb9.png 저장 완료")


# ════════════════════════════════════════════════
# 5. 시각화 4: 2024 vs 2025 공통 선수 FIP 변화
# ════════════════════════════════════════════════

common = set(df_2024['선수명']) & set(df_2025['선수명'])
if common:
    d24 = df_2024[df_2024['선수명'].isin(common)].set_index('선수명')
    d25 = df_2025[df_2025['선수명'].isin(common)].set_index('선수명')

    fip_change = (d25['FIP'] - d24['FIP']).sort_values()
    colors = ['#003087' if v <= 0 else '#C8102E' for v in fip_change]

    fig, ax = plt.subplots(figsize=(9, max(4, len(fip_change) * 0.55 + 1)))
    bars = ax.barh(fip_change.index, fip_change.values, color=colors, alpha=0.85)
    ax.axvline(x=0, color='black', linewidth=1)

    for bar, val in zip(bars, fip_change.values):
        offset = 0.03 if val >= 0 else -0.03
        ha = 'left' if val >= 0 else 'right'
        ax.text(val + offset, bar.get_y() + bar.get_height()/2,
                f'{val:+.2f}', va='center', ha=ha, fontsize=9)

    legend_elements = [mpatches.Patch(color='#003087', alpha=0.85, label='향상 (FIP 감소)'),
                       mpatches.Patch(color='#C8102E', alpha=0.85, label='하락 (FIP 증가)')]
    ax.legend(handles=legend_elements, fontsize=10)
    ax.set_title('SSG 투수 FIP 변화 (2024 → 2025)\n(음수: 실력 향상 / 양수: 실력 하락)',
                 fontsize=13, fontweight='bold')
    ax.set_xlabel('FIP 변화량')

    plt.tight_layout()
    plt.savefig('output/pitcher_04_fip_change.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("✅ output/pitcher_04_fip_change.png 저장 완료")


# ════════════════════════════════════════════════
# 6. 인사이트 요약
# ════════════════════════════════════════════════

print("\n" + "="*55)
print("📊 분석 요약: 2024 vs 2025 SSG 랜더스 투수진")
print("="*55)

for year, df_sub in [('2024', df_2024), ('2025', df_2025)]:
    if df_sub.empty:
        continue
    starters = df_sub[df_sub['역할'] == '선발']
    bullpen  = df_sub[df_sub['역할'] == '불펜']
    print(f"\n▶ {year} 시즌")
    print(f"  선발 ERA 평균: {starters['ERA'].mean():.2f} / FIP 평균: {starters['FIP'].mean():.2f}")
    print(f"  불펜 ERA 평균: {bullpen['ERA'].mean():.2f} / FIP 평균: {bullpen['FIP'].mean():.2f}")
    print(f"  선발 경기당 이닝: {starters['IP_per_G'].mean():.2f}")

    luck = df_sub.sort_values('ERA_FIP_diff', ascending=False)
    print(f"  ERA > FIP (운 나빴던 투수): {luck.iloc[0]['선수명']} ({luck.iloc[0]['ERA_FIP_diff']:+.2f})")
    print(f"  ERA < FIP (운 좋았던 투수): {luck.iloc[-1]['선수명']} ({luck.iloc[-1]['ERA_FIP_diff']:+.2f})")

print("\n✅ 모든 시각화 output/ 폴더에 저장 완료")
