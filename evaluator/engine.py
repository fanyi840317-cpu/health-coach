"""
规则引擎核心
Layer 1: 快速拦截硬性安全违规
"""
from typing import List, Dict, Any, Optional
import json
from models import Prescription, RuleViolation, SafetyLevel, EvaluationResult, DimensionScore
from safety_rules import get_all_rules, get_rules_by_type, DIET_SAFETY_RULES, EXERCISE_SAFETY_RULES


class RuleEngine:
    """
    规则引擎 - 毫秒级安全检查
    
    使用方法:
        engine = RuleEngine()
        result = engine.evaluate(prescription)
    """
    
    def __init__(self, enable_warnings: bool = True):
        """
        初始化规则引擎
        
        Args:
            enable_warnings: 是否启用警告级别规则（默认启用）
        """
        self.enable_warnings = enable_warnings
        self.all_rules = get_all_rules()
    
    def evaluate(self, prescription: Prescription) -> EvaluationResult:
        """
        评估处方安全性
        
        Args:
            prescription: 待评估的处方对象
            
        Returns:
            EvaluationResult: 评估结果
        """
        violations = []
        passed_count = 0
        failed_count = 0
        
        # 获取适用的规则
        if prescription.prescription_type == "diet":
            applicable_rules = [r for r in DIET_SAFETY_RULES]
        elif prescription.prescription_type == "exercise":
            applicable_rules = [r for r in EXERCISE_SAFETY_RULES]
        else:
            applicable_rules = self.all_rules
        
        # 过滤警告级别（如果关闭）
        if not self.enable_warnings:
            applicable_rules = [r for r in applicable_rules if r.severity == "error"]
        
        # 执行规则检查
        for rule in applicable_rules:
            try:
                triggered = self._check_rule(rule, prescription)
                if triggered:
                    violation = self._create_violation(rule, prescription)
                    violations.append(violation)
                    failed_count += 1
                else:
                    passed_count += 1
            except Exception as e:
                # 规则执行出错，记录但不中断
                print(f"Rule {rule.rule_id} execution error: {e}")
                passed_count += 1
        
        # 确定安全等级
        safety_level = self._determine_safety_level(violations)
        safety_score = self._calculate_safety_score(violations, passed_count)
        
        return EvaluationResult(
            prescription=prescription,
            safety_level=safety_level,
            safety_score=safety_score,
            violations=violations,
            passed_rules=passed_count,
            failed_rules=failed_count
        )
    
    def _check_rule(self, rule, prescription: Prescription) -> bool:
        """执行单条规则检查"""
        user = prescription.user_profile
        diet = prescription.diet
        exercise = prescription.exercise
        
        try:
            return rule.check_fn(user, diet, exercise)
        except TypeError:
            # 尝试分别传入 diet 和 exercise
            try:
                if rule.applies_to == "diet":
                    return rule.check_fn(user, diet)
                elif rule.applies_to == "exercise":
                    return rule.check_fn(user, exercise)
                else:
                    # both 类型，尝试传入两个参数
                    return rule.check_fn(user, diet, exercise)
            except Exception:
                return False
    
    def _create_violation(self, rule, prescription: Prescription) -> RuleViolation:
        """创建违规记录，填充消息模板"""
        message = rule.message
        
        # 尝试填充模板变量
        try:
            diet = prescription.diet
            exercise = prescription.exercise
            user = prescription.user_profile
            
            replacements = {
                "{carbs}": str(int(diet.carbs_grams)),
                "{protein}": str(int(diet.protein_grams)),
                "{fat}": str(int(diet.fat_grams)),
                "{calories}": str(diet.total_calories),
                "{min_protein}": str(int(user.weight * 0.8)),
                "{duration}": str(exercise.duration_minutes),
                "{freq}": str(exercise.frequency_per_week),
            }
            for key, value in replacements.items():
                message = message.replace(key, value)
        except Exception:
            pass
        
        return RuleViolation(
            rule_id=rule.rule_id,
            rule_name=rule.name,
            severity=rule.severity,
            message=message,
            suggestion=rule.suggestion
        )
    
    def _determine_safety_level(self, violations: List[RuleViolation]) -> SafetyLevel:
        """根据违规情况确定安全等级"""
        if not violations:
            return SafetyLevel.SAFE
        
        # 有error级别违规 → blocked
        if any(v.severity == "error" for v in violations):
            return SafetyLevel.BLOCKED
        
        # 有warning级别违规 → warning
        if any(v.severity == "warning" for v in violations):
            return SafetyLevel.WARNING
        
        return SafetyLevel.SAFE
    
    def _calculate_safety_score(self, violations: List[RuleViolation], passed_count: int) -> float:
        """计算安全评分（0-100）"""
        total = len(violations) + passed_count
        if total == 0:
            return 100.0
        
        # error 扣30分，warning 扣10分
        error_count = sum(1 for v in violations if v.severity == "error")
        warning_count = sum(1 for v in violations if v.severity == "warning")
        
        score = 100.0 - (error_count * 30 + warning_count * 10)
        return max(0.0, min(100.0, score))
    
    def explain_rule(self, rule_id: str) -> Optional[Dict[str, Any]]:
        """解释单条规则的逻辑"""
        for rule in self.all_rules:
            if rule.rule_id == rule_id:
                return {
                    "rule_id": rule.rule_id,
                    "name": rule.name,
                    "description": rule.description,
                    "severity": rule.severity,
                    "applies_to": rule.applies_to,
                    "suggestion": rule.suggestion
                }
        return None
    
    def list_rules(self, by_type: Optional[str] = None, by_severity: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出所有规则"""
        rules = self.all_rules
        
        if by_type:
            rules = [r for r in rules if r.applies_to == by_type]
        if by_severity:
            rules = [r for r in rules if r.severity == by_severity]
        
        return [
            {
                "rule_id": r.rule_id,
                "name": r.name,
                "severity": r.severity,
                "applies_to": r.applies_to
            }
            for r in rules
        ]


def quick_check(prescription: Prescription) -> Dict[str, Any]:
    """
    快速检查处方安全性（便捷函数）
    
    Returns:
        dict with keys: safe (bool), level (str), violations (list)
    """
    engine = RuleEngine()
    result = engine.evaluate(prescription)
    
    return {
        "safe": result.safety_level == SafetyLevel.SAFE,
        "level": result.safety_level.value,
        "safety_score": result.safety_score,
        "violations": [
            {"rule_id": v.rule_id, "message": v.message, "suggestion": v.suggestion}
            for v in result.violations
        ],
        "passed_rules": result.passed_rules,
        "failed_rules": result.failed_rules
    }
