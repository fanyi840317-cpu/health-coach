"""
多维度评分系统
Layer 2: 从安全性、适配性、科学性、完整性、可执行性五个维度评分
"""
from typing import List, Dict, Any
from models import Prescription, DimensionScore, UserProfile, DietPrescription, ExercisePrescription


# 维度权重配置
DIMENSION_WEIGHTS = {
    "安全性": 0.30,
    "适配性": 0.25,
    "科学性": 0.20,
    "完整性": 0.15,
    "可执行性": 0.10
}


class ScoringEngine:
    """
    多维度评分引擎
    
    评估处方的五个维度，给出0-100的综合评分
    """
    
    def __init__(self):
        self.weights = DIMENSION_WEIGHTS
    
    def score(self, prescription: Prescription, safety_score: float = 100.0) -> List[DimensionScore]:
        """
        对处方进行多维度评分
        
        Args:
            prescription: 待评分处方
            safety_score: 来自规则引擎的安全评分
            
        Returns:
            List[DimensionScore]: 各维度评分列表
        """
        scores = []
        
        # 1. 安全性评分（主要来自规则引擎，少量补充规则）
        safety = self._score_safety(prescription, safety_score)
        scores.append(safety)
        
        # 2. 适配性评分
        fitness = self._score_fitness(prescription)
        scores.append(fitness)
        
        # 3. 科学性评分
        science = self._score_science(prescription)
        scores.append(science)
        
        # 4. 完整性评分
        completeness = self._score_completeness(prescription)
        scores.append(completeness)
        
        # 5. 可执行性评分
        executability = self._score_executability(prescription)
        scores.append(executability)
        
        return scores
    
    def _score_safety(self, prescription: Prescription, engine_score: float) -> DimensionScore:
        """评估安全性维度"""
        reasons = []
        suggestions = []
        score = engine_score
        
        # 基于规则的补充检查
        user = prescription.user_profile
        diet = prescription.diet
        
        # 检查热量是否在合理范围
        bmr = user.weight * 24
        tdee = bmr * 1.5  # 假设轻活动水平
        if prescription.prescription_type in ["diet", "combined"]:
            if diet.total_calories < bmr * 0.8:
                reasons.append(f"热量摄入过低（{diet.total_calories}kcal < 基础代谢{int(bmr)}kcal的80%）")
                score = min(score, 60)
            elif diet.total_calories > tdee * 1.3:
                reasons.append(f"热量摄入偏高（{diet.total_calories}kcal > 估算TDEE{int(tdee)}kcal的130%）")
                score = min(score, 70)
        
        # 有基础疾病但无相关警告
        if len(user.conditions) > 0 and len(diet.warnings) == 0 and len(prescription.exercise.precautions) == 0:
            reasons.append("有基础疾病但处方缺少疾病相关警告")
            score = min(score, 75)
        
        if score >= 90 and not reasons:
            reasons.append("无安全风险，处方安全")
        
        return DimensionScore(
            dimension="安全性",
            score=min(100, max(0, score)),
            weight=self.weights["安全性"],
            reasons=reasons,
            suggestions=suggestions
        )
    
    def _score_fitness(self, prescription: Prescription) -> DimensionScore:
        """评估适配性维度 — 处方是否匹配用户特征"""
        reasons = []
        suggestions = []
        score = 100.0
        
        user = prescription.user_profile
        diet = prescription.diet
        exercise = prescription.exercise
        
        # 1. BMI与热量的匹配度
        if prescription.prescription_type in ["diet", "combined"]:
            expected_cal = self._calculate_expected_calories(user)
            cal_diff = abs(diet.total_calories - expected_cal) / expected_cal
            if cal_diff > 0.3:
                reasons.append(f"热量设定与用户BMI/目标不太匹配（偏差{int(cal_diff*100)}%）")
                score -= 20
            elif cal_diff > 0.15:
                reasons.append(f"热量设定与用户特征有轻微偏差（偏差{int(cal_diff*100)}%）")
                score -= 10
        
        # 2. 运动强度与用户运动基础的匹配度
        if prescription.prescription_type in ["exercise", "combined"]:
            if user.exercise_level == "无" and exercise.intensity == "高强度":
                reasons.append("无运动基础者直接高强度运动，强度过高")
                score -= 25
            elif user.exercise_level == "初级" and exercise.intensity == "高强度":
                reasons.append("初级运动者安排高强度运动，可能超出能力")
                score -= 15
        
        # 3. 运动频率与目标的匹配度
        if prescription.prescription_type in ["exercise", "combined"]:
            if user.goal == "减脂" and exercise.frequency_per_week < 3:
                reasons.append("减脂目标建议每周至少3次运动")
                score -= 10
            elif user.goal == "增肌" and exercise.frequency_per_week < 2:
                reasons.append("增肌目标需要足够的训练频率")
                score -= 10
        
        # 4. 饮食限制是否针对用户疾病
        if prescription.prescription_type in ["diet", "combined"]:
            disease_diet_map = {
                "糖尿病": ["低碳水", "少糖", "低GI"],
                "高血压": ["低钠", "少盐", "清淡"],
                "高血脂": ["低脂", "少油", "减少胆固醇"],
                "脂肪肝": ["低脂", "戒酒", "低碳水"],
                "痛风": ["低嘌呤", "多饮水"],
            }
            for disease in user.conditions:
                relevant_keywords = disease_diet_map.get(disease, [])
                if relevant_keywords and not any(k in str(diet.restrictions) for k in relevant_keywords):
                    reasons.append(f"糖尿病/{disease}用户处方缺少相关饮食限制")
                    score -= 10
        
        # 5. 年龄适应性
        if user.age > 60:
            if prescription.prescription_type in ["exercise", "combined"]:
                if exercise.duration_minutes > 60:
                    reasons.append("老年人单次运动时长不宜超过60分钟")
                    score -= 10
        
        if score >= 95 and not reasons:
            reasons.append("处方与用户特征高度匹配")
        
        return DimensionScore(
            dimension="适配性",
            score=min(100, max(0, score)),
            weight=self.weights["适配性"],
            reasons=reasons,
            suggestions=suggestions
        )
    
    def _score_science(self, prescription: Prescription) -> DimensionScore:
        """评估科学性维度 — 符合临床/营养学指南"""
        reasons = []
        suggestions = []
        score = 100.0
        
        diet = prescription.diet
        
        # 1. 宏量营养素比例科学性
        if prescription.prescription_type in ["diet", "combined"]:
            macros = diet.get_macros_ratio()
            
            # 碳水比例检查（40-65%为合理范围）
            carbs_ratio = macros["carbs"]
            if carbs_ratio < 40:
                reasons.append(f"碳水比例过低（{carbs_ratio}% < 40%），可能影响大脑功能")
                score -= 10
            elif carbs_ratio > 65:
                reasons.append(f"碳水比例偏高（{carbs_ratio}% > 65%），不利于血糖控制")
                score -= 10
            
            # 蛋白质比例检查
            protein_ratio = macros["protein"]
            if protein_ratio < 10:
                reasons.append(f"蛋白质比例过低（{protein_ratio}% < 10%），不足以维持肌肉")
                score -= 10
            
            # 脂肪比例检查（20-35%为合理范围）
            fat_ratio = macros["fat"]
            if fat_ratio < 20:
                reasons.append(f"脂肪比例过低（{fat_ratio}% < 20%），可能影响脂溶性维生素吸收")
                score -= 5
            elif fat_ratio > 35:
                reasons.append(f"脂肪比例偏高（{fat_ratio}% > 35%），不利于心血管健康")
                score -= 5
            
            # 蛋白质克数检查（每公斤体重）
            user = prescription.user_profile
            protein_per_kg = diet.protein_grams / user.weight
            if user.goal == "增肌" and protein_per_kg < 1.2:
                reasons.append(f"增肌目标蛋白质摄入偏低（{protein_per_kg:.1f}g/kg < 1.2g/kg）")
                score -= 10
            elif user.goal == "减脂" and protein_per_kg < 0.8:
                reasons.append(f"减脂目标蛋白质摄入偏低（{protein_per_kg:.1f}g/kg < 0.8g/kg）")
                score -= 10
        
        # 2. 运动科学性
        exercise = prescription.exercise
        if prescription.prescription_type in ["exercise", "combined"]:
            # 运动频率检查（ACSM建议每周150-300分钟中等强度）
            weekly_minutes = exercise.frequency_per_week * exercise.duration_minutes
            if weekly_minutes < 150:
                reasons.append(f"每周运动总时长偏低（{weekly_minutes}min < 150min），健康效益有限")
                score -= 10
            elif weekly_minutes > 300 and user.age > 50:
                reasons.append(f"每周运动时长偏长，老年人应注意休息")
                score -= 5
            
            # 强度与频率组合
            if exercise.intensity == "高强度" and exercise.frequency_per_week > 5:
                reasons.append("高强度运动每周不宜超过5次，避免过度训练")
                score -= 10
        
        if score >= 95 and not reasons:
            reasons.append("符合临床营养和运动科学指南")
        
        return DimensionScore(
            dimension="科学性",
            score=min(100, max(0, score)),
            weight=self.weights["科学性"],
            reasons=reasons,
            suggestions=suggestions
        )
    
    def _score_completeness(self, prescription: Prescription) -> DimensionScore:
        """评估完整性维度 — 信息是否齐全"""
        reasons = []
        suggestions = []
        score = 100.0
        missing = []
        
        diet = prescription.diet
        exercise = prescription.exercise
        user = prescription.user_profile
        
        # 饮食处方完整性
        if prescription.prescription_type in ["diet", "combined"]:
            required_diet_fields = [
                ("总热量", diet.total_calories > 0),
                ("碳水", diet.carbs_grams > 0),
                ("蛋白质", diet.protein_grams > 0),
                ("脂肪", diet.fat_grams > 0),
            ]
            for field, has_value in required_diet_fields:
                if not has_value:
                    missing.append(f"饮食-{field}")
                    score -= 5
            
            # 详细餐单
            if diet.meal_plan is None or len(diet.meal_plan) == 0:
                missing.append("详细餐单")
                score -= 10
        
        # 运动处方完整性
        if prescription.prescription_type in ["exercise", "combined"]:
            required_ex_fields = [
                ("运动频率", exercise.frequency_per_week > 0),
                ("运动时长", exercise.duration_minutes > 0),
                ("运动强度", exercise.intensity != ""),
            ]
            for field, has_value in required_ex_fields:
                if not has_value:
                    missing.append(f"运动-{field}")
                    score -= 5
            
            # 运动类型
            if len(exercise.exercise_types) == 0:
                missing.append("运动类型")
                score -= 10
        
        # 用户档案完整性
        user_fields = [
            ("年龄", user.age > 0),
            ("性别", user.gender in ["男", "女"]),
            ("身高体重", user.height > 0 and user.weight > 0),
        ]
        for field, has_value in user_fields:
            if not has_value:
                missing.append(f"用户-{field}")
                score -= 10
        
        if missing:
            reasons.append(f"缺失必要信息: {', '.join(missing)}")
            suggestions.append("请补充完整的处方信息")
        
        if score >= 95 and not missing:
            reasons.append("处方信息完整齐全")
        
        return DimensionScore(
            dimension="完整性",
            score=min(100, max(0, score)),
            weight=self.weights["完整性"],
            reasons=reasons,
            suggestions=suggestions
        )
    
    def _score_executability(self, prescription: Prescription) -> DimensionScore:
        """评估可执行性维度 — 用户能否实际执行"""
        reasons = []
        suggestions = []
        score = 100.0
        
        diet = prescription.diet
        exercise = prescription.exercise
        user = prescription.user_profile
        
        # 1. 饮食可执行性
        if prescription.prescription_type in ["diet", "combined"]:
            # 检查推荐食物是否过于昂贵或难以获取
            expensive_items = ["牛油果", "三文鱼", "藜麦", "奇亚籽", "羽衣甘蓝"]
            if diet.recommendations:
                expensive_count = sum(1 for r in diet.recommendations if any(e in str(r) for e in expensive_items))
                if expensive_count > 3:
                    reasons.append("推荐食材中进口/高价食材偏多，执行成本较高")
                    suggestions.append("可选择本地应季食材替代，降低执行难度")
                    score -= 10
            
            # 检查热量是否太极端（难以坚持）
            if diet.total_calories < 1200:
                reasons.append(f"极低热量（{diet.total_calories}kcal）难以长期坚持")
                suggestions.append("建议设定更可持续的热量目标")
                score -= 15
        
        # 2. 运动可执行性
        if prescription.prescription_type in ["exercise", "combined"]:
            # 检查运动时长是否合理
            if exercise.duration_minutes > 90:
                reasons.append("单次运动超过90分钟，执行难度大")
                suggestions.append("建议拆分为两次运动或缩短单次时长")
                score -= 10
            
            # 检查运动类型是否需要特殊设备
            equipment_types = ["游泳", "健身房的器械", "动感单车"]
            need_equipment = [t for t in exercise.exercise_types if any(e in t for e in ["游泳", "健身房"])]
            if len(need_equipment) > 0 and user.goal == "居家":
                reasons.append(f"部分运动类型（{', '.join(need_equipment)}）需要特殊场地/设备")
                suggestions.append("建议增加无需特殊设备的运动选项")
                score -= 10
        
        if score >= 95 and not reasons:
            reasons.append("处方执行难度适中，用户可以坚持")
        
        return DimensionScore(
            dimension="可执行性",
            score=min(100, max(0, score)),
            weight=self.weights["可执行性"],
            reasons=reasons,
            suggestions=suggestions
        )
    
    def _calculate_expected_calories(self, user: UserProfile) -> float:
        """估算用户每日所需热量（简单版）"""
        height_m = user.height / 100
        bmr = 10 * user.weight + 6.25 * user.height - 5 * user.age + (5 if user.gender == "男" else -161)
        
        # 活动系数（估算）
        activity_factors = {
            "无": 1.2,
            "初级": 1.375,
            "中级": 1.55,
            "高级": 1.725
        }
        activity = activity_factors.get(user.exercise_level, 1.2)
        tdee = bmr * activity
        
        # 根据目标调整
        goal_adjustments = {
            "减脂": 0.8,
            "增肌": 1.15,
            "控糖": 0.9,
            "降压": 0.85,
            "增强体质": 1.0,
            "术后康复": 1.0
        }
        adjustment = goal_adjustments.get(user.goal, 1.0)
        
        return tdee * adjustment
    
    def calculate_overall_score(self, dimension_scores: List[DimensionScore]) -> float:
        """计算综合评分"""
        if not dimension_scores:
            return 0.0
        
        total = sum(d.score * d.weight for d in dimension_scores)
        return min(100.0, max(0.0, round(total, 1)))
