"""Render exact conditional acceptance for the two selected retained examples."""
from fractions import Fraction
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from linkage_bounds.robustness_audit import cdf,cutoff
from paths import ROOT
SOURCE=ROOT/'results/joint-query-validation'
BLUE,ORANGE,GRAY='#0072B2','#D55E00','#666666'
FIGURES=None
def emit(fig,name):
    fig.savefig(FIGURES/(name+'.pdf'),metadata={'CreationDate':None,'ModDate':None})
    fig.savefig(FIGURES/(name+'.png'),dpi=190)
    plt.close(fig)

def main():
    rows=json.loads((SOURCE/'summary.json').read_text())['rows']
    select=lambda index:next(r for r in rows if r['case_index']==index and r['delta']=='1/20')
    fig,axes=plt.subplots(1,2,figsize=(7.16,2.30))
    for ax,index,title in zip(axes,[0,10],['MIMIC 60: six wrong proposed pairs','eICU 225, hospital blocks: four wrong pairs']):
        r=select(index);n=r['n'];K=r['identity_errors'];joint=r['methods']['profile']['lower'];separate=r['separate_lower']
        mvals=np.arange(n+1);joint_y=[];separate_y=[];zero_y=[]
        for m in mvals:
            joint_y.append(float(cdf(n,K,int(m),cutoff(n,joint,int(m)))))
            separate_y.append(float(cdf(n,K,int(m),cutoff(n,separate,int(m)))))
            zero_y.append(float(cdf(n,K,int(m),0)) if cdf(n,joint,int(m),0)<=Fraction(1,20) else 0.)
        ax.plot(100*mvals/n,joint_y,color=BLUE,label='Joint radius (ours)',linewidth=1.7)
        ax.plot(100*mvals/n,separate_y,color=ORANGE,label='Separate bound',linewidth=1.4,linestyle='--')
        ax.plot(100*mvals/n,zero_y,color=GRAY,label='Zero-error-only rule',linewidth=1.2,linestyle=':')
        ax.set(title=title,xlim=(0,100),ylim=(-.02,1.03),xlabel='Proposed pairs checked (%)')
        ax.set_title(title,fontsize=9);ax.grid(alpha=.2)
    axes[0].set_ylabel('Acceptance probability')
    handles,legend=axes[0].get_legend_handles_labels();fig.legend(handles,legend,loc='lower center',ncol=3,frameon=False)
    fig.subplots_adjust(left=.08,right=.975,bottom=.30,top=.83,wspace=.24);emit(fig,'audit-acceptance')

