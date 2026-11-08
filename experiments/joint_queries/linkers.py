"""Age/categorical agreement scoring and fixed feature-corruption models."""
import numpy as np

def corrupt(rows, rng, vocabulary, shifted=False):
    """Corrupt attributes only; hidden parent indices stay outside score features."""
    output = []
    for row in rows:
        bias = (4 if row['group'] == 'F' else -4) if shifted else 0
        sigma = (4 if row['group'] == 'F' else 6) if shifted else 2
        attributes = []
        for k, value in enumerate(row['attributes']):
            draw = rng.random()
            missing = .25 if shifted else .05
            replace = (.05 if shifted else .01) if k == 0 else (.15 if shifted else .05)
            if draw < missing:
                value = '<MISSING>'
            elif draw < missing+replace:
                value = str(rng.choice(vocabulary[k]))
            attributes.append(value)
        output.append({'age': row['age']+bias+rng.normal(0, sigma), 'attributes': attributes})
    return output

def agreements(left, right, rich):
    """Age bins and categorical agreements; no IDs, outcomes or parent positions."""
    age = np.array([x['age'] for x in left])[:, None]-np.array([x['age'] for x in right])[None, :]
    fields = [np.digitize(abs(age), [1, 3, 8], right=True)]
    if rich:
        for k in range(len(left[0]['attributes'])):
            a = np.array([x['attributes'][k] for x in left])[:, None]
            b = np.array([x['attributes'][k] for x in right])[None, :]
            fields.append(np.where((a == '<MISSING>') | (b == '<MISSING>'), 2, (a != b).astype(int)))
    return fields

def fit_score(left, feeds, rich):
    """Supervised smoothed m/u agreement weights on training pairs only."""
    tables = [agreements(left, feed, rich) for feed in feeds]
    n = len(left);truth = np.eye(n, dtype=bool)
    weights = []
    for k in range(len(tables[0])):
        levels = 4 if k == 0 else 3
        match = np.ones(levels);nonmatch = np.ones(levels)
        for table in tables:
            match += np.bincount(table[k][truth], minlength=levels)
            nonmatch += np.bincount(table[k][~truth], minlength=levels)
        weights.append(np.log((match/match.sum())/(nonmatch/nonmatch.sum())))
    return weights

def nonconformity(left, feed, weights, rich):
    return -sum(w[a] for w, a in zip(weights, agreements(left, feed, rich), strict=True))
