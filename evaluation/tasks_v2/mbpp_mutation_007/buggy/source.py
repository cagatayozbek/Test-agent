def min_k(test_list, K):
    res = sorted(test_list, key=lambda x: x[0])[:K]
    return res
