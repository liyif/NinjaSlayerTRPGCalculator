"""
数据类型定义 - 核心领域模型
清晰定义难度、伤害、攻击等概念
"""
from collections import defaultdict
from typing import NamedTuple, Dict, Tuple, List
from functools import lru_cache
import numpy as np



class Difficulty(NamedTuple):
    """
    难度定义：目标值 t 和所需成功数 r 的组合
    
    例如：
    - (2, 1): 最简单难度（掷 2+ 算成功）
    - (6, 2): 困难难度（需要2个6）
    - [(6,2), (5,3)]: 混合难度
    """
    conditions: Tuple[Tuple[int, int], ...]  # [(target_value, required_count), ...]
    
    def __str__(self) -> str:
        if len(self.conditions) == 1:
            t, r = self.conditions[0]
            return f"D({t},{r})"
        return f"D({self.conditions})"


    def to_label(self) -> str:
        from .definition import DIFFICULTY_TO_LABEL
        if self in DIFFICULTY_TO_LABEL:
            return DIFFICULTY_TO_LABEL[self]

        c = [0,0,0,0,0,0,0]
        for condition in self.conditions:
            c[condition[0]] += condition[1]
        p = 0
        s = ""
        for i in range(6,0,-1):
            s += str(i) * (c[i]-p)
            p = max(p, c[i])
        return s

    @staticmethod
    def from_label(label: str) -> "Difficulty":
        from .definition import LABEL_TO_DIFFICULTY
        if label in LABEL_TO_DIFFICULTY:
            return LABEL_TO_DIFFICULTY[label]
        if not label:
            return Difficulty.create([])

        c = [0,0,0,0,0,0,0]
        for t in label:
            c[int(t)]+=1
        arr = []
        p = 0
        for i in range(6,0,-1):
            if c[i]: arr.append((i,c[i]+p))
            p += c[i]
        return Difficulty.create(arr)

    def min_num_dices(self) -> int:
        if not self.conditions: return 0
        return max(map(lambda t:t[1], self.conditions))

    @staticmethod
    def create(conditions: List[Tuple[int, int]]) -> 'Difficulty':
        """规范化并创建难度对象"""
        sorted_conds = tuple(sorted(conditions, key=lambda x: (-x[0], -x[1])))
        return Difficulty(sorted_conds)

    def next(self, t: int = 1) -> 'Difficulty':
        if t == 0:
            return self
        if t == 1:
            if len(self.conditions) == 1:
                cond = self.conditions[0]
                if cond[0] < 6 and cond[1] == 1: return Difficulty.create([(cond[0]+1, 1)])
                if cond[0] == 6 : return Difficulty.create([(cond[0], cond[1]+1)])
            raise Exception()
        if t >= 2:
            return self.next(t - 1).next()


class DamageDistribution(NamedTuple):
    """
    伤害分布：可能的伤害值及其概率
    """
    values: np.ndarray      # 伤害值数组
    probabilities: np.ndarray  # 对应概率
    
    def expected_value(self) -> float:
        """期望伤害"""
        return float(np.sum(self.values * self.probabilities))
    
    def __str__(self) -> str:
        exp = self.expected_value()
        return f"Dmg(E[X]={exp:.2f})"
    
    def __hash__(self) -> int:
        return hash((tuple(self.values), tuple(self.probabilities)))
    
    def __eq__(self, value: object) -> bool:
        return isinstance(value, DamageDistribution) and np.array_equal(self.values, value.values) and np.array_equal(self.probabilities, value.probabilities)

    @staticmethod
    def from_expression(expr: str) -> 'DamageDistribution':
        """从掷骰表达式创建伤害分布"""
        from .damage import parse_dice_expression
        values, probabilities = parse_dice_expression(expr)
        return DamageDistribution(values=values, probabilities=probabilities)


class Attack(NamedTuple):
    """
    单次攻击的完整定义
    """
    damage: DamageDistribution  # 伤害分布
    difficulty: Difficulty      # 回避难度
    name: str = "Attack"
    
    def __str__(self) -> str:
        return f"{self.name}[{self.damage}@{self.difficulty}]"

    @staticmethod
    def create(damage_expr: str, evade_difficulty: Difficulty) -> 'Attack':
        return Attack(damage=DamageDistribution.from_expression(damage_expr), difficulty=evade_difficulty)

class AttackSequence(NamedTuple):
    """
    一套实际产生的攻击序列
    """
    attacks: Tuple[Attack, ...]
    
    def size(self) -> int:
        return len(self.attacks)
    
    def total_expected_damage(self) -> float:
        """所有攻击的总期望伤害（假设全中）"""
        return sum(atk.damage.expected_value() for atk in self.attacks)
    
    def __str__(self) -> str:
        return f"Attacks[{[atk.damage.expected_value() for atk in self.attacks]}]"

    @staticmethod
    def of(*attacks: Attack) -> 'AttackSequence':
        return AttackSequence(attacks=tuple(attacks))

    @staticmethod
    def concat(*sequences: 'AttackSequence') -> 'AttackSequence':
        """连接多个攻击序列"""
        all_attacks = []
        for seq in sequences:
            all_attacks.extend(seq.attacks)
        return AttackSequence(attacks=tuple(all_attacks))

class DefenseAllocation(NamedTuple):
    """
    防守资源分配方案
    """
    allocation: Tuple[int, ...]  # 每个攻击分配的资源数
    total_resource: int
    risk_value: float  # 风险调整价值
    
    def __str__(self) -> str:
        return f"Defense{list(self.allocation)}"

    @staticmethod
    def distribution(num_attacks: int, total_resource: int, risk_value: float = 0) -> List['DefenseAllocation']:
        """生成所有可能的资源分配方案"""
        from itertools import product
        allocations = []
        for alloc in product(range(total_resource + 1), repeat=num_attacks):
            if sum(alloc) == total_resource:
                allocations.append(DefenseAllocation(allocation=alloc, total_resource=total_resource, risk_value=risk_value))
        return allocations


    @staticmethod
    @lru_cache(maxsize=None)
    def best_allocation(attacks: AttackSequence, total_resource: int, risk_value: float = 0) -> Tuple['DefenseAllocation', float]:
        """根据攻击序列和风险值选择最佳防守分配方案"""
        if attacks.size() == 0:
            return DefenseAllocation(allocation=tuple(), total_resource=0, risk_value=0), 0.0
        from .probability import difficulty_success_probability
        allocations = DefenseAllocation.distribution(attacks.size(), total_resource, risk_value)
        

        best_alloc: DefenseAllocation | None = None
        best_damage = float('inf')
        for alloc in allocations:
            expected_damage = alloc.calculate_expected_damage(attacks)
            if expected_damage < best_damage:
                best_damage = expected_damage
                best_alloc = alloc
        if best_damage == float('inf'):
            print(total_resource)
            print(best_alloc)
            print(attacks)
            raise ValueError("No valid defense allocation found, that's unexpected.")
        return best_alloc, best_damage # type: ignore

    def calculate_expected_damage(self, attacks: AttackSequence) -> float:
        """计算在当前分配方案下，攻击序列的期望伤害"""
        from .probability import difficulty_success_probability
        total_damage = 0
        for atk, res in zip(attacks.attacks, self.allocation):
            p = difficulty_success_probability(atk.difficulty.conditions, res)
            total_damage += (1- p) * atk.damage.expected_value()
        return total_damage
        #TODO 使用更严格的风险调整方法，例如引入风险价值对期望伤害进行调整
            


class AttackTemplate(NamedTuple):
    """
    攻击模板：定义攻击的基本参数，便于生成具体攻击实例
    """
    conditions: List[Difficulty]
    branches: Dict[Tuple[bool, ...], AttackSequence]
    
    def __str__(self) -> str:
        return f"AttackTemplate[Conditions={len(self.conditions)}, Branches={len(self.branches)}]"

    def generate_attack_table(self, num_dice: int) -> List[Tuple[float, AttackSequence]]:
        """根据条件和骰子数量生成攻击表"""
        from .probability import joint_difficulty_probability
        dist = joint_difficulty_probability(tuple(cond.conditions for cond in self.conditions), num_dice)
        result = []
        for key, value in dist.items():
            if key in self.branches:
                result.append((value, self.branches[key]))
            else:
                result.append((value, AttackSequence.of()))  # 没有匹配的分支，视为无攻击
        return result
    
class AttackAllocation(NamedTuple):
    allocation : Tuple[int, ...]  # 每个攻击分配的资源数
    total_resource: int

    def __str__(self) -> str:
        return f"AttackAllocation{self.allocation}[Total={self.total_resource}]"
    
    @staticmethod
    def of(*allocs: int) -> 'AttackAllocation':
        total = sum(allocs)
        return AttackAllocation(allocation=tuple(allocs), total_resource=total)

    @staticmethod
    def distribute(num_attacks: int, total_resource: int) -> List['AttackAllocation']:
        """生成所有可能的资源分配方案"""
        from itertools import product
        allocations = []
        for alloc in product(range(total_resource + 1), repeat=num_attacks):
            if sum(alloc) == total_resource:
                allocations.append(AttackAllocation(allocation=alloc, total_resource=total_resource))
        return allocations

class AttackPlan(NamedTuple):
    templates: List[AttackTemplate]

    def __str__(self) -> str:
        return f"AttackPlan[Templates={len(self.templates)}]"

    def expand(self, allocation: AttackAllocation) -> List[Tuple[float, AttackSequence]]:
        """展开所有攻击模板，生成具体的攻击序列及其概率"""
        result = [(1.0, AttackSequence.of())]  # 初始状态：无攻击，概率为1
        for template, res in zip(self.templates, allocation.allocation):
                branches = template.generate_attack_table(res)
                new_result = []
                for p1, seq1 in result:
                    for p2, seq2 in branches:
                        new_result.append((p1 * p2, AttackSequence.concat(seq1, seq2)))
                result = new_result
        dict = defaultdict(float)
        for p, seq in result:
            dict[seq] += p
        return list(map(lambda x: (x[1], x[0]), dict.items()))
    
    def calculate_expected_damage(self, allocation: AttackAllocation,total_defense: int) -> float:
        """计算在给定资源分配方案下，攻击计划的期望伤害"""
        expanded = self.expand(allocation)
        total_expected_damage = sum(p * DefenseAllocation.best_allocation(seq, total_defense)[1] for p, seq in expanded)
        return total_expected_damage

    def best_allocation(self, total_attack: int, total_defense: int) -> Tuple['AttackAllocation', float]:
        allocs = AttackAllocation.distribute(num_attacks=len(self.templates), total_resource=total_attack)
        best_alloc: AttackAllocation | None = None
        best_damage = float('-inf')
        for alloc in allocs:
            expected_damage = self.calculate_expected_damage(alloc, total_defense=total_defense)
            if expected_damage > best_damage:
                best_damage = expected_damage
                best_alloc = alloc
        return best_alloc, best_damage # type: ignore



if __name__ == "__main__":


    print(Difficulty.create([(6,1),(5,4),(4,6)]).to_label())

    print(Difficulty.from_label("4222"))
    print(Difficulty.from_label("432"))
    print(Difficulty.from_label("6553"))
    # # 简单测试
    # from .definition import *
    #
    #
    # normalSeq1 = AttackSequence.of(
    #     Attack.create("1", DIFFICULTY_NORMAL),
    # )
    # normalSeq2 = AttackSequence.of(
    #     Attack.create("2", DIFFICULTY_NORMAL),
    # )
    # normalSeq3 = AttackSequence.of(
    #     Attack.create("2", DIFFICULTY_UHARD),
    # )
    # template1 = AttackTemplate(
    #     conditions=[DIFFICULTY_NORMAL, DIFFICULTY_UHARD, DIFFICULTY_UHARD3],
    #     branches={
    #         (True, False, False): normalSeq1,
    #         (True, True, False): normalSeq2,
    #         (True, True, True): normalSeq3
    #     }
    # )
    #
    # plan = AttackPlan(
    #     templates=[template1, template1, template1],
    #     total_resource=16
    # )
    # best_allocation, best_damage = plan.best_allocation(12)
    # print(f"Best allocation: {best_allocation}, Best damage: {best_damage}")
    #
    # #print(seq1)

    #alloc = DefenseAllocation.best_allocation(seq1, total_resource=8)

    #print(alloc, alloc.calculate_expected_damage(seq1))

    #print(DefenseAllocation.distribution(num_attacks=3, total_resource=10, risk_value=0.5))
