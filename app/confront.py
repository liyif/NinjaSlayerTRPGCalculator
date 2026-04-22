import math

def get_binomial_prob(n, a):
    """计算投掷 n 个骰子，成功次数从 0 到 n 的所有概率分布"""
    if a > 6: return [1.0] + [0.0] * n
    if a <= 1: return [0.0] * n + [1.0]
    
    # 单个骰子成功的概率 p
    p = (6 - a + 1) / 6.0
    q = 1.0 - p
    
    probs = []
    for k in range(n + 1):
        # 二项分布公式: C(n, k) * p^k * q^(n-k)
        comb = math.comb(n, k)
        prob = comb * (p**k) * (q**(n-k))
        probs.append(prob)
    return probs

def compare_dice(n1, a1, n2, a2):
    # 获取双方各自的概率分布
    probs1 = get_binomial_prob(n1, a1)
    probs2 = get_binomial_prob(n2, a2)
    
    p1_win = 0.0
    p2_win = 0.0
    draw = 0.0
    
    # 嵌套遍历所有可能的成功次数组合
    for i, prob_i in enumerate(probs1):
        for j, prob_j in enumerate(probs2):
            combined_p = prob_i * prob_j
            if i > j:
                p1_win += combined_p
            elif i < j:
                p2_win += combined_p
            else:
                draw += combined_p
                
    return p1_win, p2_win, draw

# 示例：
# 甲方：3个骰子，4及以上算成功
# 乙方：2个骰子，5及以上算成功
n1, a1 = 10, 5
n2, a2 = 10, 5

w1, w2, d = compare_dice(n1, a1, n2, a2)

print(f"--- 结果统计 ---")
print(f"甲方胜率: {w1:.2%}")
print(f"乙方胜率: {w2:.2%}")
print(f"平局概率: {d:.2%}")