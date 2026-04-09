# health-coach

Prescription Evaluation Engine + MCP Data Pipeline for R+ Health SLM Training

## Quick Start

`ash
pip install -r requirements.txt
python -m evaluator.test_evaluator
python -m evaluator quick
python -m pipeline.pipeline -n 50
`

## Evaluation Dimensions

| Dimension | Weight | Description |
|-----------|--------|-------------|
| Safety | 30% | Contraindications, risk factors |
| Adaptability | 25% | Match age/BMI/conditions |
| Scientific | 20% | Clinical guidelines compliance |
| Completeness | 15% | Information completeness |
| Executability | 10% | User can execute |

## Three-Layer Architecture

1. **Layer 1: Rule Engine** - Millisecond hard violation blocking
2. **Layer 2: LLM Judge** - Deep 5-dimension evaluation  
3. **Layer 3: Human Review** - Expert annotation for ground truth