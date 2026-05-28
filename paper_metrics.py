import numpy as np
from sklearn.metrics import normalized_mutual_info_score


def purity(y_true, y_pred):
    """Paper eq. 4:  sum_i (n_i^d) / N  — dominant class count per cluster, over N."""
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    n = len(y_true)
    if n == 0:
        return 0.0
    correct = 0
    for c in np.unique(y_pred):
        if c == -1:
            continue
        members = y_true[y_pred == c]
        if len(members):
            _, counts = np.unique(members, return_counts=True)
            correct += int(counts.max())
    return correct / n


def accuracy(y_true, y_pred):
    """Paper eq. 5:  sum_i (n_i^d) / sum_i (n_i)  — denominator excludes noise."""
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    num, den = 0, 0
    for c in np.unique(y_pred):
        if c == -1:
            continue
        members = y_true[y_pred == c]
        if len(members):
            _, counts = np.unique(members, return_counts=True)
            num += int(counts.max())
            den += int(len(members))
    return num / den if den > 0 else 0.0


def nmi(y_true, y_pred):
    """Paper eq. 6: standard normalised mutual information."""
    return float(normalized_mutual_info_score(np.asarray(y_true), np.asarray(y_pred)))
