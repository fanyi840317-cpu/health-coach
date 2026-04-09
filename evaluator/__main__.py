"""
处方评审引擎 CLI 入口
用法:
    python -m evaluator                                    # 运行测试
    python -m evaluator eval <json_file>                   # 评估处方JSON文件
    python -m evaluator rules [--type diet|exercise]       # 列出规则
    python -m evaluator quick                              # 快速演示
"""
import sys
import json
import argparse
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from evaluator import (
    RuleEngine, ScoringEngine, ReportGenerator,
    evaluate, quick_check, get_all_rules, print_summary
)
from models import Prescription, UserProfile, DietPrescription, ExercisePrescription


def cmd_rules(args):
    """列出安全规则"""
    engine = RuleEngine()
    rules = engine.list_rules(by_type=args.type, by_severity=args.severity)
    
    print(f"\n📋 安全规则列表（共 {len(rules)} 条）")
    print("-" * 60)
    print(f"{'规则ID':<10} {'名称':<25} {'类型':<10} {'级别':<8}")
    print("-" * 60)
    
    for rule in rules:
        severity_icon = {"error": "🔴", "warning": "🟡", "info": "🔵"}.get(rule["severity"], "⚪")
        print(f"{rule['rule_id']:<10} {rule['name']:<25} {rule['applies_to']:<10} {severity_icon} {rule['severity']:<8}")
    
    print("-" * 60)


def cmd_quick_demo():
    """快速演示"""
    print("\n" + "=" * 60)
    print("⚡ 快速演示 - 处方评审引擎")
    print("=" * 60)
    
    # 创建测试处方
    user = UserProfile(
        age=45, gender="女", height=160, weight=65,
        conditions=["高血脂", "脂肪肝"],
        exercise_level="初级",
        goal="减脂"
    )
    
    diet = DietPrescription(
        total_calories=1700,
        carbs_grams=180,
        protein_grams=85,
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
    
    # 评估
    print("\n📝 正在评估处方...")
    result = evaluate(prescription, use_llm=False)
    
    # 打印摘要
    print_summary(result)
    
    # 打印完整报告
    print("\n" + ReportGenerator().generate(result, format="text"))
    
    # 测试危险处方
    print("\n" + "=" * 60)
    print("⚠️ 测试危险处方拦截...")
    print("=" * 60)
    
    danger_user = UserProfile(
        age=60, gender="男", height=165, weight=80,
        conditions=["心脏病", "糖尿病"],
        exercise_level="无",
        goal="降压"
    )
    
    danger_diet = DietPrescription(
        total_calories=2500,
        carbs_grams=350,  # 糖尿病碳水严重超标
        protein_grams=60,
        fat_grams=80
    )
    
    danger_exercise = ExercisePrescription(
        frequency_per_week=6,
        duration_minutes=90,
        intensity="高强度",  # 心脏病患者高强度运动
        exercise_types=["跑步"]
    )
    
    danger_prescription = Prescription(
        user_profile=danger_user,
        diet=danger_diet,
        exercise=danger_exercise
    )
    
    danger_result = evaluate(danger_prescription)
    print_summary(danger_result)
    print("\n" + ReportGenerator().generate(danger_result, format="text"))


def cmd_evaluate_file(filepath: str, output: str = None, format: str = "text", use_llm: bool = False):
    """评估处方文件"""
    print(f"\n📂 加载处方文件: {filepath}")
    
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ 文件读取失败: {e}")
        return
    
    try:
        # 解析处方
        user_data = data.get("user_profile", {})
        diet_data = data.get("diet", {})
        exercise_data = data.get("exercise", {})
        
        user = UserProfile(
            age=user_data.get("age", 30),
            gender=user_data.get("gender", "男"),
            height=user_data.get("height", 170),
            weight=user_data.get("weight", 65),
            bmi=user_data.get("bmi"),
            conditions=user_data.get("conditions", []),
            exercise_level=user_data.get("exercise_level", "无"),
            goal=user_data.get("goal", "增强体质")
        )
        
        diet = DietPrescription(
            total_calories=diet_data.get("total_calories", 2000),
            carbs_grams=diet_data.get("carbs_grams", 250),
            protein_grams=diet_data.get("protein_grams", 75),
            fat_grams=diet_data.get("fat_grams", 65),
            meals_per_day=diet_data.get("meals_per_day", 3),
            restrictions=diet_data.get("restrictions", []),
            recommendations=diet_data.get("recommendations", [])
        )
        
        exercise = ExercisePrescription(
            frequency_per_week=exercise_data.get("frequency_per_week", 3),
            duration_minutes=exercise_data.get("duration_minutes", 45),
            intensity=exercise_data.get("intensity", "中强度"),
            exercise_types=exercise_data.get("exercise_types", []),
            warm_up_minutes=exercise_data.get("warm_up_minutes", 5),
            cool_down_minutes=exercise_data.get("cool_down_minutes", 5)
        )
        
        prescription = Prescription(user_profile=user, diet=diet, exercise=exercise)
        
        # 评估
        print("📝 正在评估...")
        result = evaluate(prescription, use_llm=use_llm)
        
        # 输出
        if output:
            with open(output, "w", encoding="utf-8") as f:
                f.write(ReportGenerator().generate(result, format=format))
            print(f"✅ 报告已保存: {output}")
        else:
            print("\n" + ReportGenerator().generate(result, format=format))
        
        return result
        
    except Exception as e:
        print(f"❌ 处方解析失败: {e}")
        import traceback
        traceback.print_exc()


def main():
    parser = argparse.ArgumentParser(
        description="R+ Health 处方评审引擎",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python -m evaluator              # 运行测试套件
  python -m evaluator quick         # 快速演示
  python -m evaluator rules        # 列出所有规则
  python -m evaluator rules --type diet --severity error  # 列出饮食错误规则
  python -m evaluator eval test.json                    # 评估JSON文件
  python -m evaluator eval test.json -o report.md --format markdown
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="子命令")
    
    # rules 子命令
    rules_parser = subparsers.add_parser("rules", help="列出安全规则")
    rules_parser.add_argument("--type", choices=["diet", "exercise", "both"], 
                              help="按类型筛选")
    rules_parser.add_argument("--severity", choices=["error", "warning", "info"],
                              help="按严重程度筛选")
    
    # eval 子命令
    eval_parser = subparsers.add_parser("eval", help="评估处方文件")
    eval_parser.add_argument("file", help="处方JSON文件路径")
    eval_parser.add_argument("-o", "--output", help="输出文件路径")
    eval_parser.add_argument("--format", choices=["text", "json", "markdown", "html"],
                              default="text", help="输出格式")
    eval_parser.add_argument("--llm", action="store_true", help="启用LLM深度评审")
    
    # quick 子命令
    subparsers.add_parser("quick", help="快速演示")
    
    args = parser.parse_args()
    
    if args.command == "rules":
        cmd_rules(args)
    elif args.command == "eval":
        cmd_evaluate_file(args.file, args.output, args.format, args.llm)
    elif args.command == "quick":
        cmd_quick_demo()
    else:
        # 默认运行测试
        from evaluator.test_evaluator import run_all_tests
        run_all_tests()


if __name__ == "__main__":
    main()
