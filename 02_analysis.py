"""
2025 시즌 SSG 랜더스 타자 세이버메트릭스 분석
- OPS, wOBA 계산
- 타율 vs OPS 비교
- 선수별 득점 기여도 시각화

실행 순서: 01_crawl_kbo.py 실행 후 이 파일 실행
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
import os

# ── 한글 폰트 설정 ─────────────────────────────────────────────
# macOS: 'AppleGothic' / Windows: 'Malgun Gothic' / Linux: 'NanumGothic'
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

os.makedirs("output", exist_ok=True)


# ════════════════════════════════════════════════
# 1. 데이터 로드
# ════════════════════════════════════════════════
df = pd.read_csv("data/ssg_hitters_qualified.csv")
print(f"분석 대상: {len(df)}명\n")


# ════════════════════════════════════════════════
# 2. 세이버메트릭스 지표 계산
# ════════════════════════════════════════════════

# --- OPS (출루율 + 장타율) ---
# OBP = (H + BB + HBP) / (AB + BB + HBP + SF)
# SLG = TB / AB
# 주의: KBO 기본기록에는 BB(볼넷), HBP(사구)가 별도 수집 필요
# → 여기서는 PA, AB, H, TB를 이용한 근사치 사용
#   BB ≈ PA - AB - SAC - SF  (희생타/희생플라이는 세부기록에서 가져와야 함)
#   단순화: OBP = (H + (PA - AB)) / PA  (볼넷+사구+희생 포함 근사)

df['OBP_approx'] = (df['H'] + (df['PA'] - df['AB'])) / df['PA']
df['SLG'] = df['TB'] / df['AB']
df['OPS'] = df['OBP_approx'] + df['SLG']

# --- wOBA (가중 출루율, KBO 2024 근사 가중치) ---
# wOBA = (0.69×BB + 0.72×HBP + 0.89×1B + 1.27×2B + 1.62×3B + 2.10×HR) / PA
# BB, HBP 없이 근사: 단타 = H - 2B - 3B - HR
df['1B'] = df['H'] - df['2B'] - df['3B'] - df['HR']
df['wOBA_approx'] = (
    0.89 * df['1B'] +
    1.27 * df['2B'] +
    1.62 * df['3B'] +
    2.10 * df['HR']
) / df['PA']

# --- 파워-스피드 대리 지표: ISO (순수 장타력) ---
# ISO = SLG - AVG
df['ISO'] = df['SLG'] - df['AVG']

print("── 계산된 지표 ──")
print(df[['선수명', 'AVG', 'OBP_approx', 'SLG', 'OPS', 'wOBA_approx', 'ISO']]
      .sort_values('OPS', ascending=False)
      .to_string(index=False))


# ════════════════════════════════════════════════
# 3. 시각화 1: 타율 vs OPS 비교 (타율의 한계)
# ════════════════════════════════════════════════
fig, axes = plt.subplots(1, 2, figsize=(14, 6))
fig.suptitle('2024 SSG 랜더스 — 타율 vs OPS 비교\n(단순 타율이 놓치는 것들)', 
             fontsize=14, fontweight='bold', y=1.02)

df_sorted_avg = df.sort_values('AVG', ascending=True)
df_sorted_ops = df.sort_values('OPS', ascending=True)

# 타율 순위
axes[0].barh(df_sorted_avg['선수명'], df_sorted_avg['AVG'], 
             color='steelblue', alpha=0.8)
axes[0].set_title('타율 순위', fontsize=12)
axes[0].set_xlabel('타율 (AVG)')
axes[0].axvline(x=df['AVG'].mean(), color='red', linestyle='--', alpha=0.7, label=f'평균: {df["AVG"].mean():.3f}')
axes[0].legend()
for i, (val, name) in enumerate(zip(df_sorted_avg['AVG'], df_sorted_avg['선수명'])):
    axes[0].text(val + 0.001, i, f'{val:.3f}', va='center', fontsize=9)

# OPS 순위
axes[1].barh(df_sorted_ops['선수명'], df_sorted_ops['OPS'], 
             color='darkorange', alpha=0.8)
axes[1].set_title('OPS 순위', fontsize=12)
axes[1].set_xlabel('OPS (출루율 + 장타율)')
axes[1].axvline(x=df['OPS'].mean(), color='red', linestyle='--', alpha=0.7, label=f'평균: {df["OPS"].mean():.3f}')
axes[1].legend()
for i, (val, name) in enumerate(zip(df_sorted_ops['OPS'], df_sorted_ops['선수명'])):
    axes[1].text(val + 0.003, i, f'{val:.3f}', va='center', fontsize=9)

plt.tight_layout()
plt.savefig('output/01_avg_vs_ops.png', dpi=150, bbox_inches='tight')
plt.close()
print("\n✅ output/01_avg_vs_ops.png 저장 완료")


# ════════════════════════════════════════════════
# 4. 시각화 2: wOBA 기반 득점 기여도
# ════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(10, 7))

colors = ['#C8102E' if v >= df['wOBA_approx'].mean() else '#A9A9A9' 
          for v in df.sort_values('wOBA_approx', ascending=True)['wOBA_approx']]

df_sorted_woba = df.sort_values('wOBA_approx', ascending=True)
bars = ax.barh(df_sorted_woba['선수명'], df_sorted_woba['wOBA_approx'], color=colors, alpha=0.9)

ax.axvline(x=df['wOBA_approx'].mean(), color='navy', linestyle='--', linewidth=1.5,
           label=f'팀 평균 wOBA: {df["wOBA_approx"].mean():.3f}')
ax.set_title('2024 SSG 랜더스 타자별 wOBA (가중 출루율)\n— 높을수록 득점 기여도 높음 —', 
             fontsize=13, fontweight='bold')
ax.set_xlabel('wOBA (Weighted On-Base Average)', fontsize=11)
ax.legend(fontsize=10)

for i, (val, name) in enumerate(zip(df_sorted_woba['wOBA_approx'], df_sorted_woba['선수명'])):
    ax.text(val + 0.002, i, f'{val:.3f}', va='center', fontsize=9)

from matplotlib.patches import Patch
legend_elements = [Patch(facecolor='#C8102E', alpha=0.9, label='팀 평균 이상'),
                   Patch(facecolor='#A9A9A9', alpha=0.9, label='팀 평균 미만')]
ax.legend(handles=legend_elements + [plt.Line2D([0], [0], color='navy', linestyle='--', label=f'팀 평균: {df["wOBA_approx"].mean():.3f}')],
          fontsize=10)

plt.tight_layout()
plt.savefig('output/02_woba_contribution.png', dpi=150, bbox_inches='tight')
plt.close()
print("✅ output/02_woba_contribution.png 저장 완료")


# ════════════════════════════════════════════════
# 5. 시각화 3: OBP vs SLG 산점도 (타자 유형 분류)
# ════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(10, 8))

scatter = ax.scatter(df['OBP_approx'], df['SLG'], 
                     s=df['PA'] / 3,  # 타석 수에 비례한 크기
                     c=df['OPS'], cmap='RdYlGn', alpha=0.8, edgecolors='gray', linewidth=0.5)

for _, row in df.iterrows():
    ax.annotate(row['선수명'], (row['OBP_approx'], row['SLG']),
                textcoords="offset points", xytext=(6, 4), fontsize=9)

# 평균선 추가
ax.axvline(x=df['OBP_approx'].mean(), color='gray', linestyle=':', alpha=0.6)
ax.axhline(y=df['SLG'].mean(), color='gray', linestyle=':', alpha=0.6)

# 사분면 레이블
ax.text(df['OBP_approx'].min() + 0.005, df['SLG'].max() - 0.02, 
        '장타형', fontsize=9, color='gray', alpha=0.7)
ax.text(df['OBP_approx'].max() - 0.03, df['SLG'].max() - 0.02, 
        '완성형', fontsize=9, color='green', fontweight='bold', alpha=0.8)
ax.text(df['OBP_approx'].min() + 0.005, df['SLG'].min() + 0.01, 
        '하위', fontsize=9, color='gray', alpha=0.7)
ax.text(df['OBP_approx'].max() - 0.03, df['SLG'].min() + 0.01, 
        '출루형', fontsize=9, color='steelblue', alpha=0.7)

plt.colorbar(scatter, label='OPS')
ax.set_xlabel('출루율 (OBP)', fontsize=11)
ax.set_ylabel('장타율 (SLG)', fontsize=11)
ax.set_title('2024 SSG 랜더스 타자 유형 분류\n출루율 vs 장타율 (원 크기 = 타석수)', 
             fontsize=13, fontweight='bold')

plt.tight_layout()
plt.savefig('output/03_obp_vs_slg_scatter.png', dpi=150, bbox_inches='tight')
plt.close()
print("✅ output/03_obp_vs_slg_scatter.png 저장 완료")


# ════════════════════════════════════════════════
# 6. 인사이트 요약 출력
# ════════════════════════════════════════════════
print("\n" + "="*50)
print("📊 분석 요약: 2024 SSG 랜더스 타선")
print("="*50)

top_avg = df.sort_values('AVG', ascending=False).iloc[0]
top_ops = df.sort_values('OPS', ascending=False).iloc[0]
top_woba = df.sort_values('wOBA_approx', ascending=False).iloc[0]

print(f"\n▶ 타율 1위:  {top_avg['선수명']} ({top_avg['AVG']:.3f})")
print(f"▶ OPS 1위:   {top_ops['선수명']} ({top_ops['OPS']:.3f})")
print(f"▶ wOBA 1위:  {top_woba['선수명']} ({top_woba['wOBA_approx']:.3f})")

# 타율 순위 ≠ OPS 순위인 선수 (지표 차이가 큰 선수)
df['avg_rank'] = df['AVG'].rank(ascending=False)
df['ops_rank'] = df['OPS'].rank(ascending=False)
df['rank_diff'] = (df['avg_rank'] - df['ops_rank']).abs()

notable = df.sort_values('rank_diff', ascending=False).head(3)
print(f"\n▶ 타율 순위와 OPS 순위 차이가 큰 선수 (분석 포인트):")
for _, row in notable.iterrows():
    direction = "과소평가" if row['ops_rank'] < row['avg_rank'] else "과대평가"
    print(f"   {row['선수명']}: 타율 {int(row['avg_rank'])}위 → OPS {int(row['ops_rank'])}위 ({direction})")

print("\n✅ 모든 시각화 output/ 폴더에 저장 완료")
