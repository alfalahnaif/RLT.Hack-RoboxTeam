"""Render README figures from committed metrics.json (requires matplotlib)."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import numpy as np

ROOT = Path(__file__).resolve().parent
DATA = json.loads((ROOT / 'metrics.json').read_text())
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11,
                     'svg.fonttype': 'path', 'axes.titleweight': 'bold'})
THEMES = {
    'light': {'bg':'#ffffff', 'fg':'#15243b', 'muted':'#516478', 'grid':'#e4ebf2',
              'accent':'#1878d1', 'secondary':'#008e9a', 'soft':'#eef5fb', 'warning':'#9a5700'},
    'dark': {'bg':'#0d1117', 'fg':'#edf3fa', 'muted':'#a9b8c9', 'grid':'#2b3645',
             'accent':'#66acff', 'secondary':'#55d4df', 'soft':'#172332', 'warning':'#efbd68'}
}

def frame(theme, title, subtitle, size=(13,7)):
    t=THEMES[theme]
    fig=plt.figure(figsize=size, facecolor=t['bg'])
    fig.text(.045,.925,'SUPPLIER RADAR  /  RECORDED EVIDENCE',color=t['muted'],fontsize=10,weight='bold')
    fig.text(.045,.857,title,color=t['fg'],fontsize=23,weight='bold')
    fig.text(.045,.806,subtitle,color=t['muted'],fontsize=11)
    return fig,t

def axes_style(ax,t,axis='x'):
    ax.set_facecolor(t['bg'])
    ax.set_axisbelow(True)
    ax.grid(axis=axis,color=t['grid'],linewidth=.8)
    for sp in ax.spines.values(): sp.set_visible(False)
    ax.tick_params(axis='both',colors=t['muted'],length=0,pad=9)
    ax.xaxis.label.set_color(t['muted'])
    ax.yaxis.label.set_color(t['muted'])

def footer(fig,t,line1,line2):
    fig.text(.045,.082,line1,color=t['muted'],fontsize=10)
    fig.text(.045,.047,line2,color=t['muted'],fontsize=9)

def save(fig,name,theme):
    fig.savefig(ROOT/f'{name}-{theme}.svg',facecolor=fig.get_facecolor(),metadata={'Date':None})
    fig.savefig(ROOT/f'{name}-{theme}.png',dpi=150,facecolor=fig.get_facecolor())
    plt.close(fig)

def dataset(theme):
    fig,t=frame(theme,'A documented procurement evidence base','2024–2025 organizer data · canonical record counts')
    ax=fig.add_axes([.235,.23,.70,.49])
    d=DATA['dataset']
    labels=['Procurement items','Supplier-history links','Procurement lots','Distinct supplier IDs']
    vals=[d['procurement_items'],d['canonical_supplier_links'],d['lots'],d['distinct_supplier_ids']]
    bars=ax.barh(range(4),vals,height=.46,color=[t['accent'],t['secondary'],t['accent'],t['secondary']],zorder=3)
    ax.set_yticks(range(4),labels,color=t['fg']); ax.invert_yaxis()
    ax.set_xlim(0,3500000); ax.set_xticks([0,1000000,2000000,3000000])
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v,_: '0' if v==0 else f'{v/1e6:.0f}M'))
    axes_style(ax,t); ax.set_xlabel('Record / identifier count',labelpad=14)
    ax.tick_params(axis='y',colors=t['fg'])
    for b,v in zip(bars,vals): ax.text(v+45000,b.get_y()+b.get_height()/2,f'{v:,}',va='center',fontsize=12,weight='bold',color=t['fg'])
    footer(fig,t,'Different entity types are shown separately; they are not parts of a single total.',
           'Source: reports/ingestion_report.md · Distinct IDs include quality-flagged invalid identifiers.')
    save(fig,'dataset-scale',theme)

def resolver(theme):
    fig,t=frame(theme,'Official OKPD2 category resolution','Resolver V4 · integrated fixed-test results · success-oriented metrics',size=(13,8))
    ax=fig.add_axes([.33,.24,.59,.48])
    metrics=DATA['resolver']['metrics']; vals=[m['percent'] for m in metrics]
    bars=ax.barh(range(len(vals)),vals,height=.49,color=t['accent'],zorder=3)
    ax.set_yticks(range(len(vals)),[f"{m['label']}   · n={m['n']}" for m in metrics]); ax.invert_yaxis()
    ax.set_xlim(0,112); ax.set_xticks([0,25,50,75,100]); ax.set_xlabel('Recorded result (%)',labelpad=12)
    axes_style(ax,t); ax.tick_params(axis='y',colors=t['fg'],labelsize=10.5)
    for b,v in zip(bars,vals): ax.text(v+1.5,b.get_y()+b.get_height()/2,f'{v:.2f}%',va='center',weight='bold',color=t['fg'],fontsize=11)
    err=DATA['resolver']['wrong_high_confidence_resolution']
    fig.text(.045,.155,f"Wrong high-confidence resolution: {err['percent']:.2f}%  · n={err['n']}  · lower is better",color=t['warning'],fontsize=11,weight='bold')
    footer(fig,t,'Each metric has its own test subset and denominator; these values are not overall supplier-search accuracy.',
           'Source: reports/final_intelligence_integration.md · Published 4 October 2026 · No new benchmark run.')
    save(fig,'resolver-benchmark',theme)

def ranking(theme):
    fig,t=frame(theme,'Historical supplier-ranking performance','Earlier frozen S3 configuration · 300 temporal HOLDOUT queries · EM procurement lots',size=(14,8))
    left=fig.add_axes([.07,.25,.43,.40]); right=fig.add_axes([.60,.25,.35,.40])
    r=DATA['ranking']; x=np.arange(4); width=.32
    bars1=left.bar(x-width/2,r['recall_unweighted'],width,color=t['accent'],label='Unweighted',zorder=3)
    bars2=left.bar(x+width/2,r['recall_population_weighted'],width,color=t['secondary'],label='Population-weighted',zorder=3)
    axes_style(left,t,'y'); left.set_ylim(0,100); left.set_yticks([0,25,50,75,100]); left.set_xticks(x,[f'Recall@{k}' for k in r['k']]); left.set_ylabel('Winner recall (%)',labelpad=10)
    left.set_title('Winner recall at different cutoffs',color=t['fg'],loc='left',fontsize=12,pad=20)
    for bars in [bars1,bars2]:
        for b in bars: left.text(b.get_x()+b.get_width()/2,b.get_height()+2,f'{b.get_height():.2f}',ha='center',va='bottom',color=t['fg'],fontsize=9)
    q=r['quality']; x=np.arange(3)
    a=right.bar(x-width/2,[m['unweighted'] for m in q],width,color=t['accent'],zorder=3)
    b=right.bar(x+width/2,[m['weighted'] for m in q],width,color=t['secondary'],zorder=3)
    axes_style(right,t,'y'); right.set_ylim(0,1); right.set_yticks([0,.25,.5,.75,1]); right.set_xticks(x,[m['label'] for m in q]); right.set_ylabel('Ranking score (0–1)',labelpad=10)
    right.set_title('Rank quality',color=t['fg'],loc='left',fontsize=12,pad=20)
    for bars in [a,b]:
        for bar in bars: right.text(bar.get_x()+bar.get_width()/2,bar.get_height()+.025,f'{bar.get_height():.4f}',ha='center',va='bottom',color=t['fg'],fontsize=9)
    legend=fig.legend(handles=[bars1,bars2],labels=['Unweighted','Population-weighted'],loc='upper left',bbox_to_anchor=(.065,.76),ncol=2,frameon=False,fontsize=11)
    for txt in legend.get_texts():txt.set_color(t['fg'])
    footer(fig,t,'Not rerun for the later Resolver V4/Groq integration. Reported overall baseline-gain confidence intervals include zero.',
           'Source: reports/p4_003_final_holdout.md · Historical weak labels do not establish current supplier suitability.')
    save(fig,'supplier-ranking',theme)

if __name__=='__main__':
    for theme in THEMES:
        dataset(theme); resolver(theme); ranking(theme)
    print('Rendered 3 charts × 2 themes × SVG/PNG formats.')
