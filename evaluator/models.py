"""
数据模型定义
定义用户画像、处方、评估结果等核心数据结构
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime


class PrescribeType(Enum):
    """处方类型"""
    DIET = "diet"           # 饮食处方
    EXERCISE = "exercise"   # 运动处方
    COMBINED = "combined"   # 联合处方


class SafetyLevel(Enum):
    """安全等级"""
    SAFE = "safe"           # 安全
    WARNING = "warning"      # 警告
    DANGER = "danger"        # 危险
    BLOCKED = "blocked"      # 直接拦截


class BMICategory(Enum):
    """BMI分类"""
    UNDERWEIGHT = "偏瘦"      # < 18.5
    NORMAL = "正常"           # 18.5 - 24
    OVERWEIGHT = "超重"       # 24 - 28
    OBESE = "肥胖"            # > 28


class AgeGroup(Enum):
    """年龄段"""
    YOUNG = "18-25"
    YOUNG_ADULT = "26-35"
    MIDDLE = "36-45"
    MIDDLE_AGED = "46-55"
    SENIOR = "56-65"
    ELDERLY = "65+"


class ExerciseLevel(Enum):
    """运动基础"""
    NONE = "无"       # 0年
    BEGINNER = "初级"  # < 1年
    INTERMEDIATE = "中级"  # 1-3年
    ADVANCED = "高级"     # > 3年


class HealthGoal(Enum):
    """健康目标"""
    FAT_LOSS = "减脂"
    MUSCLE_GAIN = "增肌"
    BLOOD_SUGAR_CONTROL = "控糖"
    BLOOD_PRESSURE_CONTROL = "降压"
    FITNESS = "增强体质"
    REHABILITATION = "术后康复"


class Condition(Enum):
    """基础疾病/特殊情况"""
    DIABETES = "糖尿病"
    HYPERTENSION = "高血压"
    HEART_DISEASE = "心脏病"
    HYPERLIPIDEMIA = "高血脂"
    FATTY_LIVER = "脂肪肝"
    GOUT = "痛风"
    KIDNEY_DISEASE = "肾病"
    OSTEOPOROSIS = "骨质疏松"
    ASTHMA = "哮喘"
    NONE = "无"


@dataclass
class UserProfile:
    """用户画像"""
    age: int
    gender: str                          # "男" / "女"
    height: float                        # cm
    weight: float                        # kg
    bmi: Optional[float] = None
    conditions: List[str] = field(default_factory=list)  # 基础疾病列表
    exercise_level: str = "无"          # 运动基础
    goal: str = "增强体质"               # 健康目标
    
    def __post_init__(self):
        if self.bmi is None and self.height > 0:
            self.bmi = self.weight / ((self.height / 100) ** 2)
    
    def get_bmi_category(self) -> str:
        """获取BMI分类"""
        if self.bmi is None:
            return "未知"
        if self.bmi < 18.5:
            return BMICategory.UNDERWEIGHT.value
        elif self.bmi < 24:
            return BMICategory.NORMAL.value
        elif self.bmi < 28:
            return BMICategory.OVERWEIGHT.value
        else:
            return BMICategory.OBESE.value
    
    def has_condition(self, condition: str) -> bool:
        """检查是否有特定疾病"""
        return condition in self.conditions
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "age": self.age,
            "gender": self.gender,
            "height": self.height,
            "weight": self.weight,
            "bmi": round(self.bmi, 1) if self.bmi else None,
            "bmi_category": self.get_bmi_category(),
            "conditions": self.conditions,
            "exercise_level": self.exercise_level,
            "goal": self.goal
        }


@dataclass
class DietPrescription:
    """饮食处方"""
    total_calories: int                  # 总热量 (kcal/day)
    carbs_grams: float                   # 碳水 (g/day)
    protein_grams: float                 # 蛋白质 (g/day)
    fat_grams: float                     # 脂肪 (g/day)
    meals_per_day: int = 3               # 每日餐次
    meal_plan: Optional[Dict[str, Any]] = None  # 详细餐单
    restrictions: List[str] = field(default_factory=list)  # 饮食限制
    recommendations: List[str] = field(default_factory=list)  # 建议
    warnings: List[str] = field(default_factory=list)  # 注意事项
    
    def get_macros_ratio(self) -> Dict[str, float]:
        """获取宏量营养素比例"""
        total_cal = self.carbs_grams * 4 + self.protein_grams * 4 + self.fat_grams * 9
        if total_cal == 0:
            return {"carbs": 0, "protein": 0, "fat": 0}
        return {
            "carbs": round(self.carbs_grams * 4 / total_cal * 100, 1),
            "protein": round(self.protein_grams * 4 / total_cal * 100, 1),
            "fat": round(self.fat_grams * 9 / total_cal * 100, 1)
        }
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_calories": self.total_calories,
            "carbs_grams": self.carbs_grams,
            "protein_grams": self.protein_grams,
            "fat_grams": self.fat_grams,
            "macros_ratio": self.get_macros_ratio(),
            "meals_per_day": self.meals_per_day,
            "meal_plan": self.meal_plan,
            "restrictions": self.restrictions,
            "recommendations": self.recommendations,
            "warnings": self.warnings
        }


@dataclass
class ExercisePrescription:
    """运动处方"""
    frequency_per_week: int              # 每周运动次数
    duration_minutes: int                # 每次时长(分钟)
    intensity: str                       # "低强度" / "中强度" / "高强度"
    exercise_types: List[str] = field(default_factory=list)  # 运动类型
    target_heart_rate: Optional[Dict[str, int]] = None  # 目标心率区间
    warm_up_minutes: int = 5            # 热身时间
    cool_down_minutes: int = 5           # 放松时间
    precautions: List[str] = field(default_factory=list)  # 注意事项
    
    def get_intensity_level(self) -> int:
        """获取强度等级 1-3"""
        mapping = {"低强度": 1, "中强度": 2, "高强度": 3}
        return mapping.get(self.intensity, 1)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "frequency_per_week": self.frequency_per_week,
            "duration_minutes": self.duration_minutes,
            "intensity": self.intensity,
            "intensity_level": self.get_intensity_level(),
            "exercise_types": self.exercise_types,
            "target_heart_rate": self.target_heart_rate,
            "warm_up_minutes": self.warm_up_minutes,
            "cool_down_minutes": self.cool_down_minutes,
            "precautions": self.precautions
        }


@dataclass
class Prescription:
    """完整处方（饮食+运动）"""
    user_profile: UserProfile
    diet: DietPrescription
    exercise: ExercisePrescription
    prescription_type: str = "combined"   # "diet" / "exercise" / "combined"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    version: str = "1.0"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_profile": self.user_profile.to_dict(),
            "diet": self.diet.to_dict(),
            "exercise": self.exercise.to_dict(),
            "prescription_type": self.prescription_type,
            "created_at": self.created_at,
            "version": self.version
        }


@dataclass
class RuleViolation:
    """规则违规"""
    rule_id: str
    rule_name: str
    severity: str                        # "error" / "warning" / "info"
    message: str
    suggestion: Optional[str] = None


@dataclass
class DimensionScore:
    """单个维度评分"""
    dimension: str                       # 维度名称
    score: float                         # 分数 0-100
    weight: float                         # 权重
    reasons: List[str] = field(default_factory=list)  # 扣分原因
    suggestions: List[str] = field(default_factory=list)  # 改进建议


@dataclass
class EvaluationResult:
    """评估结果"""
    prescription: Prescription
    safety_level: SafetyLevel
    safety_score: float                  # 安全评分 0-100
    
    # 规则引擎结果
    violations: List[RuleViolation] = field(default_factory=list)
    passed_rules: int = 0
    failed_rules: int = 0
    
    # 多维度评分
    dimension_scores: List[DimensionScore] = field(default_factory=list)
    overall_score: float = 0.0           # 综合评分 0-100
    
    # LLM评审结果
    llm_judge_result: Optional[Dict[str, Any]] = None
    
    # 元信息
    evaluated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    engine_version: str = "1.0"
    
    def get_summary(self) -> Dict[str, Any]:
        """获取评估摘要"""
        return {
            "safety_level": self.safety_level.value,
            "safety_score": round(self.safety_score, 1),
            "overall_score": round(self.overall_score, 1),
            "violations_count": len(self.violations),
            "failed_rules": self.failed_rules,
            "passed_rules": self.passed_rules,
            "dimensions": {d.dimension: round(d.score, 1) for d in self.dimension_scores}
        }
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "safety_level": self.safety_level.value,
            "safety_score": round(self.safety_score, 1),
            "violations": [
                {
                    "rule_id": v.rule_id,
                    "rule_name": v.rule_name,
                    "severity": v.severity,
                    "message": v.message,
                    "suggestion": v.suggestion
                } for v in self.violations
            ],
            "passed_rules": self.passed_rules,
            "failed_rules": self.failed_rules,
            "dimension_scores": [
                {
                    "dimension": d.dimension,
                    "score": round(d.score, 1),
                    "weight": d.weight,
                    "reasons": d.reasons,
                    "suggestions": d.suggestions
                } for d in self.dimension_scores
            ],
            "overall_score": round(self.overall_score, 1),
            "llm_judge_result": self.llm_judge_result,
            "evaluated_at": self.evaluated_at,
            "engine_version": self.engine_version
        }
