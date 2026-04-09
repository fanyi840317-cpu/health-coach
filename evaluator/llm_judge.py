"""
LLM 评审接口
Layer 2: 使用大语言模型进行深度评估
"""
import json
import os
from typing import Dict, Any, Optional, List
from models import Prescription


class LLMJudge:
    """
    LLM评审器 - 调用大语言模型对处方进行深度评估
    
    支持多种后端:
    - OpenAI (GPT-4)
    - Claude (Anthropic)
    - 通义千问 (阿里云)
    - DeepSeek
    - 本地模型
    """
    
    def __init__(
        self,
        provider: str = "openai",
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: float = 0.1
    ):
        """
        初始化LLM评审器
        
        Args:
            provider: 模型提供商 ("openai", "claude", "qwen", "deepseek")
            api_key: API密钥
            model: 模型名称（默认为各provider的推荐模型）
            base_url: API地址（用于代理或本地部署）
            temperature: 生成温度（0-1，越低越确定性）
        """
        self.provider = provider
        self.api_key = api_key or os.environ.get(f"{provider.upper()}_API_KEY", "")
        self.base_url = base_url or os.environ.get(f"{provider.upper()}_BASE_URL", "")
        self.temperature = temperature
        
        # 默认模型映射
        self.default_models = {
            "openai": "gpt-4o",
            "claude": "claude-3-5-sonnet-20241022",
            "qwen": "qwen-plus",
            "deepseek": "deepseek-chat"
        }
        self.model = model or self.default_models.get(provider, "gpt-4o")
        
        self._client = None
    
    def _get_client(self):
        """懒加载API客户端"""
        if self._client is not None:
            return self._client
        
        if self.provider == "openai":
            from openai import OpenAI
            self._client = OpenAI(api_key=self.api_key, base_url=self.base_url or None)
        elif self.provider == "claude":
            from anthropic import Anthropic
            self._client = Anthropic(api_key=self.api_key)
        elif self.provider == "qwen":
            from openai import OpenAI
            self._client = OpenAI(api_key=self.api_key, base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")
        elif self.provider == "deepseek":
            from openai import OpenAI
            self._client = OpenAI(api_key=self.api_key, base_url="https://api.deepseek.com")
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
        
        return self._client
    
    def judge(self, prescription: Prescription, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        对处方进行LLM评审
        
        Args:
            prescription: 待评审的处方
            context: 额外的上下文信息
            
        Returns:
            dict: 包含评分、理由、建议
        """
        prompt = self._build_prompt(prescription)
        
        try:
            response = self._call_llm(prompt)
            return self._parse_response(response)
        except Exception as e:
            return {
                "error": str(e),
                "status": "failed",
                "message": f"LLM调用失败: {e}"
            }
    
    def _build_prompt(self, prescription: Prescription) -> str:
        """构建评审提示词"""
        user = prescription.user_profile
        diet = prescription.diet
        exercise = prescription.exercise
        
        prompt = f"""你是一位资深临床营养师和运动医学专家。
请评估以下健康处方的质量和安全性。

【用户画像】
- 年龄: {user.age}岁
- 性别: {user.gender}
- 身高: {user.height}cm
- 体重: {user.weight}kg
- BMI: {user.get_bmi_category() if user.bmi else '未知'} ({round(user.bmi, 1) if user.bmi else '?'})
- 基础疾病: {', '.join(user.conditions) if user.conditions else '无'}
- 运动基础: {user.exercise_level}
- 健康目标: {user.goal}

【饮食处方】
- 总热量: {diet.total_calories} kcal/天
- 碳水: {diet.carbs_grams}g ({diet.get_macros_ratio()['carbs']}%)
- 蛋白质: {diet.protein_grams}g ({diet.get_macros_ratio()['protein']}%)
- 脂肪: {diet.fat_grams}g ({diet.get_macros_ratio()['fat']}%)
- 餐次: {diet.meals_per_day}次/天
- 饮食限制: {', '.join(diet.restrictions) if diet.restrictions else '无'}
- 建议: {', '.join(diet.recommendations) if diet.recommendations else '无'}
- 注意事项: {', '.join(diet.warnings) if diet.warnings else '无'}

【运动处方】
- 频率: {exercise.frequency_per_week}次/周
- 时长: {exercise.duration_minutes}分钟/次
- 强度: {exercise.intensity}
- 类型: {', '.join(exercise.exercise_types) if exercise.exercise_types else '未指定'}
- 目标心率: {exercise.target_heart_rate if exercise.target_heart_rate else '未设定'}
- 热身: {exercise.warm_up_minutes}分钟
- 放松: {exercise.cool_down_minutes}分钟
- 注意事项: {', '.join(exercise.precautions) if exercise.precautions else '无'}

请按以下5个维度评分（0-100分）并说明理由:

1. 安全性（权重30%）: 有无禁忌冲突或安全风险？
2. 适配性（权重25%）: 是否匹配用户的年龄、BMI、疾病和目标？
3. 科学性（权重20%）: 是否符合临床营养学和运动医学指南？
4. 完整性（权重15%）: 信息是否齐全，有无遗漏重要内容？
5. 可执行性（权重10%）: 用户能否实际执行，执行难度如何？

最后给出：
- 综合评分（0-100）
- 主要优点（1-3条）
- 主要问题（1-3条）
- 改进建议（1-3条）
- 是否适合作为训练数据: 是/否，并说明理由

请以JSON格式输出:
{{
  "scores": {{
    "safety": {{"score": 0-100, "reason": "..."}},
    "fitness": {{"score": 0-100, "reason": "..."}},
    "science": {{"score": 0-100, "reason": "..."}},
    "completeness": {{"score": 0-100, "reason": "..."}},
    "executability": {{"score": 0-100, "reason": "..."}}
  }},
  "overall_score": 0-100,
  "pros": ["...", "..."],
  "cons": ["...", "..."],
  "suggestions": ["...", "..."],
  "suitable_for_training": true/false,
  "training_note": "..."
}}
"""
        return prompt
    
    def _call_llm(self, prompt: str) -> str:
        """调用LLM API"""
        client = self._get_client()
        
        if self.provider == "claude":
            response = client.messages.create(
                model=self.model,
                max_tokens=2048,
                temperature=self.temperature,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
        else:
            response = client.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                messages=[
                    {"role": "system", "content": "你是一位专业的健康顾问和医学评审专家。请严格按照JSON格式输出。"},
                    {"role": "user", "content": prompt}
                ]
            )
            return response.choices[0].message.content
    
    def _parse_response(self, response: str) -> Dict[str, Any]:
        """解析LLM响应"""
        try:
            # 尝试提取JSON
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]
            
            return json.loads(response.strip())
        except json.JSONDecodeError:
            return {
                "error": "JSON解析失败",
                "raw_response": response[:500],
                "status": "parse_error"
            }
    
    def batch_judge(self, prescriptions: List[Prescription], max_concurrent: int = 3) -> List[Dict[str, Any]]:
        """
        批量评审处方
        
        Args:
            prescriptions: 处方列表
            max_concurrent: 最大并发数
            
        Returns:
            评审结果列表
        """
        results = []
        for i, p in enumerate(prescriptions):
            print(f"评审 [{i+1}/{len(prescriptions)}]...")
            result = self.judge(p)
            results.append(result)
        return results
    
    def set_api_key(self, api_key: str):
        """设置API密钥"""
        self.api_key = api_key
        self._client = None  # 重置客户端


def quick_judge(prescription: Prescription, api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    快速LLM评审（便捷函数）
    """
    judge = LLMJudge(api_key=api_key)
    return judge.judge(prescription)
