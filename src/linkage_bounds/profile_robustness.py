"""Exact profile transport formulation for balanced block-complete joins.

This development implementation preserves whole source profiles. It does not
support arbitrary sparse candidates. Numerical MILP optima and checked integer
LP bounds are reported separately; statistical assurance uses the latter.
"""
from dataclasses import dataclass
from fractions import Fraction
from math import ceil, floor, inf, log
from time import perf_counter
import numpy as np
from scipy.optimize import Bounds, LinearConstraint, linprog, milp
from scipy.sparse import coo_matrix, csr_matrix, eye, hstack, vstack


@dataclass
class Problem:
    groups: np.ndarray
    flags: np.ndarray
    proposal: np.ndarray
    left_blocks: np.ndarray
    right_blocks: np.ndarray

    def __post_init__(self):
        groups=np.asarray(self.groups);flags=np.asarray(self.flags)
        proposal=np.asarray(self.proposal)
        # Integer conversion must not erase invalid indicators or partner indices.
        if not np.isin(groups,[0,1]).all() or not np.isin(flags,[0,1]).all():
            raise ValueError('This implementation requires binary indicators')
        if proposal.ndim!=1 or not np.isin(proposal,np.arange(len(proposal))).all():
            raise ValueError('Expected integer partner indices')
        self.groups=np.asarray(groups,dtype=int)
        self.flags=np.asarray(flags,dtype=int)
        self.proposal=np.asarray(proposal,dtype=int)
        self.left_blocks=np.asarray(self.left_blocks)
        self.right_blocks=np.asarray(self.right_blocks)
        n=len(self.proposal)
        if self.groups.ndim!=2 or self.flags.ndim!=2 or self.groups.shape[1]!=n or self.flags.shape[1]!=n:
            raise ValueError('Expected cohort/source indicator matrices with n columns')
        if sorted(self.proposal.tolist())!=list(range(n)) or self.left_blocks.shape!=(n,) or self.right_blocks.shape!=(n,):
            raise ValueError('Expected balanced bijection and block labels')
        if not np.array_equal(self.left_blocks,self.right_blocks[self.proposal]):
            raise ValueError('Proposal violates the declared complete blocks')
        for g in self.groups:
            if not 0<g.sum()<n: raise ValueError('Empty comparison group')

    @property
    def n(self):return len(self.proposal)

    def values(self,p):
        return np.array([int(np.sum(np.where(g,self.n-int(g.sum()),-int(g.sum()))*f[p]))
                         for g in self.groups for f in self.flags],dtype=np.int64)

    def caps(self,delta):
        delta=Fraction(delta)
        if delta<0:raise ValueError('Negative sensitivity tolerance')
        return np.array([floor(delta*int(g.sum())*(self.n-int(g.sum())))
                         for g in self.groups for _ in self.flags],dtype=np.int64)


@dataclass
class Model:
    problem: Problem
    cost: np.ndarray
    upper: np.ndarray
    equality: csr_matrix
    totals: np.ndarray
    query: np.ndarray
    edges: list | None
    cells: list | None
    row_profiles: dict | None
    column_profiles: dict | None
    geometry: dict

    def permutation(self,x):
        if self.edges is not None:
            p=np.full(self.problem.n,-1,dtype=int)
            for count,(i,j) in zip(x,self.edges):
                if count:
                    if count!=1 or p[i]>=0:raise ValueError('Non-assignment edge solution')
                    p[i]=j
            return p
        remaining={}
        for count,cell in zip(x,self.cells):remaining[cell]=remaining.get(cell,0)+int(count)
        p=np.full(self.problem.n,-1,dtype=int); used=set()
        for i,j in enumerate(self.problem.proposal):
            b,g=self.row_profiles[i]; _,h=self.column_profiles[int(j)]; cell=(b,g,h)
            if remaining[cell]>0:
                p[i]=j; used.add(int(j)); remaining[cell]-=1
        columns={}
        for j,(b,h) in self.column_profiles.items():
            if j not in used:columns.setdefault((b,h),[]).append(j)
        for i in range(self.problem.n):
            if p[i]>=0:continue
            b,g=self.row_profiles[i]
            cell=next(c for c,v in remaining.items() if c[:2]==(b,g) and v>0)
            p[i]=columns[(b,cell[2])].pop(); remaining[cell]-=1
        if any(remaining.values()):raise ValueError('Unfilled target cells')
        return p


def build_model(problem,kind):
    """Free capacity N_ab and unit-cost overflow encode the exact edit distance.

    Each block/profile cell has at most two arcs. Saturated cells need only one;
    singleton row AND column profiles reduce to the original assignment model.
    """
    if kind not in ('profile','assignment','mes'):raise ValueError('Unknown representation')
    n=problem.n; totals=[]; er=[]; ec=[]; costs=[]; upper=[]; columns=[]
    # Group totals are invariant across edges/cells. Recomputing their sums in
    # the edge loop adds avoidable cubic work to the direct representation.
    group_sizes=[int(g.sum()) for g in problem.groups]
    edges=[] if kind!='profile' else None
    cells=[] if kind=='profile' else None
    row_profiles={}; column_profiles={}; cell_count=0
    for block in sorted(set(problem.left_blocks.tolist())):
        left=np.flatnonzero(problem.left_blocks==block); right=np.flatnonzero(problem.right_blocks==block)
        if len(left)!=len(right):raise ValueError('Unbalanced block')
        if kind!='profile':
            offset=len(totals); totals.extend([1]*(2*len(left)))
            for a,i in enumerate(left):
                for b,j in enumerate(right):
                    k=len(costs); edges.append((int(i),int(j)))
                    costs.append(int(j!=problem.proposal[i])); upper.append(1)
                    er.extend([offset+a,offset+len(left)+b]); ec.extend([k,k])
                    columns.append([int((n-size if g[i] else -size)*f[j])
                                    for g,size in zip(problem.groups,group_sizes) for f in problem.flags])
            continue
        gp,gi=np.unique(problem.groups[:,left].T,axis=0,return_inverse=True)
        hp,hj=np.unique(problem.flags[:,right].T,axis=0,return_inverse=True)
        for i,g in zip(left,gi):row_profiles[int(i)]=(block,int(g))
        for j,h in zip(right,hj):column_profiles[int(j)]=(block,int(h))
        local_h={int(j):int(h) for j,h in zip(right,hj)}
        initial=np.zeros((len(gp),len(hp)),dtype=int)
        for i,g in zip(left,gi):initial[int(g),local_h[int(problem.proposal[i])]]+=1
        row=initial.sum(1); col=initial.sum(0); offset=len(totals)
        totals.extend(row.tolist()+col.tolist()); cell_count+=initial.size
        for a in range(len(gp)):
            for b in range(len(hp)):
                maximum=int(min(row[a],col[b])); old=int(initial[a,b])
                for capacity,price in ((old,0),(maximum-old,1)):
                    if not capacity:continue
                    k=len(costs); costs.append(price); upper.append(capacity)
                    cells.append((block,a,b)); er.extend([offset+a,offset+len(gp)+b]); ec.extend([k,k])
                    columns.append([int((n-size if gp[a,idx] else -size)*hp[b,fidx])
                                    for idx,size in enumerate(group_sizes) for fidx,_ in enumerate(problem.flags)])
    equality=coo_matrix((np.ones(len(er),dtype=np.int64),(er,ec)),shape=(len(totals),len(costs))).tocsr()
    return Model(problem,np.asarray(costs,dtype=np.int64),np.asarray(upper,dtype=np.int64),equality,
                 np.asarray(totals,dtype=np.int64),np.asarray(columns,dtype=np.int64).T,edges,cells,
                 row_profiles or None,column_profiles or None,
                 dict(variables=len(costs),equality_rows=len(totals),profile_cells=cell_count,
                      blocks=len(set(problem.left_blocks.tolist()))))


def independent_conditions(problem,caps):
    """Exact scalar radii: one binary count change needs two within-block edits."""
    result=[]; n=problem.n
    for g in problem.groups:
        a=int(g.sum()); b=n-a
        for f in problem.flags:
            cap=int(caps[len(result)]); t=int(f.sum()); x=int(f[problem.proposal][g.astype(bool)].sum())
            inc=dec=0
            for block in set(problem.left_blocks.tolist()):
                rows=np.flatnonzero(problem.left_blocks==block)
                group=g[rows].astype(bool); y=f[problem.proposal[rows]]
                inc+=min(int((1-y[group]).sum()),int(y[~group].sum()))
                dec+=min(int(y[group].sum()),int((1-y[~group]).sum()))
            possible=(x-dec,x+inc)
            low=ceil(Fraction(a*t-cap,n)); high=floor(Fraction(a*t+cap,n))
            feasible_low=max(low,possible[0]); feasible_high=min(high,possible[1])
            enter=inf if feasible_low>feasible_high else 2*max(feasible_low-x,x-feasible_high,0)
            negative=2*(x-(low-1)) if possible[0]<=low-1<x else inf
            positive=2*((high+1)-x) if x<high+1<=possible[1] else inf
            result.append(dict(enter=enter,negative=negative,positive=positive,possible=possible,count=x))
    return result


def _tmul(matrix,multipliers):
    """Guard int64 operations, then sum products with Python integers."""
    matrix=csr_matrix(matrix,dtype=np.int64); v=np.asarray(multipliers,dtype=np.int64)
    largest=max((abs(int(x)) for x in v),default=0)
    coefficient=max((abs(int(x)) for x in matrix.data),default=0)
    if largest*coefficient*max(matrix.shape[0],1)>=2**59:raise OverflowError('Dual arithmetic guard')
    return matrix.T@v


def verify_lp_certificate(model,B,d,record):
    """Check an exact rational lower bound, or a box-separation infeasibility proof.

    This verifier uses integer matrix arithmetic, not floating-point LP status.
    Any nonnegative inequality multipliers are valid. It rejects corrupt signs
    and claimed values, regardless of the numerical dual that proposed them.
    """
    scale=record['scale']
    if type(scale) is not int or scale<=0:raise ValueError('Invalid scale')
    if record['kind']=='lower':
        lam=record['inequality']; nu=record['equality']
        if len(lam)!=len(d) or len(nu)!=len(model.totals) or any(type(v) is not int for v in lam+nu) or any(v<0 for v in lam):
            raise ValueError('Invalid dual dimensions/signs')
        residual=model.cost*scale+_tmul(model.equality,nu)+_tmul(B,lam)
        value=-sum(v*int(t) for v,t in zip(nu,model.totals))-sum(v*int(t) for v,t in zip(lam,d))
    elif record['kind']=='infeasible':
        D=vstack([model.equality,-model.equality,csr_matrix(B)]).tocsr()
        target=np.r_[model.totals,-model.totals,d]
        lam=record['inequality']
        if len(lam)!=len(target) or any(type(v) is not int or not 0<=v<=scale for v in lam):raise ValueError('Invalid separating multipliers')
        residual=_tmul(D,lam); value=-sum(v*int(t) for v,t in zip(lam,target))
    else:raise ValueError('Unknown certificate')
    value+=sum(min(0,int(r))*int(u) for r,u in zip(residual,model.upper))
    if value!=record['numerator']:raise ValueError('Incorrect exact bound')
    if record['kind']=='infeasible' and value<=0:raise ValueError('Nonseparating infeasibility claim')
    return inf if record['kind']=='infeasible' else max(0,-((-value)//scale))


def checked_lp_bound(model,B,d,time_limit=2.,primal_candidates=None):
    bounds=list(zip(np.zeros(len(model.upper)),model.upper))
    lp=linprog(model.cost,A_ub=B,b_ub=d,A_eq=model.equality,b_eq=model.totals,bounds=bounds,
               method='highs',options=dict(time_limit=time_limit))
    # This optional numerical candidate is not a certificate. The caller must
    # check integrality, all exact constraints and the original-space linkage.
    if primal_candidates is not None and lp.status==0 and lp.x is not None:
        primal_candidates.append(lp.x.copy())
    scale=10**6; record=None
    if lp.status==0:
        record=dict(kind='lower',scale=scale,
                    inequality=np.maximum(0,np.rint(-lp.ineqlin.marginals*scale)).astype(np.int64).tolist(),
                    equality=np.rint(-lp.eqlin.marginals*scale).astype(np.int64).tolist())
    elif lp.status==2:
        D=vstack([model.equality,-model.equality,csr_matrix(B)]).tocsr(); target=np.r_[model.totals,-model.totals,d]
        soft=linprog(np.r_[np.zeros(len(model.upper)),np.ones(len(target))],A_ub=hstack([D,-eye(len(target))]),
                     b_ub=target,bounds=bounds+[(0,None)]*len(target),method='highs',options=dict(time_limit=time_limit))
        if soft.status==0:
            record=dict(kind='infeasible',scale=scale,
                        inequality=np.clip(np.rint(-soft.ineqlin.marginals*scale),0,scale).astype(np.int64).tolist())
    if record is None:return 0,None
    # Compute the claimed numerator separately, then run the rejecting verifier.
    if record['kind']=='lower':
        nu=record['equality']; lam=record['inequality']
        residual=model.cost*scale+_tmul(model.equality,nu)+_tmul(B,lam)
        numerator=-sum(v*int(t) for v,t in zip(nu,model.totals))-sum(v*int(t) for v,t in zip(lam,d))
    else:
        residual=_tmul(D,record['inequality']); numerator=-sum(v*int(t) for v,t in zip(record['inequality'],target))
    numerator+=sum(min(0,int(r))*int(u) for r,u in zip(residual,model.upper))
    if record['kind']=='infeasible' and numerator<=0:return 0,None
    record['numerator']=numerator
    return verify_lp_certificate(model,B,d,record),record


def verify_permutation(problem,p,caps,expected_inside):
    p=np.asarray(p)
    if p.shape!=(problem.n,) or not np.isin(p,np.arange(problem.n)).all():
        raise ValueError('Expected integer attaining permutation indices')
    p=np.asarray(p,dtype=int)
    if sorted(p.tolist())!=list(range(problem.n)) or not np.array_equal(problem.left_blocks,problem.right_blocks[p]):
        raise ValueError('Invalid attaining permutation')
    values=problem.values(p)
    if bool(np.all(abs(values)<=caps))==expected_inside:raise ValueError('Witness did not reverse the workload condition')
    return int(np.count_nonzero(p!=problem.proposal)),values.tolist()


def solve_radius(problem,delta,kind='profile',mip_seconds=5.,lp_seconds=2.):
    started=perf_counter(); model=build_model(problem,kind); built=perf_counter()
    caps=problem.caps(delta); base=problem.values(problem.proposal); inside=bool(np.all(abs(base)<=caps))
    scalar=independent_conditions(problem,caps); branches=[]
    if inside:
        for q,s in enumerate(scalar):
            if s['negative']<inf:branches.append((model.query[q:q+1],np.array([-int(caps[q])-1]),s['negative'],f'{q}:negative'))
            if s['positive']<inf:branches.append((-model.query[q:q+1],np.array([-int(caps[q])-1]),s['positive'],f'{q}:positive'))
        separate=min([min(s['negative'],s['positive']) for s in scalar],default=inf)
    else:
        separate=max(s['enter'] for s in scalar)
        if separate<inf:branches.append((np.r_[model.query,-model.query],np.r_[caps,caps],separate,'all_within'))
    summaries=[]; best=None; mip_used=0.; bound_time=solve_time=check_time=0.
    for B,d,analytic,label in branches:
        tick=perf_counter(); lower,certificate=checked_lp_bound(model,B,d,lp_seconds); bound_time+=perf_counter()-tick
        lower=max(lower,analytic,2)
        row=dict(branch=label,lower=None if lower==inf else int(lower),infeasible_proved=lower==inf,certificate=certificate)
        if lower==inf: summaries.append(row);continue
        remaining=max(.001,mip_seconds-mip_used); tick=perf_counter()
        scale=log(9.) if kind=='mes' else 1.
        result=milp(model.cost*scale,integrality=np.ones(len(model.cost)),bounds=Bounds(0,model.upper),
                    constraints=[LinearConstraint(model.equality,model.totals,model.totals),LinearConstraint(B,-np.inf,d)],
                    options=dict(time_limit=remaining,mip_rel_gap=0.))
        used=perf_counter()-tick; mip_used+=used; solve_time+=used; tick=perf_counter()
        row['solver_status']=int(result.status)
        if result.x is not None:
            if np.max(abs(result.x-np.rint(result.x)))>1e-6:raise ArithmeticError('Fractional MIP incumbent')
            x=np.rint(result.x).astype(np.int64)
            if np.any(x<0) or np.any(x>model.upper) or not np.array_equal(model.equality@x,model.totals) or np.any(B@x>d):
                raise ArithmeticError('Invalid integer model incumbent')
            witness=model.permutation(x); distance,values=verify_permutation(problem,witness,caps,inside)
            if distance>int(model.cost@x) or lower>distance:raise ArithmeticError('Inconsistent checked radius bounds')
            row['upper']=distance
            if best is None or distance<best['upper']:
                best=dict(upper=distance,witness=witness.tolist(),witness_values=values)
        check_time+=perf_counter()-tick; summaries.append(row)
    lower=min((inf if r['infeasible_proved'] else r['lower'] for r in summaries),default=inf)
    if not summaries:lower=inf  # exact scalar-margin obstruction covers every branch
    upper=best['upper'] if best else None
    if upper is not None and lower>upper:raise ArithmeticError('Invalid global bracket')
    rigorous_invariant=lower==inf
    complete_numeric=all(r['infeasible_proved'] or r.get('solver_status') in (0,2) for r in summaries)
    return dict(method=kind,delta=str(Fraction(delta)),baseline_inside=inside,base_values=base.tolist(),caps=caps.tolist(),
                separate_lower=None if separate==inf else int(separate),separate_invariant=separate==inf,
                lower=None if rigorous_invariant else int(lower),rigorous_invariant=rigorous_invariant,
                upper=upper,bracket_closed=rigorous_invariant or (upper is not None and lower==upper),
                numerical_optimum=upper if complete_numeric else None,branches=summaries,
                **({k:v for k,v in best.items() if k!='upper'} if best else {}),
                geometry=model.geometry,timing=dict(representation_seconds=built-started,lp_bound_seconds=bound_time,
                mip_seconds=solve_time,witness_check_seconds=check_time,total_seconds=perf_counter()-started),
                mes_log_likelihood=None if kind!='mes' or upper is None else (problem.n-upper)*log(.9)+upper*log(.1))
