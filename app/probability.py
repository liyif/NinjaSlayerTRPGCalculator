"""
概率计算 - 骰子和难度判定的核心计算
"""
from functools import lru_cache
from collections import defaultdict
from typing import Dict, Tuple, List
import numpy as np
from scipy.stats import binom


@lru_cache(maxsize=None)
def difficulty_success_probability(conditions: Tuple[Tuple[int, int], ...], 
                                   num_dice: int) -> float:
    """
    计算在给定骰子数量下，特定难度的成功概率
    
    Args:
        conditions: 难度条件元组，每项为 (target_value, required_count)
        num_dice: 投掷的骰子数量
    
    Returns:
        成功概率 (0.0 - 1.0)
    """
    if len(conditions) == 0:
        return 1.0

    if len(conditions) == 1:
        # 简单情况：只有一个目标值
        target_val, req_count = conditions[0]
        success_per_die = (7 - target_val) / 6.0  # 掷出 target_val+ 的概率
        
        if req_count <= 0:
            return 1.0
        elif req_count > num_dice:
            return 0.0
        
        # 使用二项分布计算：在 num_dice 次中至少成功 req_count 次
        return 1.0 - binom.cdf(req_count - 1, num_dice, success_per_die) # type: ignore
    
    # 复杂情况：多个条件的组合（状态机DP）
    return _multiway_difficulty_probability(conditions, num_dice)


@lru_cache(maxsize=None)
def _multiway_difficulty_probability(conditions: Tuple[Tuple[int, int], ...],
                                     num_dice: int) -> float:
    """多条件难度的概率计算（使用状态机）"""
    size = len(conditions)
    
    # DP 状态：tuple 表示每个条件的已达成次数
    dp = {tuple([0] * size): 1.0}
    
    for _ in range(num_dice):
        next_dp = defaultdict(float)
        
        for state, prob in dp.items():
            # 骰子结果 1-6，每种概率 1/6
            for roll in range(1, 7):
                new_state = list(state)
                
                for j, (target_val, req_count) in enumerate(conditions):
                    if roll >= target_val:
                        new_state[j] = min(state[j] + 1, req_count)
                
                next_dp[tuple(new_state)] += prob
        
        dp = dict(next_dp)
    
    # 计数成功状态（所有条件都达成）
    success_prob = 0.0
    for state, prob in dp.items():
        if all(state[j] >= conditions[j][1] for j in range(size)):
            success_prob += prob
    
    return success_prob / (6 ** num_dice)


@lru_cache(maxsize=None)
def joint_difficulty_probability(conditions_list: Tuple[Tuple[Tuple[int, int], ...], ...],
                                 num_dice: int) -> Dict[Tuple[bool, ...], float]:
    """
    计算多个独立难度的联合概率分布
    
    Args:
        conditions_list: 多个难度条件的列表
        num_dice: 骰子数量
    
    Returns:
        结果字典：key=(s1,s2,...), value=概率
        其中 si ∈ {0,1}，表示第 i 个难度是否成功
    """
    if not conditions_list:
        return {(): 1.0}
    
    # 第一步：收集所有 target_value 及其最大 required_count
    cap = {}
    for conditions in conditions_list:
        for target_val, req_count in conditions:
            if target_val not in cap:
                cap[target_val] = req_count
            else:
                cap[target_val] = max(cap[target_val], req_count)
    
    # 第二步：DP 跟踪所有 target_value 的计数
    ts = sorted(cap.keys())
    caps = [cap[t] for t in ts]
    k = len(ts)
    
    dp = {tuple([0] * k): 1.0}
    
    for _ in range(num_dice):
        next_dp = defaultdict(float)
        
        for state, prob in dp.items():
            for roll in range(1, 7):
                new_state = list(state)
                
                for idx, t in enumerate(ts):
                    if roll >= t:
                        c = state[idx] + 1
                        if c > caps[idx]:
                            c = caps[idx]
                        new_state[idx] = c
                
                next_dp[tuple(new_state)] += prob
        
        dp = dict(next_dp)
    
    # 第三步：评估每个难度的成功
    t_to_idx = {t: i for i, t in enumerate(ts)}
    m = len(conditions_list)
    joint = defaultdict(float)
    
    for state, prob in dp.items():
        outcome = []
        
        for conditions in conditions_list:
            ok = True
            for target_val, req_count in conditions:
                idx = t_to_idx[target_val]
                if state[idx] < req_count:
                    ok = False
                    break
            outcome.append(1 if ok else 0)
        
        joint[tuple(outcome)] += prob
    
    # 归一化
    total = 6 ** num_dice
    return {k: v / total for k, v in joint.items()}


if __name__ == "__main__":
    # 简单测试
    print(difficulty_success_probability(((6, 2),), 4))  # 4d6，至少2个6
    print(difficulty_success_probability(((5, 3),), 4))  # 4d6，至少3个5
    print(difficulty_success_probability(((6, 2), (5, 3)), 4))  # 4d6，至少2个6且至少3个5
    
    joint = joint_difficulty_probability((((6, 2),), ((5, 3),),), 4)
    for outcome, prob in joint.items():
        print(f"Outcome {outcome}: Probability {prob:.4f}")