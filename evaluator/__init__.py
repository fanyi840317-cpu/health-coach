"""
R+ Health 处方评审引擎
R+ Health Prescription Evaluation Engine

三层评估架构:
- Layer 1: 规则引擎 (RuleEngine) - 毫秒级安全拦截
- Layer 2: 多维度评分 (ScoringEngine) + LLM评审 (LLMJudge)
- Layer 3: 人工复核 (待实现)

使用方法:
    from evaluator import evaluate, RuleEngine, ScoringEngine, LLMJudge
    
    # 快速评估
    result = evaluate(prescription)
    
    # 详细评估
    engine = RuleEngine()
    rule_result = engine.evaluate(prescription)
    
    scorer = ScoringEngine()
    scores = scorer.score(prescription, rule_result.safety_score)
    
    # 生成报告
    from evaluator import ReportGenerator
    report = ReportGenerator().generate(result)
"""

__version__ = "1.0.0"
__author__ = "R+ Health Team"

from .models import (
    Prescription,
    UserProfile,
    DietPrescription,
    ExercisePrescription,
    EvaluationResult,
    RuleViolation,
    DimensionScore,
    SafetyLevel,
    PrescribeType,
    BMICategory,
    AgeGroup,
    ExerciseLevel,
    HealthGoal,
    Condition
)

from .engine import RuleEngine, quick_check
from .scoring import ScoringEngine
from .llm_judge import LLMJudge, quick_judge
from .report import ReportGenerator, save_report, print_summary
from .safety_rules import (
    DIET_SAFETY_RULES,
    EXERCISE_SAFETY_RULES,
    get_all_rules,
    get_rules_by_severity,
    get_rules_by_type
)


def evaluate(
    prescription: Prescription,
    use_llm: bool = False,
    llm_api_key: str = None
) -> EvaluationResult:
    """
    一键评估处方
    
    Args:
        prescription: 待评估的处方
        use_llm: 是否启用LLM深度评审
        llm_api_key: LLM API密钥
        
    Returns:
        EvaluationResult: 完整评估结果
    """
    # Layer 1: 规则引擎
    engine = RuleEngine()
    result = engine.evaluate(prescription)
    
    # Layer 2: 多维度评分
    scorer = ScoringEngine()
    result.dimension_scores = scorer.score(prescription, result.safety_score)
    result.overall_score = scorer.calculate_overall_score(result.dimension_scores)
    
    # Layer 2+: LLM深度评审（可选）
    if use_llm:
        try:
            judge = LLMJudge(api_key=llm_api_key)
            result.llm_judge_result = judge.judge(prescription)
        except Exception as e:
            print(f"LLM评审失败: {e}")
    
    return result


__all__ = [
    # 核心函数
    "evaluate",
    "quick_check",
    "quick_judge",
    # 模型
    "Prescription",
    "UserProfile", 
    "DietPrescription",
    "ExercisePrescription",
    "EvaluationResult",
    "RuleViolation",
    "DimensionScore",
    "SafetyLevel",
    # 引擎
    "RuleEngine",
    "ScoringEngine",
    "LLMJudge",
    "ReportGenerator",
    # 规则
    "DIET_SAFETY_RULES",
    "EXERCISE_SAFETY_RULES",
    "get_all_rules",
    "get_rules_by_severity",
    "get_rules_by_type",
    # 工具
    "save_report",
    "print_summary"
]
