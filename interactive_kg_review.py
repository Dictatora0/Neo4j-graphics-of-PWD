#!/usr/bin/env python3
"""
交互式知识图谱审查和修正工具
支持实体和关系的检查、修正、合并、消歧
"""
import pandas as pd
import json
from collections import defaultdict
import re

class KGReviewer:
    def __init__(self):
        self.concepts_df = pd.read_csv('output/concepts_cleaned.csv')
        self.relationships_df = pd.read_csv('output/relationships_cleaned.csv')
        
        # 记录修改
        self.entity_merges = {}  # 旧名 -> 新名
        self.entity_corrections = {}  # 旧名 -> 新名
        self.entity_deletions = set()
        self.relation_corrections = []
        
        print("="*80)
        print("知识图谱交互式审查工具")
        print("="*80)
        print(f"\n加载数据:")
        print(f"  实体: {len(self.concepts_df)} 个")
        print(f"  关系: {len(self.relationships_df)} 个")
    
    def find_similar_entities(self, entity, threshold=0.7):
        """查找相似实体（用于消歧）"""
        similar = []
        entity_lower = str(entity).lower()
        
        for idx, row in self.concepts_df.iterrows():
            other = str(row['entity'])
            other_lower = other.lower()
            
            if entity == other:
                continue
            
            # 简单相似度：包含关系
            if entity_lower in other_lower or other_lower in entity_lower:
                similar.append({
                    'entity': other,
                    'category': row['category'],
                    'importance': row['importance']
                })
            # 检查是否有共同词
            elif len(set(entity_lower) & set(other_lower)) / max(len(entity_lower), len(other_lower)) > threshold:
                similar.append({
                    'entity': other,
                    'category': row['category'],
                    'importance': row['importance']
                })
        
        return similar[:5]  # 最多返回5个
    
    def review_entities_by_category(self):
        """按类别审查实体"""
        print("\n" + "="*80)
        print("实体审查（按类别）")
        print("="*80)
        
        categories = self.concepts_df['category'].value_counts()
        
        print("\n可用类别:")
        for i, (cat, count) in enumerate(categories.items(), 1):
            print(f"  {i}. {cat:15s} ({count} 个)")
        
        choice = input("\n选择要审查的类别编号（回车跳过）: ").strip()
        if not choice:
            return
        
        try:
            cat_idx = int(choice) - 1
            selected_cat = list(categories.keys())[cat_idx]
        except:
            print("无效选择")
            return
        
        # 审查该类别的实体
        entities = self.concepts_df[self.concepts_df['category'] == selected_cat]
        print(f"\n审查类别: {selected_cat} ({len(entities)} 个实体)")
        print("-"*80)
        
        for idx, row in entities.iterrows():
            entity = row['entity']
            importance = row['importance']
            
            print(f"\n实体: {entity}")
            print(f"  重要性: {importance}")
            print(f"  类别: {selected_cat}")
            
            # 显示相关关系
            rel_count = len(self.relationships_df[
                (self.relationships_df['node_1'] == entity) | 
                (self.relationships_df['node_2'] == entity)
            ])
            print(f"  关系数: {rel_count}")
            
            # 查找相似实体
            similar = self.find_similar_entities(entity)
            if similar:
                print(f"  相似实体:")
                for i, sim in enumerate(similar, 1):
                    print(f"    {i}. {sim['entity']} ({sim['category']})")
            
            print("\n操作:")
            print("  [Enter] 保持不变")
            print("  [r] 重命名")
            print("  [m] 合并到其他实体")
            print("  [c] 修改类别")
            print("  [d] 删除")
            print("  [q] 退出审查")
            
            action = input("选择操作: ").strip().lower()
            
            if action == 'q':
                break
            elif action == 'r':
                new_name = input(f"  新名称（当前: {entity}）: ").strip()
                if new_name and new_name != entity:
                    self.entity_corrections[entity] = new_name
                    print(f"  ✓ 将重命名为: {new_name}")
            elif action == 'm':
                if similar:
                    merge_choice = input(f"  合并到哪个实体？(1-{len(similar)}): ").strip()
                    try:
                        merge_idx = int(merge_choice) - 1
                        target = similar[merge_idx]['entity']
                        self.entity_merges[entity] = target
                        print(f"  ✓ 将合并到: {target}")
                    except:
                        print("  无效选择")
                else:
                    target = input(f"  合并到（输入目标实体名）: ").strip()
                    if target:
                        self.entity_merges[entity] = target
                        print(f"  ✓ 将合并到: {target}")
            elif action == 'c':
                print("  可用类别:", ', '.join(categories.keys()))
                new_cat = input(f"  新类别（当前: {selected_cat}）: ").strip()
                if new_cat:
                    self.concepts_df.loc[idx, 'category'] = new_cat
                    print(f"  ✓ 类别已更改为: {new_cat}")
            elif action == 'd':
                confirm = input(f"  确认删除 '{entity}'? (y/n): ").strip().lower()
                if confirm == 'y':
                    self.entity_deletions.add(entity)
                    print(f"  ✓ 已标记删除")
    
    def review_suspicious_entities(self):
        """审查可疑实体"""
        print("\n" + "="*80)
        print("可疑实体审查")
        print("="*80)
        
        suspicious = []
        
        # 1. 过短的实体
        short_entities = self.concepts_df[self.concepts_df['entity'].str.len() <= 3]
        for idx, row in short_entities.iterrows():
            suspicious.append({
                'entity': row['entity'],
                'reason': '名称过短',
                'category': row['category'],
                'importance': row['importance']
            })
        
        # 2. 包含特殊字符的实体
        special_char_entities = self.concepts_df[
            self.concepts_df['entity'].str.contains(r'[^\w\s\-\u4e00-\u9fff]', regex=True, na=False)
        ]
        for idx, row in special_char_entities.iterrows():
            suspicious.append({
                'entity': row['entity'],
                'reason': '包含特殊字符',
                'category': row['category'],
                'importance': row['importance']
            })
        
        # 3. 重要性很低的实体
        low_importance = self.concepts_df[self.concepts_df['importance'] <= 2]
        for idx, row in low_importance.head(20).iterrows():
            suspicious.append({
                'entity': row['entity'],
                'reason': '重要性低',
                'category': row['category'],
                'importance': row['importance']
            })
        
        if not suspicious:
            print("\n✓ 未发现可疑实体")
            return
        
        print(f"\n发现 {len(suspicious)} 个可疑实体")
        print("-"*80)
        
        for i, item in enumerate(suspicious[:30], 1):  # 最多显示30个
            print(f"\n{i}. {item['entity']}")
            print(f"   原因: {item['reason']}")
            print(f"   类别: {item['category']}, 重要性: {item['importance']}")
            
            # 显示关系数
            entity = item['entity']
            rel_count = len(self.relationships_df[
                (self.relationships_df['node_1'] == entity) | 
                (self.relationships_df['node_2'] == entity)
            ])
            print(f"   关系数: {rel_count}")
            
            print("\n   操作: [Enter]保持 [r]重命名 [d]删除 [q]退出")
            action = input("   选择: ").strip().lower()
            
            if action == 'q':
                break
            elif action == 'r':
                new_name = input(f"   新名称: ").strip()
                if new_name:
                    self.entity_corrections[entity] = new_name
                    print(f"   ✓ 将重命名为: {new_name}")
            elif action == 'd':
                self.entity_deletions.add(entity)
                print(f"   ✓ 已标记删除")
    
    def review_relations(self):
        """审查关系"""
        print("\n" + "="*80)
        print("关系审查")
        print("="*80)
        
        # 按关系类型分组
        edge_types = self.relationships_df['edge'].value_counts()
        
        print("\n关系类型分布:")
        for i, (edge, count) in enumerate(edge_types.head(15).items(), 1):
            print(f"  {i}. {edge:30s} ({count} 个)")
        
        print("\n审查选项:")
        print("  1. 审查特定关系类型")
        print("  2. 审查高权重关系")
        print("  3. 审查低权重关系")
        print("  4. 查找重复关系")
        
        choice = input("\n选择 (1-4, 回车跳过): ").strip()
        
        if choice == '1':
            self._review_by_relation_type(edge_types)
        elif choice == '2':
            self._review_high_weight_relations()
        elif choice == '3':
            self._review_low_weight_relations()
        elif choice == '4':
            self._find_duplicate_relations()
    
    def _review_by_relation_type(self, edge_types):
        """按关系类型审查"""
        type_choice = input("输入关系类型编号: ").strip()
        try:
            type_idx = int(type_choice) - 1
            selected_type = list(edge_types.keys())[type_idx]
        except:
            print("无效选择")
            return
        
        relations = self.relationships_df[self.relationships_df['edge'] == selected_type]
        print(f"\n审查关系类型: {selected_type} ({len(relations)} 个)")
        print("-"*80)
        
        for idx, row in relations.head(20).iterrows():
            print(f"\n{row['node_1']} --[{row['edge']}]--> {row['node_2']}")
            print(f"  权重: {row['weight']:.3f}")
            print(f"  来源: {row['source']}")
            
            print("\n  操作: [Enter]保持 [t]修改类型 [d]删除 [q]退出")
            action = input("  选择: ").strip().lower()
            
            if action == 'q':
                break
            elif action == 't':
                new_type = input(f"  新关系类型: ").strip()
                if new_type:
                    self.relationships_df.loc[idx, 'edge'] = new_type
                    print(f"  ✓ 已修改为: {new_type}")
            elif action == 'd':
                self.relationships_df = self.relationships_df.drop(idx)
                print(f"  ✓ 已删除")
    
    def _review_high_weight_relations(self):
        """审查高权重关系"""
        high_weight = self.relationships_df.nlargest(20, 'weight')
        print(f"\n审查高权重关系（前20个）")
        print("-"*80)
        
        for idx, row in high_weight.iterrows():
            print(f"\n{row['node_1']} --[{row['edge']}]--> {row['node_2']}")
            print(f"  权重: {row['weight']:.3f}")
            print(f"  来源: {row['source']}")
            
            print("\n  操作: [Enter]保持 [q]退出")
            action = input("  选择: ").strip().lower()
            if action == 'q':
                break
    
    def _review_low_weight_relations(self):
        """审查低权重关系"""
        low_weight = self.relationships_df.nsmallest(30, 'weight')
        print(f"\n审查低权重关系（最低30个）")
        print("-"*80)
        
        for idx, row in low_weight.iterrows():
            print(f"\n{row['node_1']} --[{row['edge']}]--> {row['node_2']}")
            print(f"  权重: {row['weight']:.3f}")
            print(f"  来源: {row['source']}")
            
            print("\n  操作: [Enter]保持 [d]删除 [q]退出")
            action = input("  选择: ").strip().lower()
            
            if action == 'q':
                break
            elif action == 'd':
                self.relationships_df = self.relationships_df.drop(idx)
                print(f"  ✓ 已删除")
    
    def _find_duplicate_relations(self):
        """查找重复关系"""
        print(f"\n查找重复关系...")
        
        duplicates = self.relationships_df.groupby(['node_1', 'node_2']).filter(lambda x: len(x) > 1)
        
        if len(duplicates) == 0:
            print("✓ 未发现重复关系")
            return
        
        print(f"发现 {len(duplicates)} 个可能重复的关系")
        print("-"*80)
        
        for (n1, n2), group in duplicates.groupby(['node_1', 'node_2']):
            print(f"\n{n1} --> {n2}")
            for idx, row in group.iterrows():
                print(f"  [{row['edge']}] 权重:{row['weight']:.3f} 来源:{row['source']}")
            
            print("\n  操作: [Enter]保持全部 [k]保留最高权重 [q]退出")
            action = input("  选择: ").strip().lower()
            
            if action == 'q':
                break
            elif action == 'k':
                # 保留权重最高的
                keep_idx = group['weight'].idxmax()
                drop_indices = group.index[group.index != keep_idx]
                self.relationships_df = self.relationships_df.drop(drop_indices)
                print(f"  ✓ 已保留权重最高的关系，删除 {len(drop_indices)} 个")
    
    def apply_changes(self):
        """应用所有修改"""
        print("\n" + "="*80)
        print("应用修改")
        print("="*80)
        
        # 1. 应用实体合并
        if self.entity_merges:
            print(f"\n合并实体: {len(self.entity_merges)} 个")
            for old, new in self.entity_merges.items():
                print(f"  {old} -> {new}")
                # 更新关系中的实体名
                self.relationships_df.loc[self.relationships_df['node_1'] == old, 'node_1'] = new
                self.relationships_df.loc[self.relationships_df['node_2'] == old, 'node_2'] = new
                # 从概念表中删除旧实体
                self.concepts_df = self.concepts_df[self.concepts_df['entity'] != old]
        
        # 2. 应用实体重命名
        if self.entity_corrections:
            print(f"\n重命名实体: {len(self.entity_corrections)} 个")
            for old, new in self.entity_corrections.items():
                print(f"  {old} -> {new}")
                self.concepts_df.loc[self.concepts_df['entity'] == old, 'entity'] = new
                self.relationships_df.loc[self.relationships_df['node_1'] == old, 'node_1'] = new
                self.relationships_df.loc[self.relationships_df['node_2'] == old, 'node_2'] = new
        
        # 3. 删除实体
        if self.entity_deletions:
            print(f"\n删除实体: {len(self.entity_deletions)} 个")
            for entity in self.entity_deletions:
                print(f"  {entity}")
                self.concepts_df = self.concepts_df[self.concepts_df['entity'] != entity]
                self.relationships_df = self.relationships_df[
                    (self.relationships_df['node_1'] != entity) &
                    (self.relationships_df['node_2'] != entity)
                ]
        
        # 4. 保存修改
        print(f"\n💾 保存修改后的数据...")
        self.concepts_df.to_csv('output/concepts_reviewed.csv', index=False, encoding='utf-8-sig')
        self.relationships_df.to_csv('output/relationships_reviewed.csv', index=False, encoding='utf-8-sig')
        
        print(f"  ✓ 已保存: output/concepts_reviewed.csv ({len(self.concepts_df)} 个实体)")
        print(f"  ✓ 已保存: output/relationships_reviewed.csv ({len(self.relationships_df)} 个关系)")
        
        # 保存修改日志
        changes_log = {
            'entity_merges': self.entity_merges,
            'entity_corrections': self.entity_corrections,
            'entity_deletions': list(self.entity_deletions),
            'total_entities_before': len(pd.read_csv('output/concepts_cleaned.csv')),
            'total_entities_after': len(self.concepts_df),
            'total_relations_before': len(pd.read_csv('output/relationships_cleaned.csv')),
            'total_relations_after': len(self.relationships_df)
        }
        
        with open('output/review_changes.json', 'w', encoding='utf-8') as f:
            json.dump(changes_log, f, ensure_ascii=False, indent=2)
        
        print(f"  ✓ 修改日志: output/review_changes.json")
    
    def run(self):
        """运行交互式审查"""
        while True:
            print("\n" + "="*80)
            print("主菜单")
            print("="*80)
            print("  1. 按类别审查实体")
            print("  2. 审查可疑实体")
            print("  3. 审查关系")
            print("  4. 应用修改并保存")
            print("  5. 退出（不保存）")
            
            choice = input("\n选择操作 (1-5): ").strip()
            
            if choice == '1':
                self.review_entities_by_category()
            elif choice == '2':
                self.review_suspicious_entities()
            elif choice == '3':
                self.review_relations()
            elif choice == '4':
                self.apply_changes()
                print("\n✓ 修改已保存！")
                break
            elif choice == '5':
                confirm = input("确认退出不保存? (y/n): ").strip().lower()
                if confirm == 'y':
                    print("已退出")
                    break
            else:
                print("无效选择")

if __name__ == "__main__":
    reviewer = KGReviewer()
    reviewer.run()
