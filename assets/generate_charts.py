import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.sans-serif': ['Segoe UI', 'Helvetica', 'Arial'],
    'font.size': 13,
    'axes.spines.top': False,
    'axes.spines.right': False,
    'figure.facecolor': 'white',
    'axes.facecolor': 'white',
    'savefig.dpi': 200,
    'savefig.bbox': 'tight',
    'savefig.pad_inches': 0.3,
})

IRYS = '#1a73e8'
TENET = '#ea4335'
FABLE = '#9334e6'
OPUS = '#f9ab00'
OTHER = '#aaaaaa'
DELTA_GREEN = '#0d9488'

IRYS_LABEL = 'irys (Gemini 3.7 Flash, no thinking)'

# ── Chart 1: All-Pass Rate ──
fig, ax = plt.subplots(figsize=(10, 5))
systems = [IRYS_LABEL, 'Muse Spark', 'Tenet', 'Grok 4.5', 'Fable 5', 'Kimi K3', 'DS V4 Flash', 'Opus 4.7', 'Opus 5', 'Gemini 3.6', 'GPT-5.6 Sol']
allpass = [32.5, 20.0, 19.7, 12.9, 11.5, 10.8, 8.3, 7.1, 6.7, 3.3, 2.5]
colors = [IRYS, OTHER, TENET, OTHER, FABLE, OTHER, OTHER, OPUS, OPUS, OTHER, OTHER]

bars = ax.barh(range(len(systems)), allpass, color=colors, height=0.65, edgecolor='white', linewidth=0.5)
ax.set_yticks(range(len(systems)))
ax.set_yticklabels(systems, fontsize=12)
ax.invert_yaxis()
ax.set_xlabel('Strict All-Pass Rate (%)', fontsize=13, fontweight='bold')
ax.set_title('Harvey Legal Agent Benchmark — All-Pass Rate', fontsize=16, fontweight='bold', pad=15)

for i, (bar, val) in enumerate(zip(bars, allpass)):
    ax.text(bar.get_width() + 0.4, bar.get_y() + bar.get_height()/2,
            f'{val}%', va='center', fontsize=11, fontweight='bold' if i == 0 else 'normal',
            color=colors[i])

ax.set_xlim(0, 39)
ax.xaxis.set_major_formatter(mticker.FormatStrFormatter('%g%%'))
plt.tight_layout()
plt.savefig('assets/lab_allpass_rate.png')
plt.close()

# ── Chart 2: Intelligence Per Dollar (bubble/scatter) ──
fig, ax = plt.subplots(figsize=(10, 6))

data = [
    (IRYS_LABEL, 4.64, 32.5, 7.00, IRYS),
    ('Tenet', 8, 19.7, 2.46, TENET),
    ('Fable 5', 102, 11.5, 0.11, FABLE),
    ('Opus 4.7', 51, 7.1, 0.14, OPUS),
]

for name, cost, ap, ipd, color in data:
    size = max(ipd * 120, 80)
    ax.scatter(cost, ap, s=size, c=color, alpha=0.85, edgecolors='white', linewidth=1.5, zorder=5)
    offset_x = 3 if cost < 80 else -8
    offset_y = 1.2
    if name == 'Opus 4.7':
        offset_y = -2.0
    label = name if name != IRYS_LABEL else 'irys'
    ax.annotate(f'{label}\n{ipd} all-pass/$',
                (cost, ap), textcoords='offset points',
                xytext=(offset_x, offset_y), fontsize=10, fontweight='bold',
                color=color, va='bottom')

ax.set_xlabel('Cost per Task ($)', fontsize=13, fontweight='bold')
ax.set_ylabel('All-Pass Rate (%)', fontsize=13, fontweight='bold')
ax.set_title('Performance vs Cost — Harvey LAB', fontsize=16, fontweight='bold', pad=15)
ax.set_xlim(-5, 120)
ax.set_ylim(0, 40)
ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('%g%%'))

ax.annotate('', xy=(4.64, 32.5), xytext=(102, 11.5),
            arrowprops=dict(arrowstyle='->', color='#666666', lw=1.5, linestyle='--'))
ax.text(55, 24, '62x intelligence\nper dollar', fontsize=10, color='#666666',
        ha='center', style='italic')

plt.tight_layout()
plt.savefig('assets/lab_performance_vs_cost.png')
plt.close()

# ── Chart 3: Cost per All-Pass Point ──
fig, ax = plt.subplots(figsize=(9, 4.5))
systems_cost = [IRYS_LABEL, 'Tenet', 'Opus 4.7', 'Fable 5']
cpp = [0.14, 0.41, 7.18, 8.87]
colors_cost = [IRYS, TENET, OPUS, FABLE]

bars = ax.barh(range(len(systems_cost)), cpp, color=colors_cost, height=0.55, edgecolor='white', linewidth=0.5)
ax.set_yticks(range(len(systems_cost)))
ax.set_yticklabels(systems_cost, fontsize=12)
ax.invert_yaxis()
ax.set_xlabel('Cost per All-Pass Percentage Point ($)', fontsize=12, fontweight='bold')
ax.set_title('Cost per Point of Quality', fontsize=16, fontweight='bold', pad=15)

for i, (bar, val) in enumerate(zip(bars, cpp)):
    label = f'${val:.2f}'
    if i == 0:
        label += '  (63x cheaper than Fable 5)'
    ax.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height()/2,
            label, va='center', fontsize=11, fontweight='bold' if i == 0 else 'normal',
            color=colors_cost[i])

ax.set_xlim(0, 14)
plt.tight_layout()
plt.savefig('assets/lab_cost_per_point.png')
plt.close()

# ── Chart 4: What $100 buys ──
fig, ax = plt.subplots(figsize=(9, 4.5))
systems_100 = [IRYS_LABEL, 'Tenet', 'Opus 4.7', 'Fable 5']
expected_pass = [7.0, 2.5, 0.14, 0.11]
colors_100 = [IRYS, TENET, OPUS, FABLE]

bars = ax.barh(range(len(systems_100)), expected_pass, color=colors_100, height=0.55, edgecolor='white', linewidth=0.5)
ax.set_yticks(range(len(systems_100)))
ax.set_yticklabels(systems_100, fontsize=12)
ax.invert_yaxis()
ax.set_xlabel('Expected All-Pass Tasks per $100', fontsize=12, fontweight='bold')
ax.set_title('What $100 Buys You on LAB', fontsize=16, fontweight='bold', pad=15)

for i, (bar, val) in enumerate(zip(bars, expected_pass)):
    ax.text(bar.get_width() + 0.08, bar.get_y() + bar.get_height()/2,
            f'{val}', va='center', fontsize=11, fontweight='bold' if i == 0 else 'normal',
            color=colors_100[i])

ax.set_xlim(0, 8)
plt.tight_layout()
plt.savefig('assets/lab_what_100_buys.png')
plt.close()

# ── Chart 5: Training Investment vs Performance ──
fig, ax = plt.subplots(figsize=(9, 3.5))

ax.barh([0], [32.5], color=IRYS, height=0.5, label=IRYS_LABEL)
ax.barh([1], [19.7], color=TENET, height=0.5, label='Harvey Tenet')

ax.set_yticks([0, 1])
ax.set_yticklabels([
    'irys (Gemini 3.7 Flash)\nZero training',
    'Tenet\n150 B300 GPUs × 2 months'
], fontsize=11)
ax.invert_yaxis()
ax.set_xlabel('All-Pass Rate (%)', fontsize=12, fontweight='bold')
ax.set_title('Training Investment vs Performance', fontsize=16, fontweight='bold', pad=15)

ax.text(32.5 + 0.5, 0, '32.5%', va='center', fontsize=12, fontweight='bold', color=IRYS)
ax.text(19.7 + 0.5, 1, '19.7%', va='center', fontsize=12, fontweight='bold', color=TENET)

ax.annotate('+65%', xy=(26, 0.5), fontsize=14, fontweight='bold', color='#333',
            ha='center', va='center',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='#e8f0fe', edgecolor=IRYS, linewidth=1.5))

ax.set_xlim(0, 40)
ax.xaxis.set_major_formatter(mticker.FormatStrFormatter('%g%%'))
plt.tight_layout()
plt.savefig('assets/lab_training_vs_performance.png')
plt.close()

# ── Chart 6: DELTA Criteria Rate vs Leaderboard ──
fig, ax = plt.subplots(figsize=(10, 5.5))
delta_systems = ['Opus 5', 'Fable 5.1', IRYS_LABEL, 'Grok 4.6', 'GPT-6 Astra', 'Gemini 3.8 Flash']
delta_criteria = [77.6, 75.7, 75.6, 68.8, 67.7, 61.4]
delta_colors = [OPUS, FABLE, IRYS, OTHER, OTHER, OTHER]

bars = ax.barh(range(len(delta_systems)), delta_criteria, color=delta_colors, height=0.55, edgecolor='white', linewidth=0.5)
ax.set_yticks(range(len(delta_systems)))
ax.set_yticklabels(delta_systems, fontsize=12)
ax.invert_yaxis()
ax.set_xlabel('Criteria Met (%)', fontsize=13, fontweight='bold')
ax.set_title('DELTA Dutch Legal Research — Criteria Rate', fontsize=16, fontweight='bold', pad=15)

for i, (bar, val) in enumerate(zip(bars, delta_criteria)):
    weight = 'bold' if i == 2 else 'normal'
    ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height()/2,
            f'{val}%', va='center', fontsize=11, fontweight=weight,
            color=delta_colors[i])

ax.set_xlim(0, 92)
ax.xaxis.set_major_formatter(mticker.FormatStrFormatter('%g%%'))

ax.text(46, 5.7, 'All scored by GPT-5.6 Sol (official DELTA judge)',
        fontsize=9, color='#888888', style='italic', ha='center')

plt.tight_layout()
plt.savefig('assets/delta_criteria_rate.png')
plt.close()

# ── Chart 7: DELTA Cost per Task vs Leaderboard ──
fig, ax = plt.subplots(figsize=(10, 5.5))
delta_cost_systems = [IRYS_LABEL, 'Gemini 3.8 Flash', 'Grok 4.6', 'GPT-6 Astra', 'Opus 5', 'Fable 5.1']
delta_costs = [0.010, 0.100, 0.191, 0.672, 1.068, 1.758]
delta_cost_colors = [IRYS, OTHER, OTHER, OTHER, OPUS, FABLE]

bars = ax.barh(range(len(delta_cost_systems)), delta_costs, color=delta_cost_colors, height=0.55, edgecolor='white', linewidth=0.5)
ax.set_yticks(range(len(delta_cost_systems)))
ax.set_yticklabels(delta_cost_systems, fontsize=12)
ax.invert_yaxis()
ax.set_xlabel('Cost per Task ($)', fontsize=13, fontweight='bold')
ax.set_title('DELTA Dutch Legal Research — Cost per Task', fontsize=16, fontweight='bold', pad=15)

for i, (bar, val) in enumerate(zip(bars, delta_costs)):
    weight = 'bold' if i == 0 else 'normal'
    suffix = '  (175x cheaper than Fable 5.1)' if i == 0 else ''
    ax.text(bar.get_width() + 0.01, bar.get_y() + bar.get_height()/2,
            f'${val:.3f}{suffix}' if val < 0.1 else f'${val:.3f}',
            va='center', fontsize=11, fontweight=weight,
            color=delta_cost_colors[i])

ax.set_xlim(0, 2.5)
plt.tight_layout()
plt.savefig('assets/delta_cost_per_task.png')
plt.close()

# ── Chart 8: DELTA Performance vs Cost (scatter) ──
fig, ax = plt.subplots(figsize=(10, 6))

delta_scatter = [
    ('irys', 0.010, 75.6, IRYS),
    ('Opus 5', 1.068, 77.6, OPUS),
    ('Fable 5.1', 1.758, 75.7, FABLE),
    ('Grok 4.6', 0.191, 68.8, OTHER),
    ('GPT-6 Astra', 0.672, 67.7, OTHER),
    ('Gemini 3.8 Flash', 0.100, 61.4, OTHER),
]

for name, cost, criteria, color in delta_scatter:
    ax.scatter(cost, criteria, s=200, c=color, alpha=0.85, edgecolors='white', linewidth=1.5, zorder=5)
    offset_x = 8
    offset_y = 0
    if name == 'Gemini 3.8 Flash':
        offset_y = -3
    if name == 'irys':
        offset_x = 8
        offset_y = -1
    if name == 'Grok 4.6':
        offset_y = 3
    label_text = f'{name}\n{criteria}% @ ${cost}'
    ax.annotate(label_text,
                (cost, criteria), textcoords='offset points',
                xytext=(offset_x, offset_y), fontsize=10, fontweight='bold',
                color=color, va='center')

ax.set_xlabel('Cost per Task ($)', fontsize=13, fontweight='bold')
ax.set_ylabel('Criteria Met (%)', fontsize=13, fontweight='bold')
ax.set_title('Performance vs Cost — DELTA Benchmark', fontsize=16, fontweight='bold', pad=15)
ax.set_xlim(-0.1, 2.2)
ax.set_ylim(55, 85)
ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('%g%%'))

ax.annotate('', xy=(0.010, 75.6), xytext=(1.758, 75.7),
            arrowprops=dict(arrowstyle='->', color='#666666', lw=1.5, linestyle='--'))
ax.text(0.9, 78, '175x cheaper,\nsame quality', fontsize=10, color='#666666',
        ha='center', style='italic')

ax.text(1.1, 57, 'All scored by GPT-5.6 Sol (official DELTA judge)',
        fontsize=9, color='#888888', style='italic', ha='center')

plt.tight_layout()
plt.savefig('assets/delta_performance_vs_cost.png')
plt.close()

# ── Chart 9: DELTA Consolidated Dashboard (2x2) ──
fig, axes = plt.subplots(2, 2, figsize=(14, 10))

systems = ['Opus\n5', 'Fable\n5.1', 'irys', 'Grok\n4.6', 'GPT-6\nAstra', 'Gemini\n3.8 Flash']
colors = [OPUS, FABLE, IRYS, OTHER, OTHER, OTHER]
criteria = [77.6, 75.7, 75.6, 68.8, 67.7, 61.4]
task_pass = [13.3, 15.0, 10.0, 10.0, 6.7, 5.0]
costs = [1.068, 1.758, 0.010, 0.191, 0.672, 0.100]
cpd = [c / cost for c, cost in zip(criteria, costs)]
n = len(systems)

# Panel 1 (top-left): Criteria Rate
ax = axes[0, 0]
bars = ax.bar(range(n), criteria, color=colors, width=0.55, edgecolor='white', linewidth=0.5)
for i, (bar, val) in enumerate(zip(bars, criteria)):
    weight = 'bold' if i == 2 else 'normal'
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.8,
            f'{val}%', ha='center', va='bottom', fontsize=11, fontweight=weight, color=colors[i])
ax.set_xticks(range(n))
ax.set_xticklabels(systems, fontsize=10)
ax.set_ylim(0, 92)
ax.set_ylabel('%', fontsize=12)
ax.set_title('Criteria Met', fontsize=15, fontweight='bold', pad=12)
ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('%g%%'))

# Panel 2 (top-right): Task Pass Rate
ax = axes[0, 1]
bars = ax.bar(range(n), task_pass, color=colors, width=0.55, edgecolor='white', linewidth=0.5)
for i, (bar, val) in enumerate(zip(bars, task_pass)):
    weight = 'bold' if i == 2 else 'normal'
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
            f'{val}%', ha='center', va='bottom', fontsize=11, fontweight=weight, color=colors[i])
ax.set_xticks(range(n))
ax.set_xticklabels(systems, fontsize=10)
ax.set_ylim(0, 22)
ax.set_ylabel('%', fontsize=12)
ax.set_title('Task Pass (all criteria)', fontsize=15, fontweight='bold', pad=12)
ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('%g%%'))

# Panel 3 (bottom-left): Cost per Task
ax = axes[1, 0]
bars = ax.bar(range(n), costs, color=colors, width=0.55, edgecolor='white', linewidth=0.5)
for i, (bar, val) in enumerate(zip(bars, costs)):
    weight = 'bold' if i == 2 else 'normal'
    label = f'${val:.3f}' if val < 0.1 else f'${val:.3f}'
    y_pos = bar.get_height() + 0.02
    ax.text(bar.get_x() + bar.get_width()/2, y_pos,
            label, ha='center', va='bottom', fontsize=11, fontweight=weight, color=colors[i])
ax.set_xticks(range(n))
ax.set_xticklabels(systems, fontsize=10)
ax.set_ylim(0, 2.3)
ax.set_ylabel('$', fontsize=12)
ax.set_title('Cost per Task', fontsize=15, fontweight='bold', pad=12)

# Panel 4 (bottom-right): Intelligence per Dollar
ax = axes[1, 1]
bars = ax.bar(range(n), cpd, color=colors, width=0.55, edgecolor='white', linewidth=0.5)
for i, (bar, val) in enumerate(zip(bars, cpd)):
    weight = 'bold' if i == 2 else 'normal'
    if val > 1000:
        label = f'{val:,.0f}'
    else:
        label = f'{val:.1f}'
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 80,
            label, ha='center', va='bottom', fontsize=11, fontweight=weight, color=colors[i])
ax.set_xticks(range(n))
ax.set_xticklabels(systems, fontsize=10)
ax.set_ylabel('criteria % per $', fontsize=12)
ax.set_title('Intelligence per Dollar', fontsize=15, fontweight='bold', pad=12)

fig.suptitle('DELTA Dutch Legal Research Benchmark', fontsize=18, fontweight='bold', y=1.01)
fig.text(0.5, -0.01, 'All scored by GPT-5.6 Sol (official DELTA judge). irys uses domain-agnostic prompts.',
         fontsize=10, color='#888888', style='italic', ha='center')

plt.tight_layout()
plt.savefig('assets/delta_consolidated.png', bbox_inches='tight')
plt.close()

print("All 9 charts generated in assets/")
