"""
评估报告生成器
生成可读性强的评估报告
"""
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from models import EvaluationResult, Prescription


class ReportGenerator:
    """
    评估报告生成器
    
    支持多种格式输出:
    - text: 纯文本格式
    - json: 结构化JSON
    - html: 格式化HTML
    - markdown: Markdown格式
    """
    
    def __init__(self, include_llm: bool = True):
        self.include_llm = include_llm
    
    def generate(
        self,
        result: EvaluationResult,
        format: str = "text",
        title: str = "处方质量评估报告"
    ) -> str:
        """
        生成评估报告
        
        Args:
            result: 评估结果
            format: 输出格式 ("text", "json", "html", "markdown")
            title: 报告标题
            
        Returns:
            格式化报告字符串
        """
        if format == "json":
            return self._generate_json(result)
        elif format == "html":
            return self._generate_html(result, title)
        elif format == "markdown":
            return self._generate_markdown(result, title)
        else:
            return self._generate_text(result, title)
    
    def _generate_text(self, result: EvaluationResult, title: str) -> str:
        """生成纯文本报告"""
        lines = []
        lines.append("=" * 60)
        lines.append(f"  {title}")
        lines.append("=" * 60)
        
        # 基本信息
        lines.append(f"\n📋 评估时间: {result.evaluated_at}")
        lines.append(f"🔧 引擎版本: {result.engine_version}")
        
        # 总体评分
        lines.append(f"\n{'=' * 60}")
        lines.append("📊 综合评分")
        lines.append("=" * 60)
        
        # 安全等级
        level_emoji = {
            "safe": "🟢",
            "warning": "🟡",
            "danger": "🟠",
            "blocked": "🔴"
        }
        lines.append(f"安全等级: {level_emoji.get(result.safety_level.value, '⚪')} {result.safety_level.value.upper()}")
        lines.append(f"安全评分: {result.safety_score:.1f} / 100")
        lines.append(f"综合评分: {result.overall_score:.1f} / 100")
        
        # 维度评分
        lines.append(f"\n{'=' * 60}")
        lines.append("📈 各维度评分")
        lines.append("=" * 60)
        
        for dim in result.dimension_scores:
            score_bar = self._make_bar(dim.score, 40)
            lines.append(f"  {dim.dimension} ({dim.weight*100:.0f}%权重): {dim.score:.1f} {score_bar}")
            if dim.reasons:
                for reason in dim.reasons:
                    lines.append(f"    └─ {reason}")
        
        # 规则检查
        lines.append(f"\n{'=' * 60}")
        lines.append("🔍 规则检查")
        lines.append("=" * 60)
        lines.append(f"通过规则: {result.passed_rules} 条")
        lines.append(f"违规规则: {result.failed_rules} 条")
        
        if result.violations:
            lines.append(f"\n⚠️ 违规详情:")
            for v in result.violations:
                severity_icon = {"error": "🔴", "warning": "🟡", "info": "🔵"}.get(v.severity, "⚪")
                lines.append(f"  {severity_icon} [{v.rule_id}] {v.rule_name}")
                lines.append(f"      问题: {v.message}")
                if v.suggestion:
                    lines.append(f"      建议: {v.suggestion}")
        
        # 用户画像摘要
        user = result.prescription.user_profile
        lines.append(f"\n{'=' * 60}")
        lines.append("👤 用户画像摘要")
        lines.append("=" * 60)
        lines.append(f"  {user.age}岁 {user.gender}, {user.height}cm, {user.weight}kg")
        lines.append(f"  BMI: {user.get_bmi_category()} ({round(user.bmi, 1) if user.bmi else '?'})")
        lines.append(f"  疾病: {', '.join(user.conditions) if user.conditions else '无'}")
        lines.append(f"  运动: {user.exercise_level}, 目标: {user.goal}")
        
        # LLM评审结果（如果有）
        if result.llm_judge_result and self.include_llm:
            lines.append(f"\n{'=' * 60}")
            lines.append("🤖 LLM评审结果")
            lines.append("=" * 60)
            llm = result.llm_judge_result
            
            if "overall_score" in llm:
                lines.append(f"  综合评分: {llm.get('overall_score', 'N/A')}")
            
            if "pros" in llm and llm["pros"]:
                lines.append(f"\n  ✅ 优点:")
                for pro in llm["pros"]:
                    lines.append(f"     • {pro}")
            
            if "cons" in llm and llm["cons"]:
                lines.append(f"\n  ❌ 问题:")
                for con in llm["cons"]:
                    lines.append(f"     • {con}")
            
            if "suggestions" in llm and llm["suggestions"]:
                lines.append(f"\n  💡 建议:")
                for sug in llm["suggestions"]:
                    lines.append(f"     • {sug}")
            
            if "suitable_for_training" in llm:
                status = "✅ 适合" if llm["suitable_for_training"] else "❌ 不适合"
                lines.append(f"\n  训练数据: {status}")
        
        lines.append("\n" + "=" * 60)
        lines.append("报告结束")
        lines.append("=" * 60)
        
        return "\n".join(lines)
    
    def _generate_json(self, result: EvaluationResult) -> str:
        """生成JSON格式报告"""
        output = result.to_dict()
        output["prescription_summary"] = {
            "user_age": result.prescription.user_profile.age,
            "user_gender": result.prescription.user_profile.gender,
            "user_bmi": result.prescription.user_profile.bmi,
            "user_conditions": result.prescription.user_profile.conditions,
            "user_goal": result.prescription.user_profile.goal,
            "diet_calories": result.prescription.diet.total_calories,
            "exercise_frequency": result.prescription.exercise.frequency_per_week
        }
        return json.dumps(output, ensure_ascii=False, indent=2)
    
    def _generate_markdown(self, result: EvaluationResult, title: str) -> str:
        """生成Markdown格式报告"""
        md = []
        md.append(f"# {title}\n")
        md.append(f"**评估时间**: {result.evaluated_at}\n")
        
        # 评分概览
        md.append("## 📊 评分概览\n")
        md.append(f"| 指标 | 评分 |")
        md.append(f"|------|------|")
        md.append(f"| 综合评分 | **{result.overall_score:.1f}** |")
        md.append(f"| 安全评分 | {result.safety_score:.1f} |")
        md.append(f"| 安全等级 | {result.safety_level.value} |")
        
        # 维度评分
        md.append("\n## 📈 各维度评分\n")
        md.append(f"| 维度 | 权重 | 评分 | 理由 |")
        md.append(f"|------|------|------|------|")
        for dim in result.dimension_scores:
            reasons = "; ".join(dim.reasons[:2]) if dim.reasons else "-"
            md.append(f"| {dim.dimension} | {dim.weight*100:.0f}% | {dim.score:.1f} | {reasons} |")
        
        # 违规详情
        if result.violations:
            md.append("\n## ⚠️ 违规详情\n")
            for v in result.violations:
                md.append(f"### [{v.rule_id}] {v.rule_name}\n")
                md.append(f"- **问题**: {v.message}\n")
                if v.suggestion:
                    md.append(f"- **建议**: {v.suggestion}\n")
        
        return "\n".join(md)
    
    def _generate_html(self, result: EvaluationResult, title: str) -> str:
        """生成HTML格式报告"""
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
        .score-card {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 12px; margin: 20px 0; }}
        .score {{ font-size: 48px; font-weight: bold; }}
        .dimension {{ background: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 8px; }}
        .violation {{ background: #fff3cd; padding: 12px; margin: 8px 0; border-left: 4px solid #ffc107; }}
        .error {{ background: #f8d7da; border-left-color: #dc3545; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <p>评估时间: {result.evaluated_at}</p>
    
    <div class="score-card">
        <div>综合评分</div>
        <div class="score">{result.overall_score:.1f}<small>/100</small></div>
        <div>安全等级: {result.safety_level.value.upper()}</div>
    </div>
    
    <h2>各维度评分</h2>
    <table>
        <tr><th>维度</th><th>权重</th><th>评分</th></tr>
"""
        for dim in result.dimension_scores:
            html += f"        <tr><td>{dim.dimension}</td><td>{dim.weight*100:.0f}%</td><td>{dim.score:.1f}</td></tr>\n"
        
        html += """    </table>
    
"""
        if result.violations:
            html += "    <h2>⚠️ 违规详情</h2>\n"
            for v in result.violations:
                cls = "error" if v.severity == "error" else ""
                html += f'    <div class="violation {cls}"><strong>[{v.rule_id}] {v.rule_name}</strong><br>{v.message}'
                if v.suggestion:
                    html += f'<br><em>建议: {v.suggestion}</em>'
                html += "</div>\n"
        
        html += """</body>
</html>"""
        return html
    
    def _make_bar(self, score: float, width: int = 40) -> str:
        """生成ASCII评分条"""
        filled = int(score / 100 * width)
        empty = width - filled
        return "[" + "█" * filled + "░" * empty + "]"


def save_report(result: EvaluationResult, filepath: str, format: str = "json"):
    """
    保存评估报告到文件
    
    Args:
        result: 评估结果
        filepath: 文件路径
        format: 格式 ("json", "markdown", "html", "text")
    """
    generator = ReportGenerator()
    content = generator.generate(result, format=format)
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    
    print(f"报告已保存: {filepath}")


def print_summary(result: EvaluationResult):
    """打印简洁摘要"""
    dim_summary = ", ".join([f"{d.dimension}:{d.score:.0f}" for d in result.dimension_scores])
    print(f"评估完成 | 综合:{result.overall_score:.1f} | 安全:{result.safety_score:.1f}({result.safety_level.value}) | 违规:{result.failed_rules}条")
