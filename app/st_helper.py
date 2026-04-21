from collections import defaultdict

import streamlit as st
import pandas as pd

from .probability import joint_difficulty_probability
from .types import Difficulty, AttackSequence, Attack, AttackTemplate, AttackPlan


def df_to_attack_template_conditions(
        df: pd.DataFrame
)-> list[Difficulty]:
    try:
        cd = list(map(lambda x: Difficulty.from_label(x), df["难度"]))
        return cd
    except Exception:
        return []

def get_all_available_branch_cond_strs(conditions: list[Difficulty]):
    if not conditions:
        return []
    num_dices = max(map(lambda d:d.min_num_dices(), conditions))
    test = joint_difficulty_probability(tuple(cond.conditions for cond in conditions), num_dices)
    return [ "".join([ str(int(p)) for p in t ]) for t in test.keys()]
    #return list(map(lambda t: str(t), (test.keys())))

def df_to_attack_template_branches(
        df: pd.DataFrame, atmosphere: int = 0
)-> dict[tuple[bool, ...], AttackSequence]:
    try:
        brs = defaultdict(list)
        for _, row in df.iterrows():
            case = row["情况"]
            case = tuple(map(bool,map(int, tuple(case))))
            diff = Difficulty.from_label(row["回避难度"])
            match row["气氛"]:
                case "近战": diff= diff.next(atmosphere)
                case "远程": diff= diff.next(atmosphere/2)
                case "术": diff= diff.next(atmosphere/2)
                case "无": pass
            brs[case].append(Attack.create(row["伤害"], diff))
        return dict(map(lambda t: (t[0], AttackSequence(attacks=t[1])), brs.items()))
    except Exception as e:
        return {}

def df_to_attack_plan(
        df: pd.DataFrame,
        templates: dict[str, AttackTemplate],
        atmosphere: int
) -> AttackPlan | None:
    try:
        result = []
        for _, row in df.iterrows():
            result.append(templates[row['模板']+":"+str(atmosphere)])
        return AttackPlan(templates=result)
    except:
        return None
