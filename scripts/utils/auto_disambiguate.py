#!/usr/bin/env python3
"""
自动实体消歧和合并
基于规则自动识别和合并相似实体
"""
import pandas as pd
import re
from difflib import SequenceMatcher
from collections import defaultdict

class AutoDisambiguator:
    def __init__(self):
        self.concepts_df = pd.read_csv('output/concepts_cleaned.csv')
        self.relationships_df = pd.read_csv('output/relationships_cleaned.csv')
        
        print("="*80)
        print("自动实体消歧和合并")
        print("="*80)
        print(f"\n加载数据:")
        print(f"  实体: {len(self.concepts_df)} 个")
        print(f"  关系: {len(self.relationships_df)} 个")
        
        self.merge_candidates = []
        self.merges_applied = {}
    
    def similarity(self, s1, s2):
        """计算字符串相似度"""
        return SequenceMatcher(None, s1.lower(), s2.lower()).ratio()
    
    def find_merge_candidates(self):
        """查找需要合并的候选实体"""
        print("\n查找合并候选...")
        
        entities = self.concepts_df['entity'].tolist()
        categories = self.concepts_df['category'].tolist()
        
        # 1. 查找完全包含关系的实体
        print("\n  检查包含关系...")
        for i, (e1, c1) in enumerate(zip(entities, categories)):
            for j, (e2, c2) in enumerate(zip(entities, categories)):
                if i >= j:
                    continue
                
                e1_lower = str(e1).lower()
                e2_lower = str(e2).lower()
                
                # 如果一个实体完全包含另一个（且类别相同或相近）
                if e1_lower in e2_lower and len(e1) >= 3:
                    if c1 == c2 or c1 == '其他' or c2 == '其他':
                        self.merge_candidates.append({
                            'entity1': e1,
                            'entity2': e2,
                            'reason': f'包含关系: "{e1}" in "{e2}"',
                            'keep': e2 if len(e2) > len(e1) else e1,  # 保留较长的
                            'category': c1 if c1 != '其他' else c2,
                            'confidence': 0.9
                        })
                elif e2_lower in e1_lower and len(e2) >= 3:
                    if c1 == c2 or c1 == '其他' or c2 == '其他':
                        self.merge_candidates.append({
                            'entity1': e1,
                            'entity2': e2,
                            'reason': f'包含关系: "{e2}" in "{e1}"',
                            'keep': e1 if len(e1) > len(e2) else e2,
                            'category': c1 if c1 != '其他' else c2,
                            'confidence': 0.9
                        })
        
        # 2. 查找高度相似的实体
        print("  检查相似度...")
        for i, (e1, c1) in enumerate(zip(entities, categories)):
            for j, (e2, c2) in enumerate(zip(entities, categories)):
                if i >= j:
                    continue
                
                sim = self.similarity(e1, e2)
                
                # 相似度>0.85且类别相同
                if sim > 0.85 and c1 == c2:
                    self.merge_candidates.append({
                        'entity1': e1,
                        'entity2': e2,
                        'reason': f'高度相似 (相似度: {sim:.2f})',
                        'keep': e1 if len(e1) >= len(e2) else e2,
                        'category': c1,
                        'confidence': sim
                    })
        
        # 3. 查找同义词（基于预定义规则）
        print("  检查同义词...")
        synonym_rules = {
            'pine wilt disease': ['pwd', '松材线虫病', '松材线虫病害'],
            'bursaphelenchus xylophilus': ['松材线虫', 'pwn'],
            'monochamus alternatus': ['松褐天牛', '墨天牛'],
            'pinus massoniana': ['马尾松'],
            'pinus thunbergii': ['黑松'],
        }
        
        entity_lower_map = {e.lower(): e for e in entities}
        
        for canonical, synonyms in synonym_rules.items():
            canonical_entity = entity_lower_map.get(canonical)
            
            for syn in synonyms:
                syn_entity = entity_lower_map.get(syn.lower())
                
                if canonical_entity and syn_entity and canonical_entity != syn_entity:
                    # 获取类别
                    cat1 = self.concepts_df[self.concepts_df['entity'] == canonical_entity]['category'].iloc[0]
                    cat2 = self.concepts_df[self.concepts_df['entity'] == syn_entity]['category'].iloc[0]
                    
                    self.merge_candidates.append({
                        'entity1': canonical_entity,
                        'entity2': syn_entity,
                        'reason': f'已知同义词',
                        'keep': canonical_entity,  # 保留规范名称
                        'category': cat1 if cat1 != '其他' else cat2,
                        'confidence': 1.0
                    })
        
        print(f"\n  发现 {len(self.merge_candidates)} 个合并候选")
        
        return self.merge_candidates
    
    def review_candidates(self):
        """审查合并候选"""
        if not self.merge_candidates:
            print("\n没有合并候选")
            return
        
        print("\n" + "="*80)
        print("审查合并候选")
        print("="*80)
        
        # 按置信度排序
        self.merge_candidates.sort(key=lambda x: x['confidence'], reverse=True)
        
        approved = []
        
        for i, candidate in enumerate(self.merge_candidates, 1):
            print(f"\n{i}/{len(self.merge_candidates)}")
            print(f"  实体1: {candidate['entity1']}")
            print(f"  实体2: {candidate['entity2']}")
            print(f"  原因: {candidate['reason']}")
            print(f"  建议保留: {candidate['keep']}")
            print(f"  类别: {candidate['category']}")
            print(f"  置信度: {candidate['confidence']:.2f}")
            
            # 显示关系数
            e1_rels = len(self.relationships_df[
                (self.relationships_df['node_1'] == candidate['entity1']) |
                (self.relationships_df['node_2'] == candidate['entity1'])
            ])
            e2_rels = len(self.relationships_df[
                (self.relationships_df['node_1'] == candidate['entity2']) |
                (self.relationships_df['node_2'] == candidate['entity2'])
            ])
            print(f"  关系数: {candidate['entity1']}({e1_rels}), {candidate['entity2']}({e2_rels})")
            
            # 高置信度自动批准
            if candidate['confidence'] >= 0.95:
                print("  自动批准（高置信度）")
                approved.append(candidate)
            else:
                print("\n  操作: [y]合并 [n]跳过 [c]修改保留项 [q]退出审查")
                action = input("  选择: ").strip().lower()
                
                if action == 'q':
                    break
                elif action == 'y':
                    approved.append(candidate)
                    print("  已批准")
                elif action == 'c':
                    keep_choice = input(f"  保留哪个? (1={candidate['entity1']}, 2={candidate['entity2']}): ").strip()
                    if keep_choice == '1':
                        candidate['keep'] = candidate['entity1']
                    elif keep_choice == '2':
                        candidate['keep'] = candidate['entity2']
                    approved.append(candidate)
                    print(f"  已批准，保留: {candidate['keep']}")
                else:
                    print("  已跳过")
        
        return approved
    
    def apply_merges(self, approved_merges):
        """应用合并"""
        if not approved_merges:
            print("\n没有需要应用的合并")
            return
        
        print("\n" + "="*80)
        print(f"应用 {len(approved_merges)} 个合并")
        print("="*80)
        
        for merge in approved_merges:
            e1 = merge['entity1']
            e2 = merge['entity2']
            keep = merge['keep']
            remove = e1 if keep == e2 else e2
            
            print(f"\n  合并: {remove} -> {keep}")
            
            # 更新关系
            self.relationships_df.loc[self.relationships_df['node_1'] == remove, 'node_1'] = keep
            self.relationships_df.loc[self.relationships_df['node_2'] == remove, 'node_2'] = keep
            
            # 删除被合并的实体
            self.concepts_df = self.concepts_df[self.concepts_df['entity'] != remove]
            
            # 记录合并
            self.merges_applied[remove] = keep
        
        # 合并后去重关系
        print("\n  去重关系...")
        before_dedup = len(self.relationships_df)
        self.relationships_df = self.relationships_df.groupby(
            ['node_1', 'node_2', 'edge'], as_index=False
        ).agg({
            'weight': 'max',
            'source': lambda x: ','.join(sorted(set(','.join(x).split(',')))),
            'chunk_id': 'first'
        })
        after_dedup = len(self.relationships_df)
        print(f"  去重: {before_dedup} -> {after_dedup} (移除 {before_dedup - after_dedup} 个)")
    
    def save_results(self):
        """保存结果"""
        print("\n保存结果...")
        
        self.concepts_df.to_csv('output/concepts_disambiguated.csv', index=False, encoding='utf-8-sig')
        self.relationships_df.to_csv('output/relationships_disambiguated.csv', index=False, encoding='utf-8-sig')
        
        print(f"  已保存: output/concepts_disambiguated.csv ({len(self.concepts_df)} 个实体)")
        print(f"  已保存: output/relationships_disambiguated.csv ({len(self.relationships_df)} 个关系)")
        
        # 保存合并记录
        import json
        with open('output/entity_merges.json', 'w', encoding='utf-8') as f:
            json.dump(self.merges_applied, f, ensure_ascii=False, indent=2)
        
        print(f"  合并记录: output/entity_merges.json")
    
    def run(self, auto_mode=False):
        """运行消歧流程"""
        # 1. 查找候选
        self.find_merge_candidates()
        
        if not self.merge_candidates:
            print("\n未发现需要合并的实体")
            return
        
        # 2. 审查候选
        if auto_mode:
            # 自动模式：只批准高置信度的
            approved = [c for c in self.merge_candidates if c['confidence'] >= 0.95]
            print(f"\n自动模式: 批准 {len(approved)}/{len(self.merge_candidates)} 个高置信度合并")
        else:
            approved = self.review_candidates()
        
        if not approved:
            print("\n没有批准的合并")
            return
        
        # 3. 应用合并
        self.apply_merges(approved)
        
        # 4. 保存结果
        self.save_results()
        
        print("\n" + "="*80)
        print("消歧完成。")
        print("="*80)
        print(f"\n统计:")
        print(f"  合并候选: {len(self.merge_candidates)}")
        print(f"  已批准: {len(approved)}")
        print(f"  最终实体数: {len(self.concepts_df)}")
        print(f"  最终关系数: {len(self.relationships_df)}")

if __name__ == "__main__":
    import sys
    
    disambiguator = AutoDisambiguator()
    
    # 检查是否使用自动模式
    auto_mode = '--auto' in sys.argv
    
    if auto_mode:
        print("\n[自动模式] 只批准高置信度合并")
    
    disambiguator.run(auto_mode=auto_mode)
