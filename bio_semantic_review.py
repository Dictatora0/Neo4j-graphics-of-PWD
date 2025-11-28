#!/usr/bin/env python3
"""
基于生物学规则的三元组语义体检脚本

输入:
  output/triples_export.csv

输出:
  1) output/triples_export_semantic_clean.csv        # 语义清洗后的三元组(用于重新导入)
  2) output/triples_semantic_issues.csv             # 检查到的语义问题及修正建议

核心功能:
  - 按名称规则为节点打标签(Host, Pathogen, Vector, Disease, Symptom, ControlMeasure, Region, EnvironmentalFactor, Technology, Other)
  - 基于(关系类型, 起点标签, 终点标签)的白名单检查语义合理性
  - 对少量典型关系进行自动方向纠正(例如 Host->Pathogen 的 INFECTS 反转为 Pathogen->Host)

注意:
  - 本脚本尽量保守: 只在非常确定的情况下自动纠正方向, 其他问题仅记录在 issues 文件中供人工审查
  - 不修改原始 triples_export.csv, 只生成新的 clean 版本
"""

import os
import pandas as pd
from typing import Dict, List, Tuple


TRIPLES_PATH = "output/triples_export.csv"
OUTPUT_CLEAN_PATH = "output/triples_export_semantic_clean.csv"
OUTPUT_ISSUES_PATH = "output/triples_semantic_issues.csv"


def infer_node_type(name: str) -> str:
    """根据名称启发式推断节点类型(label)。尽量与业务知识保持一致。"""
    n = (name or "").lower()

    # 明确的关键字优先
    if any(x in n for x in ["bursaphelenchus", "nematode", "bacteria"]):
        return "Pathogen"
    if "pine wilt" in n or "松材线虫病" in n:
        return "Disease"

    # 特殊精确匹配
    if n.strip() == "leaf":
        return "Symptom"

    # 树种 / 森林类型 / 寄主群落
    if any(x in n for x in ["pinus", "pine", "spruce", "forest", "tree"]):
        return "Host"

    # 媒介昆虫
    if any(x in n for x in ["monochamus", "arhopalus", "longhorn beetle", "beetle", "天牛"]):
        return "Vector"

    # 防治措施
    if any(x in n for x in ["control", "防治", "trap", "bait", "sanitation felling", "清理", "化学防治"]):
        return "ControlMeasure"

    # 症状
    if any(x in n for x in ["symptom", "症状", "wilt", "wilting", "discoloration", "枯萎", "变色"]):
        return "Symptom"

    # 地点 / 区域
    if any(x in n for x in ["province", "city", "county", "area", "region", "mount", "peak", "temple", "寺", "景区", "门", " valley", "峪"]):
        return "Region"

    # 环境因子
    if any(x in n for x in [
        "temperature",
        "humidity",
        "climate",
        "meteorological",
        "cold",
        "stress",
        "气象",
        "environment",
        "环境",
        "altitude",
        "高海拔",
        "低海拔",
    ]):
        return "EnvironmentalFactor"

    # 技术/方法
    if any(x in n for x in [
        "spectral",
        "spectrum",
        "hyperspectral",
        "sentinel",
        "algorithm",
        "band",
        "imaging",
        "uav",
        "analysis",
        "detection",
        "scale",
        "光谱",
        "波段",
    ]):
        return "Technology"

    return "Other"


def build_relation_schema() -> Dict[str, List[Tuple[str, str]]]:
    """定义每种关系允许的(起点类型, 终点类型)组合白名单。"""
    schema: Dict[str, List[Tuple[str, str]]] = {
        # 典型致病/寄生/感染关系
        "INFECTS": [("Pathogen", "Host")],
        "PARASITIZES": [("Pathogen", "Host"), ("Pathogen", "Vector")],
        "CAUSES": [("Pathogen", "Disease")],

        # 传播/携带
        "TRANSMITS": [("Vector", "Pathogen"), ("Vector", "Disease")],
        "CARRIES": [("Vector", "Pathogen"), ("Vector", "Disease")],
        "FEEDS_ON": [("Vector", "Host")],

        # 防治/治疗
        "CONTROLS": [
            ("ControlMeasure", "Disease"),
            ("ControlMeasure", "Pathogen"),
            ("ControlMeasure", "Vector"),
        ],
        "TREATS": [
            ("ControlMeasure", "Disease"),
            ("ControlMeasure", "Pathogen"),
        ],
        "PREVENTS": [
            ("ControlMeasure", "Disease"),
            ("ControlMeasure", "Pathogen"),
        ],
        "SOLVES": [
            ("ControlMeasure", "Disease"),
            ("ControlMeasure", "Pathogen"),
            ("ControlMeasure", "Vector"),
        ],

        # 分布/发生
        "DISTRIBUTED_IN": [
            ("Disease", "Region"),
            ("Host", "Region"),
            ("Vector", "Region"),
        ],
        "OCCURS_IN": [("Disease", "Region")],
        "LOCATED_IN": [
            ("Host", "Region"),
            ("Vector", "Region"),
        ],

        # 监测/应用
        "MONITORS": [
            ("Technology", "Disease"),
            ("Technology", "Host"),
            ("Technology", "Vector"),
        ],
        "APPLIES_TO": [
            ("Technology", "Disease"),
            ("Technology", "Host"),
            ("Technology", "Pathogen"),
        ],

        # 影响关系
        "AFFECTS": [
            ("EnvironmentalFactor", "Disease"),
            ("EnvironmentalFactor", "Pathogen"),
            ("EnvironmentalFactor", "Vector"),
            ("EnvironmentalFactor", "Host"),
            ("Pathogen", "Host"),
            ("Disease", "Host"),
            ("Disease", "Symptom"),
        ],
        "AFFECTED_BY": [
            ("Disease", "EnvironmentalFactor"),
            ("Pathogen", "EnvironmentalFactor"),
            ("Vector", "EnvironmentalFactor"),
        ],

        # 环境因子关系(较少使用, 主要用于标记错误)
        "ENVIRONMENTAL_FACTOR": [
            ("EnvironmentalFactor", "Disease"),
            ("EnvironmentalFactor", "Pathogen"),
            ("EnvironmentalFactor", "Vector"),
            ("EnvironmentalFactor", "Host"),
        ],

        # 症状
        "SYMPTOM_OF": [("Symptom", "Disease"), ("Symptom", "Pathogen")],
        "hasSymptom": [("Disease", "Symptom")],

        # 共现/相关: 放宽约束
        "CO_OCCURS_WITH": [],
        "RELATED_TO": [],
        "COMPARES_WITH": [],
    }

    return schema


def is_allowed(schema: Dict[str, List[Tuple[str, str]]], rel: str, s_type: str, t_type: str) -> bool:
    """检查(关系, 起点类型, 终点类型)是否在白名单中。如果该关系没有配置限制, 返回 True(宽松处理)。"""
    allowed = schema.get(rel)
    if allowed is None:
        # 未知关系, 不做强约束
        return True
    if not allowed:
        # 显式允许任意组合(如 CO_OCCURS_WITH)
        return True
    return (s_type, t_type) in allowed


def maybe_reverse(schema: Dict[str, List[Tuple[str, str]]], rel: str, s_type: str, t_type: str) -> bool:
    """判断是否应该自动反转方向, 只在非常明确的几种关系上尝试。"""
    # 只对这些关系做反转尝试
    reversible = {
        "INFECTS",
        "PARASITIZES",
        "CAUSES",
        "AFFECTS",
        "AFFECTED_BY",
        "CONTROLS",
        "TREATS",
        "PREVENTS",
        "DISTRIBUTED_IN",
        "LOCATED_IN",
        "MONITORS",
        "APPLIES_TO",
        "SYMPTOM_OF",
    }
    if rel not in reversible:
        return False

    allowed = schema.get(rel) or []
    # 如果当前方向不在白名单, 但反向在白名单, 则认为可以反转
    if (s_type, t_type) in allowed:
        return False
    if (t_type, s_type) in allowed:
        return True
    return False


def main() -> None:
    if not os.path.exists(TRIPLES_PATH):
        print(f"[错误] 找不到输入文件: {TRIPLES_PATH}")
        return

    df = pd.read_csv(TRIPLES_PATH)
    required_cols = {"node_1", "relationship", "node_2", "weight"}
    if not required_cols.issubset(df.columns):
        print(f"[错误] triples_export.csv 缺少必要列: {required_cols - set(df.columns)}")
        return

    print("=" * 80)
    print("语义体检: 读取三元组")
    print("=" * 80)
    print(f"  总三元组数: {len(df)}")

    schema = build_relation_schema()

    # 预推断所有节点类型
    print("\n推断节点类型(label)...")
    nodes = sorted(set(df["node_1"].astype(str)) | set(df["node_2"].astype(str)))
    node_type_map: Dict[str, str] = {n: infer_node_type(n) for n in nodes}

    # 统计节点类型分布
    type_counts: Dict[str, int] = {}
    for t in node_type_map.values():
        type_counts[t] = type_counts.get(t, 0) + 1
    print("  节点类型分布:")
    for t, c in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"    {t:20s}: {c}")

    # 逐条检查
    print("\n开始检查三元组语义...")
    issues = []
    fixed_rows = []

    for idx, row in df.iterrows():
        s = str(row["node_1"])
        t = str(row["node_2"])
        rel = str(row["relationship"])
        w = row["weight"]

        s_type = node_type_map.get(s, "Other")
        t_type = node_type_map.get(t, "Other")

        allowed = is_allowed(schema, rel, s_type, t_type)
        reversed_flag = False
        note = ""

        if not allowed:
            # 尝试反转
            if maybe_reverse(schema, rel, s_type, t_type):
                reversed_flag = True
                s, t = t, s
                s_type, t_type = t_type, s_type
                note = "auto_reverse"
            else:
                note = "type_mismatch"

            issues.append({
                "node_1": row["node_1"],
                "node_1_type": node_type_map.get(str(row["node_1"]), "Other"),
                "relationship": rel,
                "node_2": row["node_2"],
                "node_2_type": node_type_map.get(str(row["node_2"]), "Other"),
                "weight": w,
                "action": note,
                "new_node_1": s,
                "new_node_1_type": s_type,
                "new_node_2": t,
                "new_node_2_type": t_type,
            })

        fixed_rows.append({
            "node_1": s,
            "relationship": rel,
            "node_2": t,
            "weight": w,
        })

    clean_df = pd.DataFrame(fixed_rows)
    os.makedirs(os.path.dirname(OUTPUT_CLEAN_PATH), exist_ok=True)
    clean_df.to_csv(OUTPUT_CLEAN_PATH, index=False)
    print(f"\n已生成语义清洗后的三元组文件: {OUTPUT_CLEAN_PATH} (共 {len(clean_df)} 条)")

    if issues:
        issues_df = pd.DataFrame(issues)
        issues_df.to_csv(OUTPUT_ISSUES_PATH, index=False)
        print(f"检测到 {len(issues)} 条存在语义问题的三元组, 已输出到: {OUTPUT_ISSUES_PATH}")
    else:
        print("未发现语义问题三元组 (在当前规则下)")

    print("\n完成语义体检。你可以:")
    print("  1. 查看 output/triples_semantic_issues.csv 了解具体问题")
    print("  2. 使用 import_to_neo4j_final.py 重新导入, 它将优先使用 semantic_clean 版本")


if __name__ == "__main__":
    main()
