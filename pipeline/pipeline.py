"""
MCP 数据生成流水线
自动批量调用 MCP 生成处方 + 引擎自动评审

设计目标:
- 用户画像覆盖矩阵：年龄×BMI×疾病×运动基础×目标
- 理论组合约 5760 种有效组合
- 数据目标：冷启动 2000 条，中期 20000 条，远期 60000-100000 条
"""
import json
import os
import random
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path

# MCP 相关
try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    print("⚠️ MCP SDK 未安装，运行: pip install mcp")

# 评审引擎
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from evaluator import evaluate, RuleEngine, ScoringEngine
from evaluator.models import (
    UserProfile, DietPrescription, ExercisePrescription, Prescription,
    SafetyLevel
)


# ============ 用户画像覆盖矩阵 ============

@dataclass
class ProfileDimension:
    """画像维度定义"""
    name: str
    values: List[Any]

AGE_GROUPS = [
    {"label": "18-25", "min": 18, "max": 25},
    {"label": "26-35", "min": 26, "max": 35},
    {"label": "36-45", "min": 36, "max": 45},
    {"label": "46-55", "min": 46, "max": 55},
    {"label": "56-65", "min": 56, "max": 65},
    {"label": "65+", "min": 65, "max": 80},
]

BMI_RANGES = [
    {"label": "偏瘦", "min": 16, "max": 18.4},
    {"label": "正常", "min": 18.5, "max": 23.9},
    {"label": "超重", "min": 24, "max": 27.9},
    {"label": "肥胖", "min": 28, "max": 40},
]

CONDITIONS = [
    [],
    ["糖尿病"],
    ["高血压"],
    ["心脏病"],
    ["高血脂"],
    ["脂肪肝"],
    ["糖尿病", "高血压"],
    ["高血脂", "脂肪肝"],
]

EXERCISE_LEVELS = ["无", "初级", "中级", "高级"]

GOALS = ["减脂", "增肌", "控糖", "降压", "增强体质", "术后康复"]

GENDERS = ["男", "女"]


def generate_random_profile(
    ensure_coverage: bool = False,
    force_conditions: Optional[List[str]] = None
) -> UserProfile:
    """
    生成随机用户画像
    
    Args:
        ensure_coverage: 是否确保覆盖所有维度组合
        force_conditions: 强制指定的基础疾病
    """
    # 随机选择维度
    age_range = random.choice(AGE_GROUPS)
    bmi_range = random.choice(BMI_RANGES)
    conditions = force_conditions or random.choice(CONDITIONS)
    exercise_level = random.choice(EXERCISE_LEVELS)
    goal = random.choice(GOALS)
    gender = random.choice(GENDERS)
    
    # 生成具体数值
    age = random.randint(age_range["min"], age_range["max"])
    height = random.randint(155, 185) if gender == "男" else random.randint(150, 175)
    bmi = random.uniform(bmi_range["min"], bmi_range["max"])
    weight = round(bmi * (height / 100) ** 2, 1)
    
    return UserProfile(
        age=age,
        gender=gender,
        height=height,
        weight=weight,
        bmi=round(bmi, 1),
        conditions=conditions,
        exercise_level=exercise_level,
        goal=goal
    )


# ============ MCP 连接管理 ============

class MCPClient:
    """
    MCP 客户端 - 连接 R+ Health MCP Server
    
    MCP Server: https://mcp-uat.rplushealth.cn/sse
    工具: create_diet_prescription, create_exercise_prescription
    """
    
    def __init__(
        self,
        server_url: str = "https://mcp-uat.rplushealth.cn/sse",
        timeout: int = 60
    ):
        self.server_url = server_url
        self.timeout = timeout
        self.session: Optional[Any] = None
        self._connected = False
    
    async def connect(self):
        """连接到 MCP Server"""
        if not MCP_AVAILABLE:
            raise RuntimeError("MCP SDK 未安装，请运行: pip install mcp")
        
        # 注意：生产环境需要配置正确的认证
        # 这里使用 SSE 连接
        print(f"🔗 连接到 MCP Server: {self.server_url}")
        
        # TODO: 实现 SSE 连接
        # 由于 MCP SSE 连接需要额外的配置，
        # 这里先实现 mock 模式用于测试
        self._connected = True
        print("✅ MCP 连接成功（Mock模式）")
    
    async def disconnect(self):
        """断开连接"""
        if self.session:
            await self.session.close()
        self._connected = False
    
    async def create_diet_prescription(
        self,
        user_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        调用 MCP 创建饮食处方
        
        Args:
            user_profile: 用户画像字典
            
        Returns:
            饮食处方字典
        """
        if not self._connected:
            await self.connect()
        
        # TODO: 实现真实的 MCP 调用
        # 目前返回模拟数据
        return self._mock_diet_prescription(user_profile)
    
    async def create_exercise_prescription(
        self,
        user_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        调用 MCP 创建运动处方
        
        Args:
            user_profile: 用户画像字典
            
        Returns:
            运动处方字典
        """
        if not self._connected:
            await self.connect()
        
        return self._mock_exercise_prescription(user_profile)
    
    def _mock_diet_prescription(self, user: Dict[str, Any]) -> Dict[str, Any]:
        """生成模拟饮食处方"""
        weight = user.get("weight", 65)
        goal = user.get("goal", "增强体质")
        
        # 根据目标计算热量
        goal_calories = {
            "减脂": 1500,
            "增肌": 2500,
            "控糖": 1800,
            "降压": 1600,
            "增强体质": 2000,
            "术后康复": 1800
        }
        total_cal = goal_calories.get(goal, 2000)
        
        # 添加一些随机变化
        total_cal = int(total_cal * random.uniform(0.9, 1.1))
        
        # 宏量营养素计算
        carbs = int(total_cal * 0.5 / 4)  # 50%碳水
        protein = int(weight * 1.2)  # 1.2g/kg
        fat = int((total_cal - carbs * 4 - protein * 4) / 9)
        
        return {
            "total_calories": total_cal,
            "carbs_grams": carbs,
            "protein_grams": protein,
            "fat_grams": fat,
            "meals_per_day": 3,
            "restrictions": [],
            "recommendations": ["均衡饮食", "定时定量"],
            "warnings": []
        }
    
    def _mock_exercise_prescription(self, user: Dict[str, Any]) -> Dict[str, Any]:
        """生成模拟运动处方"""
        age = user.get("age", 35)
        exercise_level = user.get("exercise_level", "无")
        goal = user.get("goal", "增强体质")
        
        # 根据运动基础和年龄确定强度
        intensity_map = {
            "无": "低强度",
            "初级": "低强度",
            "中级": "中强度",
            "高级": "中强度"
        }
        intensity = intensity_map.get(exercise_level, "低强度")
        
        # 根据年龄调整
        if age > 60:
            intensity = "低强度"
        
        # 频率和时长
        frequency_map = {"减脂": 5, "增肌": 4, "控糖": 4, "降压": 5, "增强体质": 3, "术后康复": 3}
        frequency = frequency_map.get(goal, 3)
        
        duration = 45 if intensity == "中强度" else 30
        
        # 运动类型
        type_map = {
            "减脂": ["快走", "慢跑", "游泳"],
            "增肌": ["力量训练", "器械训练"],
            "控糖": ["快走", "游泳", "太极"],
            "降压": ["快走", "游泳", "太极"],
            "增强体质": ["跑步", "游泳", "骑行"],
            "术后康复": ["散步", "太极", "轻度拉伸"]
        }
        exercise_types = type_map.get(goal, ["快走"])
        
        return {
            "frequency_per_week": frequency,
            "duration_minutes": duration,
            "intensity": intensity,
            "exercise_types": exercise_types,
            "warm_up_minutes": 5,
            "cool_down_minutes": 5,
            "precautions": ["运动前热身", "如有不适停止运动"]
        }


# ============ 数据生成流水线 ============

@dataclass
class PipelineConfig:
    """流水线配置"""
    output_dir: str = "data/raw"              # 输出目录
    target_count: int = 2000                 # 目标生成数量
    batch_size: int = 10                     # 每批处理数量
    save_interval: int = 50                   # 每多少条保存一次
    quality_threshold: float = 60.0           # 质量阈值（低于此分数不纳入数据集）
    use_mock_mcp: bool = True                 # 使用模拟MCP（测试用）
    mcp_server_url: str = "https://mcp-uat.rplushealth.cn/sse"


@dataclass
class PipelineStats:
    """流水线统计"""
    total_generated: int = 0
    total_evaluated: int = 0
    safe_prescriptions: int = 0
    blocked_prescriptions: int = 0
    high_quality: int = 0                    # 综合评分 >= 阈值
    low_quality: int = 0                     # 综合评分 < 阈值
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_generated": self.total_generated,
            "total_evaluated": self.total_evaluated,
            "safe_prescriptions": self.safe_prescriptions,
            "blocked_prescriptions": self.blocked_prescriptions,
            "high_quality": self.high_quality,
            "low_quality": self.low_quality,
            "quality_rate": f"{self.high_quality/max(1,self.total_evaluated)*100:.1f}%",
            "duration_seconds": (self.end_time - self.start_time).total_seconds() if self.end_time and self.start_time else None
        }


class DataPipeline:
    """
    数据生成流水线
    
    流程:
    1. 生成用户画像组合
    2. 调用 MCP 生成处方
    3. 评审引擎评估
    4. 分级存储（gold_standard / raw）
    5. 定期保存进度
    """
    
    def __init__(self, config: Optional[PipelineConfig] = None):
        self.config = config or PipelineConfig()
        self.stats = PipelineStats()
        self.engine = RuleEngine()
        self.scorer = ScoringEngine()
        self.mcp_client = MCPClient(server_url=self.config.mcp_server_url)
        
        # 输出目录
        self.output_dir = Path(self.config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 历史记录
        self.generated_profiles: List[Dict] = []
        self.evaluation_results: List[Dict] = []
    
    async def initialize(self):
        """初始化流水线"""
        print("=" * 60)
        print("🚀 数据生成流水线初始化")
        print("=" * 60)
        print(f"📂 输出目录: {self.output_dir}")
        print(f"🎯 目标数量: {self.config.target_count}")
        print(f"📊 质量阈值: {self.config.quality_threshold}")
        print(f"🔧 Mock模式: {self.config.use_mock_mcp}")
        
        if not self.config.use_mock_mcp:
            await self.mcp_client.connect()
        
        self.stats.start_time = datetime.now()
        print("\n✅ 初始化完成，开始生成数据...\n")
    
    async def run(self, count: Optional[int] = None):
        """
        运行流水线
        
        Args:
            count: 指定生成数量（覆盖配置）
        """
        await self.initialize()
        
        target = count or self.config.target_count
        self.stats.total_generated = target
        
        for i in range(target):
            try:
                # 1. 生成用户画像
                profile = generate_random_profile()
                
                # 2. 调用 MCP 生成处方
                prescription = await self._generate_prescription(profile)
                
                # 3. 评审引擎评估
                result = evaluate(prescription)
                
                # 4. 记录统计
                self._update_stats(result)
                
                # 5. 存储结果
                self._store_result(profile, prescription, result)
                
                # 6. 定期保存
                if (i + 1) % self.config.save_interval == 0:
                    self._save_checkpoint()
                    self._print_progress(i + 1, target)
                
            except Exception as e:
                print(f"❌ 生成失败 [{i+1}/{target}]: {e}")
                continue
        
        # 最终保存
        self._save_final()
        self.stats.end_time = datetime.now()
        self._print_summary()
    
    async def _generate_prescription(self, profile: UserProfile) -> Prescription:
        """生成处方"""
        user_dict = profile.to_dict()
        
        if self.config.use_mock_mcp:
            # Mock 模式
            diet_data = self.mcp_client._mock_diet_prescription(user_dict)
            exercise_data = self.mcp_client._mock_exercise_prescription(user_dict)
        else:
            # 真实 MCP 调用
            diet_data = await self.mcp_client.create_diet_prescription(user_dict)
            exercise_data = await self.mcp_client.create_exercise_prescription(user_dict)
        
        diet = DietPrescription(**diet_data)
        exercise = ExercisePrescription(**exercise_data)
        
        return Prescription(user_profile=profile, diet=diet, exercise=exercise)
    
    def _update_stats(self, result):
        """更新统计"""
        self.stats.total_evaluated += 1
        
        if result.safety_level == SafetyLevel.SAFE:
            self.stats.safe_prescriptions += 1
        else:
            self.stats.blocked_prescriptions += 1
        
        if result.overall_score >= self.config.quality_threshold:
            self.stats.high_quality += 1
        else:
            self.stats.low_quality += 1
    
    def _store_result(
        self,
        profile: UserProfile,
        prescription: Prescription,
        result
    ):
        """存储结果"""
        record = {
            "id": len(self.evaluation_results) + 1,
            "timestamp": datetime.now().isoformat(),
            "user_profile": profile.to_dict(),
            "prescription": prescription.to_dict(),
            "evaluation": result.to_dict(),
            "is_high_quality": result.overall_score >= self.config.quality_threshold,
            "is_safe": result.safety_level == SafetyLevel.SAFE
        }
        
        self.evaluation_results.append(record)
        
        # 分级存储
        if result.overall_score >= 80 and result.safety_level == SafetyLevel.SAFE:
            # 高质量安全处方 → gold_standard
            filepath = self.output_dir.parent / "gold_standard" / f"sample_{record['id']:06d}.json"
            filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(record, f, ensure_ascii=False, indent=2)
    
    def _save_checkpoint(self):
        """保存检查点"""
        checkpoint = {
            "timestamp": datetime.now().isoformat(),
            "stats": self.stats.to_dict(),
            "results_count": len(self.evaluation_results)
        }
        filepath = self.output_dir / "checkpoint.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(checkpoint, f, ensure_ascii=False, indent=2)
    
    def _save_final(self):
        """保存最终结果"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 保存完整数据
        filepath = self.output_dir / f"prescriptions_{timestamp}.jsonl"
        with open(filepath, "w", encoding="utf-8") as f:
            for record in self.evaluation_results:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        
        print(f"\n💾 完整数据已保存: {filepath}")
    
    def _print_progress(self, current: int, total: int):
        """打印进度"""
        pct = current / total * 100
        quality_rate = self.stats.high_quality / max(1, self.stats.total_evaluated) * 100
        
        print(f"📊 进度: {current}/{total} ({pct:.1f}%) | "
              f"高质量: {self.stats.high_quality} ({quality_rate:.1f}%) | "
              f"安全: {self.stats.safe_prescriptions}")
    
    def _print_summary(self):
        """打印最终摘要"""
        stats = self.stats.to_dict()
        
        print("\n" + "=" * 60)
        print("🏁 流水线执行完成")
        print("=" * 60)
        print(f"📊 总生成: {stats['total_generated']}")
        print(f"📝 总评估: {stats['total_evaluated']}")
        print(f"✅ 安全处方: {stats['safe_prescriptions']}")
        print(f"⚠️ 拦截处方: {stats['blocked_prescriptions']}")
        print(f"⭐ 高质量(≥{self.config.quality_threshold}): {stats['high_quality']}")
        print(f"📉 低质量: {stats['low_quality']}")
        print(f"🎯 高质量率: {stats['quality_rate']}")
        if stats['duration_seconds']:
            print(f"⏱️ 用时: {stats['duration_seconds']:.1f}秒")
        print("=" * 60)


# ============ CLI 入口 ============

async def main():
    """CLI 主入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="MCP 数据生成流水线")
    parser.add_argument("-n", "--count", type=int, default=50, help="生成数量")
    parser.add_argument("-o", "--output", default="data/raw", help="输出目录")
    parser.add_argument("--threshold", type=float, default=60.0, help="质量阈值")
    parser.add_argument("--mock", action="store_true", default=True, help="使用Mock模式")
    parser.add_argument("--real", dest="mock", action="store_false", help="使用真实MCP")
    
    args = parser.parse_args()
    
    config = PipelineConfig(
        output_dir=args.output,
        target_count=args.count,
        quality_threshold=args.threshold,
        use_mock_mcp=args.mock
    )
    
    pipeline = DataPipeline(config)
    await pipeline.run()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
