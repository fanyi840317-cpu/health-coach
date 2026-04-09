"""
测试用例
验证处方评审引擎的正确性
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import (
    UserProfile, DietPrescription, ExercisePrescription, Prescription,
    SafetyLevel, Condition
)
from engine import RuleEngine, quick_check
from scoring import ScoringEngine
from report import ReportGenerator
from safety_rules import get_all_rules


class TestResult:
    """测试结果"""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
    
    def add_pass(self, name: str):
        self.passed += 1
        print(f"  ✅ {name}")
    
    def add_fail(self, name: str, reason: str):
        self.failed += 1
        self.errors.append((name, reason))
        print(f"  ❌ {name}: {reason}")
    
    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*50}")
        print(f"测试结果: {self.passed}/{total} 通过")
        if self.errors:
            print(f"\n失败项:")
            for name, reason in self.errors:
                print(f"  - {name}: {reason}")
        return self.failed == 0


def test_models():
    """测试数据模型"""
    print("\n📦 测试数据模型...")
    result = TestResult()
    
    # 测试用户画像
    try:
        user = UserProfile(
            age=35, gender="男", height=175, weight=70,
            conditions=["糖尿病", "高血压"],
            exercise_level="初级",
            goal="减脂"
        )
        assert user.bmi is not None
        assert user.get_bmi_category() == "正常"
        result.add_pass("UserProfile 创建")
    except Exception as e:
        result.add_fail("UserProfile 创建", str(e))
    
    # 测试饮食处方
    try:
        diet = DietPrescription(
            total_calories=1800,
            carbs_grams=200,
            protein_grams=80,
            fat_grams=60,
            meals_per_day=3,
            restrictions=["低糖", "少盐"]
        )
        macros = diet.get_macros_ratio()
        assert macros["carbs"] > 0
        result.add_pass("DietPrescription 创建")
    except Exception as e:
        result.add_fail("DietPrescription 创建", str(e))
    
    # 测试运动处方
    try:
        exercise = ExercisePrescription(
            frequency_per_week=4,
            duration_minutes=45,
            intensity="中强度",
            exercise_types=["快走", "游泳"]
        )
        assert exercise.get_intensity_level() == 2
        result.add_pass("ExercisePrescription 创建")
    except Exception as e:
        result.add_fail("ExercisePrescription 创建", str(e))
    
    return result


def test_rule_engine():
    """测试规则引擎"""
    print("\n⚙️ 测试规则引擎...")
    result = TestResult()
    engine = RuleEngine()
    
    # 测试1: 正常处方（无违规）
    try:
        user = UserProfile(age=30, gender="男", height=170, weight=65)
        diet = DietPrescription(total_calories=2000, carbs_grams=250, protein_grams=80, fat_grams=65)
        exercise = ExercisePrescription(frequency_per_week=4, duration_minutes=45, intensity="中强度")
        prescription = Prescription(user_profile=user, diet=diet, exercise=exercise)
        
        eval_result = engine.evaluate(prescription)
        assert eval_result.safety_level == SafetyLevel.SAFE
        result.add_pass("正常处方 - 无违规")
    except Exception as e:
        result.add_fail("正常处方 - 无违规", str(e))
    
    # 测试2: 糖尿病碳水超标
    try:
        user = UserProfile(age=50, gender="女", height=160, weight=60, conditions=["糖尿病"])
        diet = DietPrescription(total_calories=2000, carbs_grams=300, protein_grams=70, fat_grams=60)
        exercise = ExercisePrescription(frequency_per_week=3, duration_minutes=30, intensity="低强度")
        prescription = Prescription(user_profile=user, diet=diet, exercise=exercise)
        
        eval_result = engine.evaluate(prescription)
        assert eval_result.safety_level in [SafetyLevel.BLOCKED, SafetyLevel.WARNING]
        assert any(v.rule_id == "DIET_001" for v in eval_result.violations)
        result.add_pass("糖尿病碳水超标 - 被拦截")
    except Exception as e:
        result.add_fail("糖尿病碳水超标 - 被拦截", str(e))
    
    # 测试3: 心脏病患者高强度运动
    try:
        user = UserProfile(age=60, gender="男", height=165, weight=70, conditions=["心脏病"])
        diet = DietPrescription(total_calories=1800, carbs_grams=200, protein_grams=75, fat_grams=55)
        exercise = ExercisePrescription(frequency_per_week=5, duration_minutes=60, intensity="高强度")
        prescription = Prescription(user_profile=user, diet=diet, exercise=exercise)
        
        eval_result = engine.evaluate(prescription)
        assert eval_result.safety_level == SafetyLevel.BLOCKED
        assert any(v.rule_id == "EX_001" for v in eval_result.violations)
        result.add_pass("心脏病患者高强度运动 - 被拦截")
    except Exception as e:
        result.add_fail("心脏病患者高强度运动 - 被拦截", str(e))
    
    # 测试4: 无运动基础直接高强度
    try:
        user = UserProfile(age=40, gender="女", height=158, weight=55, exercise_level="无")
        diet = DietPrescription(total_calories=1600, carbs_grams=180, protein_grams=65, fat_grams=50)
        exercise = ExercisePrescription(frequency_per_week=4, duration_minutes=50, intensity="高强度")
        prescription = Prescription(user_profile=user, diet=diet, exercise=exercise)
        
        eval_result = engine.evaluate(prescription)
        assert eval_result.failed_rules > 0
        result.add_pass("无运动基础高强度 - 规则触发")
    except Exception as e:
        result.add_fail("无运动基础高强度 - 规则触发", str(e))
    
    return result


def test_scoring():
    """测试评分系统"""
    print("\n📊 测试评分系统...")
    result = TestResult()
    scorer = ScoringEngine()
    engine = RuleEngine()
    
    # 测试正常处方评分
    try:
        user = UserProfile(age=35, gender="男", height=175, weight=70, goal="减脂")
        diet = DietPrescription(
            total_calories=2000, carbs_grams=220, protein_grams=90, fat_grams=60,
            restrictions=["少油少盐"], recommendations=["多吃蔬菜"]
        )
        exercise = ExercisePrescription(
            frequency_per_week=4, duration_minutes=45, intensity="中强度",
            exercise_types=["快走", "力量训练"], warm_up_minutes=5, cool_down_minutes=5
        )
        prescription = Prescription(user_profile=user, diet=diet, exercise=exercise)
        
        rule_result = engine.evaluate(prescription)
        scores = scorer.score(prescription, rule_result.safety_score)
        overall = scorer.calculate_overall_score(scores)
        
        assert len(scores) == 5
        assert overall > 0
        assert overall <= 100
        result.add_pass("评分系统正常工作")
    except Exception as e:
        result.add_fail("评分系统正常工作", str(e))
    
    # 测试评分权重
    try:
        weights = scorer.weights
        total_weight = sum(weights.values())
        assert abs(total_weight - 1.0) < 0.01
        result.add_pass("评分权重总和为1.0")
    except Exception as e:
        result.add_fail("评分权重总和为1.0", str(e))
    
    return result


def test_rules_coverage():
    """测试规则覆盖率"""
    print("\n📋 测试规则覆盖率...")
    result = TestResult()
    
    rules = get_all_rules()
    
    # 检查饮食规则
    diet_rules = [r for r in rules if r.applies_to in ["diet", "both"]]
    result.add_pass(f"饮食安全规则: {len(diet_rules)} 条")
    
    # 检查运动规则
    exercise_rules = [r for r in rules if r.applies_to in ["exercise", "both"]]
    result.add_pass(f"运动安全规则: {len(exercise_rules)} 条")
    
    # 检查严重级别
    error_rules = [r for r in rules if r.severity == "error"]
    warning_rules = [r for r in rules if r.severity == "warning"]
    result.add_pass(f"硬性拦截规则: {len(error_rules)} 条")
    result.add_pass(f"警告规则: {len(warning_rules)} 条")
    
    # 检查规则ID唯一性
    rule_ids = [r.rule_id for r in rules]
    unique_ids = set(rule_ids)
    if len(rule_ids) != len(unique_ids):
        result.add_fail("规则ID重复", f"共{len(rule_ids)}个ID，{len(unique_ids)}个唯一")
    else:
        result.add_pass("所有规则ID唯一")
    
    return result


def test_integration():
    """集成测试 - 完整评估流程"""
    print("\n🔄 集成测试 - 完整评估流程...")
    result = TestResult()
    
    try:
        # 构建测试处方
        user = UserProfile(
            age=45, gender="女", height=160, weight=65,
            conditions=["高血脂"],
            exercise_level="初级",
            goal="减脂"
        )
        diet = DietPrescription(
            total_calories=1700,
            carbs_grams=180,
            protein_grams=80,
            fat_grams=50,
            meals_per_day=3,
            restrictions=["低脂", "少油"],
            recommendations=["多吃深海鱼", "增加膳食纤维"]
        )
        exercise = ExercisePrescription(
            frequency_per_week=4,
            duration_minutes=40,
            intensity="中强度",
            exercise_types=["快走", "游泳"],
            warm_up_minutes=5,
            cool_down_minutes=5,
            precautions=["运动时注意心率", "如有不适立即停止"]
        )
        prescription = Prescription(user_profile=user, diet=diet, exercise=exercise)
        
        # 完整评估流程
        from evaluator import evaluate
        
        eval_result = evaluate(prescription)
        
        # 验证结果结构
        assert hasattr(eval_result, 'safety_level')
        assert hasattr(eval_result, 'safety_score')
        assert hasattr(eval_result, 'overall_score')
        assert hasattr(eval_result, 'dimension_scores')
        assert len(eval_result.dimension_scores) == 5
        
        # 生成报告
        report_gen = ReportGenerator()
        text_report = report_gen.generate(eval_result, format="text")
        assert len(text_report) > 100
        
        result.add_pass("完整评估流程")
    except Exception as e:
        result.add_fail("完整评估流程", str(e))
    
    return result


def run_all_tests():
    """运行所有测试"""
    print("=" * 50)
    print("🧪 R+ Health 处方评审引擎 - 测试套件")
    print("=" * 50)
    
    results = []
    
    results.append(test_models())
    results.append(test_rule_engine())
    results.append(test_scoring())
    results.append(test_rules_coverage())
    results.append(test_integration())
    
    # 汇总
    total_passed = sum(r.passed for r in results)
    total_failed = sum(r.failed for r in results)
    total = total_passed + total_failed
    
    print("\n" + "=" * 50)
    print(f"🏁 最终结果: {total_passed}/{total} 通过")
    
    if total_failed == 0:
        print("✅ 所有测试通过！引擎工作正常。")
        return True
    else:
        print(f"❌ {total_failed} 个测试失败，请检查。")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
