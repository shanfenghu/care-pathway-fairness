"""Bounded, independently checkable integer infeasibility trees.

Ordinary branch-and-bound is inherited machinery. Its role here is to close
radius brackets that LP bounds cannot close. A numerical infeasibility status
never closes a leaf without its integer-arithmetic separating certificate.
"""
from time import perf_counter
import numpy as np
from scipy.optimize import linprog
from scipy.sparse import csr_matrix,vstack
from .profile_robustness import checked_lp_bound,verify_lp_certificate


def rows_for_path(model,B,d,upper,path):
    extra=[]; rhs=[]
    for variable,side,split in path:
        sign=1 if side=='left' else -1
        extra.append(csr_matrix(([sign],([0],[variable])),shape=(1,len(model.cost))))
        rhs.append(split if side=='left' else -split-1)
    return vstack([csr_matrix(B),csr_matrix(model.cost[None,:]),*extra]).tocsr(),np.r_[d,upper-1,rhs].astype(np.int64)


def prove_integer_lower(model,B,d,upper,seconds=2.,max_nodes=128):
    started=perf_counter(); nodes=0; incomplete=False
    def visit(path):
        nonlocal nodes,incomplete
        if nodes>=max_nodes or perf_counter()-started>=seconds:
            incomplete=True;return None
        nodes+=1;D,target=rows_for_path(model,B,d,upper,path)
        remaining=max(.001,seconds-(perf_counter()-started))
        lp=linprog(model.cost,A_ub=D,b_ub=target,A_eq=model.equality,b_eq=model.totals,
                   bounds=list(zip(np.zeros(len(model.cost)),model.upper)),method='highs',options=dict(time_limit=remaining))
        if lp.status==2:
            bound,certificate=checked_lp_bound(model,D,target,max(.001,seconds-(perf_counter()-started)))
            if certificate is None or certificate['kind']!='infeasible':incomplete=True;return None
            return dict(kind='leaf',certificate=certificate)
        if lp.status!=0:incomplete=True;return None
        fractions=abs(lp.x-np.rint(lp.x))
        variable=int(np.argmax(fractions))
        if fractions[variable]<=1e-7:
            x=np.rint(lp.x).astype(np.int64)
            if np.array_equal(model.equality@x,model.totals) and np.all(D@x<=target) and np.all(x>=0) and np.all(x<=model.upper):
                return dict(kind='counterexample',x=x.tolist())
            incomplete=True;return None
        split=int(np.floor(lp.x[variable]))
        left=visit(path+[(variable,'left',split)])
        if left is None:return None
        if left['kind']=='counterexample':return left
        right=visit(path+[(variable,'right',split)])
        if right is None:return None
        if right['kind']=='counterexample':return right
        return dict(kind='split',variable=variable,split=split,left=left,right=right)
    tree=visit([])
    return dict(complete=tree is not None and tree['kind']!='counterexample',tree=tree,nodes=nodes,
                search_seconds=perf_counter()-started,incomplete=incomplete)


def verify_integer_tree(model,B,d,upper,tree):
    """Verify that both integer halves are covered and every leaf is impossible."""
    nodes=leaves=0
    def visit(node,path):
        nonlocal nodes,leaves
        nodes+=1
        if not isinstance(node,dict):raise ValueError('Missing proof branch')
        if node.get('kind')=='leaf':
            D,target=rows_for_path(model,B,d,upper,path)
            if verify_lp_certificate(model,D,target,node['certificate'])!=float('inf'):raise ValueError('Unproved integer leaf')
            leaves+=1;return
        if node.get('kind')!='split':raise ValueError('Invalid proof node')
        variable=node['variable'];split=node['split']
        if type(variable) is not int or not 0<=variable<len(model.cost) or type(split) is not int or not 0<=split<int(model.upper[variable]):
            raise ValueError('Invalid integer partition')
        visit(node['left'],path+[(variable,'left',split)])
        visit(node['right'],path+[(variable,'right',split)])
    visit(tree,[])
    return dict(nodes=nodes,leaves=leaves,proven_lower=upper)
