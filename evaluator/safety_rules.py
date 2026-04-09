"""
安全规则库
定义所有硬性安全规则和软性警告规则
"""
from typing import Callable, Dict, Any, List
from dataclasses import dataclass


@dataclass
class SafetyRule:
    """安全规则定义"""
    rule_id: str
    name: str
    description: str
    severity: str                          # "error", "warning", "info"
    check_fn: Callable[[Any, Any], bool]   # 检查函数
    message: str                           # 违规消息模板
    suggestion: str                        # 改进建议
    applies_to: str = "both"              # "diet", "exercise", "both"


# ============ 饮食安全规则 ============

DIET_SAFETY_RULES: List[SafetyRule] = [
    # --- 硬性拦截规则 (error) ---
    SafetyRule(
        rule_id="DIET_001",
        name="糖尿病碳水超标",
        description="糖尿病患者每日碳水摄入不应超过200g",
        severity="error",
        applies_to="diet",
        check_fn=lambda user, diet: (
            "糖尿病" in user.conditions and diet.carbs_grams > 200
        ),
        message="糖尿病患者碳水摄入超标（当前: {carbs}g，建议 ≤200g/天）",
        suggestion="减少主食、水果、甜食摄入，增加蔬菜和优质蛋白"
    ),
    SafetyRule(
        rule_id="DIET_002",
        name="高血压高钠饮食",
        description="高血压患者应严格控制钠摄入",
        severity="error",
        applies_to="diet",
        check_fn=lambda user, diet: (
            "高血压" in user.conditions
        ),
        message="高血压患者需特别注意低钠饮食",
        suggestion="避免腌制食品、加工食品，每日盐摄入<5g"
    ),
    SafetyRule(
        rule_id="DIET_003",
        name="热量严重不足",
        description="每日热量摄入不应低于基础代谢",
        severity="error",
        applies_to="diet",
        check_fn=lambda user, diet: (
            diet.total_calories < user.weight * 18  # 约18kcal/kg为基础代谢下限
        ),
        message="热量摄入严重不足（当前: {calories}kcal，可能低于基础代谢）",
        suggestion="增加适量健康食物摄入，确保不低于基础代谢需求"
    ),
    SafetyRule(
        rule_id="DIET_004",
        name="热量严重超标",
        description="每日热量摄入不应高于TDEE+50%",
        severity="error",
        applies_to="diet",
        check_fn=lambda user, diet: (
            diet.total_calories > user.weight * 50  # 约50kcal/kg为极限
        ),
        message="热量摄入过高（当前: {calories}kcal/d）",
        suggestion="减少高热量食物，遵循处方中的热量建议"
    ),
    SafetyRule(
        rule_id="DIET_005",
        name="蛋白质严重不足",
        description="减脂/增肌时蛋白质摄入需充足",
        severity="error",
        applies_to="diet",
        check_fn=lambda user, diet: (
            diet.protein_grams < user.weight * 0.8
        ),
        message="蛋白质摄入不足（当前: {protein}g，建议 ≥{min_protein}g）",
        suggestion="增加优质蛋白来源：鸡胸肉、鱼、蛋、豆制品"
    ),
    SafetyRule(
        rule_id="DIET_006",
        name="脂肪肝低碳水",
        description="脂肪肝患者不宜过度低碳水",
        severity="error",
        applies_to="diet",
        check_fn=lambda user, diet: (
            "脂肪肝" in user.conditions and diet.carbs_grams < 150
        ),
        message="脂肪肝患者碳水摄入过低（当前: {carbs}g）",
        suggestion="脂肪肝患者需要适量碳水，选择低GI主食，避免过度低碳"
    ),
    SafetyRule(
        rule_id="DIET_007",
        name="痛风高嘌呤",
        description="痛风患者需限制高嘌呤食物",
        severity="error",
        applies_to="diet",
        check_fn=lambda user, diet: (
            "痛风" in user.conditions and diet.restrictions and "限制高嘌呤" not in diet.restrictions
        ),
        message="痛风患者处方中未包含高嘌呤食物限制",
        suggestion="痛风患者应限制动物内脏、海鲜、浓汤等高嘌呤食物"
    ),
    SafetyRule(
        rule_id="DIET_008",
        name="肾病高蛋白",
        description="肾病患者需限制蛋白质摄入",
        severity="error",
        applies_to="diet",
        check_fn=lambda user, diet: (
            "肾病" in user.conditions and diet.protein_grams > user.weight * 0.8
        ),
        message="肾病患者蛋白质摄入过高（当前: {protein}g）",
        suggestion="肾病患者应限制蛋白质摄入，遵医嘱调整"
    ),
    SafetyRule(
        rule_id="DIET_009",
        name="骨质疏松未补钙",
        description="骨质疏松患者需补充钙和维生素D",
        severity="error",
        applies_to="diet",
        check_fn=lambda user, diet: (
            "骨质疏松" in user.conditions and "钙" not in str(diet.restrictions) and "维生素D" not in str(diet.restrictions)
        ),
        message="骨质疏松患者处方中未包含钙/维生素D补充建议",
        suggestion="骨质疏松患者需补充钙和维生素D，多晒太阳，适量负重运动"
    ),
    
    # --- 警告规则 (warning) ---
    SafetyRule(
        rule_id="DIET_101",
        name="宏量营养素比例异常",
        description="碳水/蛋白/脂肪比例应在合理范围",
        severity="warning",
        applies_to="diet",
        check_fn=lambda user, diet: (
            diet.carbs_grams * 4 + diet.protein_grams * 4 + diet.fat_grams * 9 > 0 and
            not (0.4 <= diet.carbs_grams * 4 / (diet.carbs_grams * 4 + diet.protein_grams * 4 + diet.fat_grams * 9) <= 0.65)
        ),
        message="宏量营养素比例可能不合理",
        suggestion="碳水应占总热量40-65%，蛋白质10-35%，脂肪20-35%"
    ),
    SafetyRule(
        rule_id="DIET_102",
        name="餐次不合理",
        description="每日餐次应在2-6次之间",
        severity="warning",
        applies_to="diet",
        check_fn=lambda user, diet: (
            diet.meals_per_day < 2 or diet.meals_per_day > 6
        ),
        message=f"每日餐次({diet.meals_per_day})不在合理范围(2-6次)",
        suggestion="建议每日3-5餐，避免漏餐或暴饮暴食"
    ),
    SafetyRule(
        rule_id="DIET_103",
        name="无饮食限制说明",
        description="有基础疾病时应包含饮食限制",
        severity="warning",
        applies_to="diet",
        check_fn=lambda user, diet: (
            len(user.conditions) > 0 and len(diet.restrictions) == 0
        ),
        message="用户有基础疾病但处方未包含饮食限制说明",
        suggestion="针对用户的基础疾病添加相应的饮食限制说明"
    ),
]

# ============ 运动安全规则 ============

EXERCISE_SAFETY_RULES: List[SafetyRule] = [
    # --- 硬性拦截规则 (error) ---
    SafetyRule(
        rule_id="EX_001",
        name="心脏病患者高强度运动",
        description="心脏病患者禁止高强度运动",
        severity="error",
        applies_to="exercise",
        check_fn=lambda user, ex: (
            "心脏病" in user.conditions and ex.intensity == "高强度"
        ),
        message="心脏病患者禁止高强度运动",
        suggestion="心脏病患者应以低中强度有氧运动为主，如快走、太极、游泳"
    ),
    SafetyRule(
        rule_id="EX_002",
        name="高血压患者高强度运动",
        description="高血压患者应避免高强度运动",
        severity="error",
        applies_to="exercise",
        check_fn=lambda user, ex: (
            "高血压" in user.conditions and ex.intensity == "高强度"
        ),
        message="高血压患者高强度运动有风险",
        suggestion="高血压患者建议中低强度运动，运动时避免憋气"
    ),
    SafetyRule(
        rule_id="EX_003",
        name="骨质疏松患者高冲击运动",
        description="骨质疏松患者禁止高冲击运动",
        severity="error",
        applies_to="exercise",
        check_fn=lambda user, ex: (
            "骨质疏松" in user.conditions and 
            any(t in ["跑步", "跳跃", "篮球", "足球"] for t in ex.exercise_types)
        ),
        message="骨质疏松患者禁止高冲击运动",
        suggestion="骨质疏松患者适合游泳、走路、太极等低冲击运动"
    ),
    SafetyRule(
        rule_id="EX_004",
        name="运动时长过长",
        description="每次运动时长不宜超过120分钟",
        severity="error",
        applies_to="exercise",
        check_fn=lambda user, ex: (
            ex.duration_minutes > 120
        ),
        message="单次运动时长过长（当前: {duration}分钟）",
        suggestion="单次运动建议控制在60-90分钟内，避免过度疲劳"
    ),
    SafetyRule(
        rule_id="EX_005",
        name="无运动基础直接高强度",
        description="无运动基础者应从低强度开始",
        severity="error",
        applies_to="exercise",
        check_fn=lambda user, ex: (
            user.exercise_level == "无" and ex.intensity == "高强度"
        ),
        message="无运动基础者不宜直接进行高强度运动",
        suggestion="建议从低强度开始，循序渐进增加强度"
    ),
    SafetyRule(
        rule_id="EX_006",
        name="运动频率过低",
        description="每周运动频率不宜低于2次",
        severity="error",
        applies_to="exercise",
        check_fn=lambda user, ex: (
            ex.frequency_per_week < 2
        ),
        message="运动频率过低（当前: {freq}次/周）",
        suggestion="建议每周至少运动3次才能达到健康效果"
    ),
    SafetyRule(
        rule_id="EX_007",
        name="哮喘患者高强度/冷空气运动",
        description="哮喘患者应避免诱发因素",
        severity="error",
        applies_to="exercise",
        check_fn=lambda user, ex: (
            "哮喘" in user.conditions and ex.intensity == "高强度"
        ),
        message="哮喘患者高强度运动有风险",
        suggestion="哮喘患者运动前需吸入支气管扩张剂，避免冷空气运动"
    ),
    SafetyRule(
        rule_id="EX_008",
        name="无热身/放松",
        description="运动处方应包含热身和放松",
        severity="error",
        applies_to="exercise",
        check_fn=lambda user, ex: (
            ex.warm_up_minutes < 3 or ex.cool_down_minutes < 3
        ),
        message=f"运动处方热身/放松时间不足（热身:{ex.warm_up_minutes}min, 放松:{ex.cool_down_minutes}min）",
        suggestion="每次运动前后应有5-10分钟热身和放松"
    ),
    
    # --- 警告规则 (warning) ---
    SafetyRule(
        rule_id="EX_101",
        name="缺乏运动多样性",
        description="运动类型应包含有氧+力量+柔韧",
        severity="warning",
        applies_to="exercise",
        check_fn=lambda user, ex: (
            len(ex.exercise_types) < 2
        ),
        message="运动类型过于单一",
        suggestion="建议综合有氧、力量、柔韧训练，全面提升健康"
    ),
    SafetyRule(
        rule_id="EX_102",
        name="老年人缺少平衡训练",
        description="老年人运动处方应包含平衡训练",
        severity="warning",
        applies_to="exercise",
        check_fn=lambda user, ex: (
            user.age > 60 and "平衡" not in str(ex.exercise_types) and "太极" not in str(ex.exercise_types)
        ),
        message="老年用户运动处方缺少平衡训练",
        suggestion="60岁以上人群应加入平衡训练，预防跌倒"
    ),
    SafetyRule(
        rule_id="EX_103",
        name="目标心率未设定",
        description="运动处方应包含目标心率区间",
        severity="warning",
        applies_to="exercise",
        check_fn=lambda user, ex: (
            ex.target_heart_rate is None or len(ex.target_heart_rate) == 0
        ),
        message="运动处方缺少目标心率区间",
        suggestion="应设定目标心率区间（通常为最大心率的50-85%）"
    ),
    SafetyRule(
        rule_id="EX_104",
        name="术后康复缺少专业指导说明",
        description="术后康复运动需要专业指导",
        severity="warning",
        applies_to="exercise",
        check_fn=lambda user, ex: (
            user.goal == "术后康复" and len(ex.precautions) < 3
        ),
        message="术后康复运动需要更详细的专业指导说明",
        suggestion="术后康复运动应在医生指导下进行，提供详细的注意事项"
    ),
]


def get_all_rules() -> List[SafetyRule]:
    """获取所有安全规则"""
    return DIET_SAFETY_RULES + EXERCISE_SAFETY_RULES


def get_rules_by_severity(severity: str) -> List[SafetyRule]:
    """按严重程度获取规则"""
    return [r for r in get_all_rules() if r.severity == severity]


def get_rules_by_type(prescription_type: str) -> List[SafetyRule]:
    """按处方类型获取规则"""
    return [
        r for r in get_all_rules() 
        if r.applies_to == prescription_type or r.applies_to == "both"
    ]
