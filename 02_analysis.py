"""
2024 vs 2025 SSG 랜더스 타선 비교 분석
- OPS, wOBA, ISO 계산
- 시즌별 팀 타선 전체 비교
- 두 시즌 모두 출전한 선수 개인 성장/하락 추적
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import os

plt.rcParams['font.family'] = 'Malgun Gothic'  # macOS: 'AppleGothic'
plt.rcParams['axes.unicode_minus'] = False

os.makedirs("output", exist_ok=True)


# ════════════════════════════════════════════════
# 1. 데이터 로드 및 지표 계산
# ════════════════════════════════════════════════

def calc_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """OPS, wOBA, ISO 계산"""
    df = df.copy()
    df['OBP']  = (df['H'] + (df['PA'] - df['AB'])) / df['PA']
    df['SLG']  = df['TB'] / df['AB']
    df['OPS']  = df['OBP'] + df['SLG']
    df['1B']   = df['H'] - df['2B'] - df['3B'] - df['HR']
    df['wOBA'] = (0.89*df['1B'] + 1.27*df['2B'] + 1.62*df['3B'] + 2.10*df['HR']) / df['PA']
    df['ISO']  = df['SLG'] - df['AVG']
    return df


df_all  = pd.read_csv("data/ssg_hitters_qualified.csv")
df_all  = calc_metrics(df_all)

df_2024 = df_all[df_all['season'] == 2024].copy()
df_2025 = df_all[df_all['season'] == 2025].copy()

print(f"2024 시즌: {len(df_2024)}명 / 2025 시즌: {len(df_2025)}명\n")


# ════════════════════════════════════════════════
# 2. 시각화 1: 시즌별 팀 평균 지표 비교
# ════════════════════════════════════════════════

metrics = ['AVG', 'OBP', 'SLG', 'OPS', 'wOBA']
labels  = ['타율', '출루율', '장타율', 'OPS', 'wOBA']

avg_2024 = [df_2024[m].mean() for m in metrics]
avg_2025 = [df_2025[m].mean() for m in metrics]

x     = np.arange(len(metrics))
width = 0.35

fig, ax = plt.subplots(figsize=(11, 6))
bars1 = ax.bar(x - width/2, avg_2024, width, label='2024', color='#C8102E', alpha=0.85)
bars2 = ax.bar(x + width/2, avg_2025, width, label='2025', color='#003087', alpha=0.85)

ax.set_title('SSG 랜더스 팀 타선 지표 비교: 2024 vs 2025\n(200타석 이상 선수 평균)',
             fontsize=13, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels(labels, fontsize=11)
ax.legend(fontsize=11)

for bar in bars1:
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.003,
            f'{bar.get_height():.3f}', ha='center', va='bottom', fontsize=9)
for bar in bars2:
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.003,
            f'{bar.get_height():.3f}', ha='center', va='bottom', fontsize=9)

plt.tight_layout()
plt.savefig('output/01_team_comparison.png', dpi=150, bbox_inches='tight')
plt.close()
print("✅ output/01_team_comparison.png 저장 완료")


# ════════════════════════════════════════════════
# 3. 시각화 2: 공통 선수 OPS 변화량
# ════════════════════════════════════════════════

common_players  = set(df_2024['선수명']) & set(df_2025['선수명'])
df_2024_common  = df_2024[df_2024['선수명'].isin(common_players)].set_index('선수명')
df_2025_common  = df_2025[df_2025['선수명'].isin(common_players)].set_index('선수명')

ops_change = (df_2025_common['OPS'] - df_2024_common['OPS']).sort_values()
colors     = ['#C8102E' if v >= 0 else '#A9A9A9' for v in ops_change]

fig, ax = plt.subplots(figsize=(10, max(5, len(ops_change) * 0.5 + 1)))
bars    = ax.barh(ops_change.index, ops_change.values, color=colors, alpha=0.85)
ax.axvline(x=0, color='black', linewidth=1)

ax.set_title('SSG 랜더스 선수별 OPS 변화\n(2024 → 2025, 두 시즌 모두 200타석 이상)',
             fontsize=13, fontweight='bold')
ax.set_xlabel('OPS 변화량 (양수: 향상 / 음수: 하락)', fontsize=11)

for bar, val in zip(bars, ops_change.values):
    offset = 0.003 if val >= 0 else -0.003
    ha     = 'left' if val >= 0 else 'right'
    ax.text(val + offset, bar.get_y() + bar.get_height()/2,
            f'{val:+.3f}', va='center', ha=ha, fontsize=9)

legend_elements = [mpatches.Patch(color='#C8102E', alpha=0.85, label='향상'),
                   mpatches.Patch(color='#A9A9A9', alpha=0.85, label='하락')]
ax.legend(handles=legend_elements, fontsize=10)

plt.tight_layout()
plt.savefig('output/02_ops_change.png', dpi=150, bbox_inches='tight')
plt.close()
print("✅ output/02_ops_change.png 저장 완료")


# ════════════════════════════════════════════════
# 4. 시각화 3: wOBA 나란히 비교
# ════════════════════════════════════════════════

fig, axes = plt.subplots(1, 2, figsize=(14, max(5, len(common_players) * 0.45 + 1)))

for ax, df_sub, year, color in zip(
    axes,
    [df_2024_common.loc[sorted(common_players)],
     df_2025_common.loc[sorted(common_players)]],
    ['2024', '2025'],
    ['#C8102E', '#003087']
):
    df_plot    = df_sub['wOBA'].sort_values()
    bar_colors = [color if v >= df_sub['wOBA'].mean() else '#D3D3D3' for v in df_plot]
    ax.barh(df_plot.index, df_plot.values, color=bar_colors, alpha=0.85)
    ax.axvline(x=df_sub['wOBA'].mean(), color='black', linestyle='--', linewidth=1.2,
               label=f'평균: {df_sub["wOBA"].mean():.3f}')
    ax.set_title(f'{year} 시즌 wOBA', fontsize=12, fontweight='bold')
    ax.set_xlabel('wOBA')
    ax.legend(fontsize=9)
    for i, val in enumerate(df_plot.values):
        ax.text(val + 0.002, i, f'{val:.3f}', va='center', fontsize=8)

fig.suptitle('SSG 랜더스 선수별 wOBA 비교 (공통 선수)', fontsize=13, fontweight='bold')
plt.tight_layout()
plt.savefig('output/03_woba_comparison.png', dpi=150, bbox_inches='tight')
plt.close()
print("✅ output/03_woba_comparison.png 저장 완료")


# ════════════════════════════════════════════════
# 5. 인사이트 요약
# ════════════════════════════════════════════════

print("\n" + "="*55)
print("📊 분석 요약: 2024 vs 2025 SSG 랜더스 타선")
print("="*55)

for metric, label in zip(['AVG', 'OPS', 'wOBA'], ['타율', 'OPS', 'wOBA']):
    v24       = df_2024[metric].mean()
    v25       = df_2025[metric].mean()
    diff      = v25 - v24
    direction = "▲ 향상" if diff > 0 else "▼ 하락"
    print(f"{label:>5}: {v24:.3f} → {v25:.3f}  ({direction} {abs(diff):.3f})")

if len(ops_change) > 0:
    top_improve = ops_change.idxmax()
    top_decline = ops_change.idxmin()
    print(f"\n▶ OPS 가장 많이 향상: {top_improve} ({ops_change[top_improve]:+.3f})")
    print(f"▶ OPS 가장 많이 하락: {top_decline} ({ops_change[top_decline]:+.3f})")

print("\n✅ 모든 시각화 output/ 폴더에 저장 완료")
