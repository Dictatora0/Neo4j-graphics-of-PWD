#!/usr/bin/env python3
"""
修复已识别的语义问题三元组
直接修改 output/triples_export_semantic_clean.csv
"""

import pandas as pd
import os

CSV_PATH = "output/triples_export_semantic_clean.csv"

print("=" * 80)
print("修复语义问题三元组")
print("=" * 80)

if not os.path.exists(CSV_PATH):
    print(f"[错误] 找不到文件: {CSV_PATH}")
    exit(1)

# 读取 CSV
df = pd.read_csv(CSV_PATH)
print(f"\n原始三元组数: {len(df)}")

# 定义修复规则: (原始行条件, 新的行内容)
# 格式: ((node_1, relationship, node_2), (new_node_1, new_relationship, new_node_2))
fixes = [
    # 1. 疾病/病原体 与 地点/海拔
    (("dexing city", "AFFECTS", "pine wilt disease"), 
     ("pine wilt disease", "DISTRIBUTED_IN", "dexing city")),
    
    (("mount tai scenic area", "INFECTS", "pine wilt disease"), 
     ("pine wilt disease", "DISTRIBUTED_IN", "mount tai scenic area")),
    
    (("mount tai scenic area", "DISTRIBUTED_IN", "high altitude area"), 
     ("mount tai scenic area", "LOCATED_IN", "high altitude area")),
    
    # 2. 疾病/病原体 与 环境因子
    (("pine wilt disease", "CAUSES", "cold stress"), 
     ("pine wilt disease", "RELATED_TO", "cold stress")),
    
    (("pine wood nematode associated bacteria", "CAUSES", "bursaphelenchus xylophilus"), 
     ("pine wood nematode associated bacteria", "RELATED_TO", "bursaphelenchus xylophilus")),
    
    # 3. 症状/叶片 与 地点/区域
    # leaf,AFFECTS,mount tai scenic area → 删除
    
    # pinus massoniana,COMPONENT_OF,leaf → leaf,COMPONENT_OF,pinus massoniana
    (("pinus massoniana", "COMPONENT_OF", "leaf"), 
     ("leaf", "COMPONENT_OF", "pinus massoniana")),
    
    # 4. 防治措施/监测手段 与 地点
    # trap,AFFECTS,mount tai scenic area → 删除
    # trap,ENVIRONMENTAL_FACTOR,leaf → 删除
    # sentinel-2,AFFECTS,pine wilt disease → 删除
    
    # 5. 方向没问题但语义弱/可选调整
    (("control", "SOLVES", "pine wilt disease"), 
     ("control", "TREATS", "pine wilt disease")),
    
    (("leaf", "COOPERATES_WITH", "biological control"), 
     ("leaf", "CO_OCCURS_WITH", "biological control")),
    
    (("leaf", "COOPERATES_WITH", "trap"), 
     ("leaf", "CO_OCCURS_WITH", "trap")),
]

# 应用修复规则
fixed_count = 0
for (old_n1, old_rel, old_n2), (new_n1, new_rel, new_n2) in fixes:
    mask = (df["node_1"] == old_n1) & (df["relationship"] == old_rel) & (df["node_2"] == old_n2)
    if mask.any():
        df.loc[mask, "node_1"] = new_n1
        df.loc[mask, "relationship"] = new_rel
        df.loc[mask, "node_2"] = new_n2
        fixed_count += 1
        print(f"修复: {old_n1} -{old_rel}-> {old_n2}")
        print(f"  改为: {new_n1} -{new_rel}-> {new_n2}")

# 删除明显有问题的行
delete_conditions = [
    (("leaf", "AFFECTS", "mount tai scenic area"), "叶片影响景区（无意义）"),
    (("trap", "AFFECTS", "mount tai scenic area"), "诱捕器影响景区（无意义）"),
    (("trap", "ENVIRONMENTAL_FACTOR", "leaf"), "诱捕器是环境因子（错误关系名）"),
    (("sentinel-2", "AFFECTS", "pine wilt disease"), "Sentinel-2影响疾病（应为MONITORS）"),
]

deleted_count = 0
for (n1, rel, n2), reason in delete_conditions:
    mask = (df["node_1"] == n1) & (df["relationship"] == rel) & (df["node_2"] == n2)
    if mask.any():
        df = df[~mask]
        deleted_count += 1
        print(f"删除: {n1} -{rel}-> {n2}")
        print(f"  原因: {reason}")

# 保存修改后的 CSV
df.to_csv(CSV_PATH, index=False)
print(f"\n修复完成:")
print(f"  修改行数: {fixed_count}")
print(f"  删除行数: {deleted_count}")
print(f"  最终三元组数: {len(df)}")
print(f"\n已保存到: {CSV_PATH}")
