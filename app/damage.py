"""
伤害分布 - 掷骰子表达式解析和概率计算
"""
import re
from typing import Tuple
import numpy as np
from scipy import stats
from .types import DamageDistribution


def parse_dice_expression(expr: str) -> Tuple[np.ndarray, np.ndarray]:
    """
    解析掷骰表达式 (如 '2D6+3') 为伤害分布
    
    Args:
        expr: 表达式字符串 "NDX+C" 或 "NDX" 或 纯数字
    
    Returns:
        (damage_values, probabilities)
    """
    expr = expr.strip()
    
    # 尝试直接解析为整数
    try:
        value = int(expr)
        return np.array([value]), np.array([1.0])
    except ValueError:
        pass
    
    # 解析 NDX+C 格式
    match = re.match(r'(\d+)D(\d+)(?:\+(\d+))?', expr, re.IGNORECASE)
    if not match:
        raise ValueError(f"无法解析掷骰表达式: {expr}。格式应为 NDX 或 NDX+C")
    
    num_dice = int(match.group(1))
    faces = int(match.group(2))
    constant = int(match.group(3)) if match.group(3) else 0
    
    if num_dice <= 0 or faces <= 0:
        raise ValueError(f"骰子数量和面数必须 > 0")
    
    # 计算单个骰子的概率
    single_pmf = np.full(faces, 1.0 / faces)
    
    # 多个骰子卷积
    total_pmf = single_pmf
    for _ in range(num_dice - 1):
        total_pmf = np.convolve(total_pmf, single_pmf)
    
    # 生成伤害值范围
    min_damage = num_dice + constant
    max_damage = num_dice * faces + constant
    damages = np.arange(min_damage, max_damage + 1)
    
    return damages, total_pmf


def create_damage_distribution(expr: str) -> DamageDistribution:
    """
    从掷骰表达式创建伤害分布对象
    
    Args:
        expr: 掷骰表达式 (如 "2D6+3")
    
    Returns:
        DamageDistribution 对象
    """
    values, probs = parse_dice_expression(expr)
    return DamageDistribution(values=values, probabilities=probs)


def create_custom_distribution(values: list, probabilities: list) -> DamageDistribution:
    """
    从自定义值和概率创建伤害分布
    
    Args:
        values: 伤害值列表
        probabilities: 对应的概率列表
    
    Returns:
        DamageDistribution 对象
    """
    values_arr = np.array(values, dtype=np.float64)
    probs_arr = np.array(probabilities, dtype=np.float64)
    
    # 归一化概率
    probs_arr = probs_arr / np.sum(probs_arr)
    
    return DamageDistribution(values=values_arr, probabilities=probs_arr)


def to_scipy_rv(dist: DamageDistribution) -> stats.rv_discrete:
    """
    将 DamageDistribution 转换为 Scipy rv_discrete 对象
    （用于高级概率计算）
    """
    return stats.rv_discrete(
        name='damage',
        values=(dist.values.astype(int), dist.probabilities)
    )


if __name__ == '__main__':
    # 测试
    d1 = create_damage_distribution("2D6+3")
    print(f"2D6+3: {d1}")
    print(f"  期望伤害: {d1.expected_value():.2f}")
    
    d2 = create_damage_distribution("1D6")
    print(f"1D6: {d2}")
    print(f"  期望伤害: {d2.expected_value():.2f}")
    
    d3 = create_custom_distribution([5, 10], [0.6, 0.4])
    print(f"自定义: {d3}")
    print(f"  期望伤害: {d3.expected_value():.2f}")
