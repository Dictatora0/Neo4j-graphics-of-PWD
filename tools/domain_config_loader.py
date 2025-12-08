#!/usr/bin/env python3
"""
领域配置加载工具
从外部 JSON 文件加载实体别名映射和类型层级
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
import sys

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class DomainConfigLoader:
    """领域配置加载器"""
    
    def __init__(
        self,
        domain_dict_path: Optional[str] = None,
        hierarchy_path: Optional[str] = None
    ):
        """
        初始化配置加载器
        
        Args:
            domain_dict_path: 实体别名配置文件路径
            hierarchy_path: 类型层级配置文件路径
        """
        # 默认路径
        if domain_dict_path is None:
            domain_dict_path = str(project_root / "config" / "domain_dict.json")
        if hierarchy_path is None:
            hierarchy_path = str(project_root / "config" / "type_hierarchy.json")
        
        self.domain_dict_path = Path(domain_dict_path)
        self.hierarchy_path = Path(hierarchy_path)
        
        self._domain_dict: Optional[Dict] = None
        self._hierarchy: Optional[Dict] = None
        self._canonical_mapping: Optional[Dict[str, str]] = None
        self._type_hierarchy: Optional[Dict[str, List[str]]] = None
    
    def load_domain_dict(self) -> Dict[str, List[str]]:
        """
        加载实体别名配置
        
        Returns:
            {category: [alias1, alias2, ...]}
        """
        if self._domain_dict is not None:
            return self._domain_dict
        
        with open(self.domain_dict_path, 'r', encoding='utf-8') as f:
            self._domain_dict = json.load(f)
        
        return self._domain_dict
    
    def load_hierarchy(self) -> Dict:
        """
        加载类型层级配置
        
        Returns:
            完整的层级配置字典
        """
        if self._hierarchy is not None:
            return self._hierarchy
        
        with open(self.hierarchy_path, 'r', encoding='utf-8') as f:
            self._hierarchy = json.load(f)
        
        return self._hierarchy
    
    def get_canonical_mapping(self) -> Dict[str, str]:
        """
        获取别名到标准名称的映射
        
        Returns:
            {alias: canonical_name}
            
        Example:
            {
                "pine wilt disease": "松材线虫病",
                "PWD": "松材线虫病",
                "B. xylophilus": "松材线虫",
                ...
            }
        """
        if self._canonical_mapping is not None:
            return self._canonical_mapping
        
        domain_dict = self.load_domain_dict()
        mapping = {}
        
        for category, aliases in domain_dict.items():
            if not aliases:
                continue
            
            # 第一个别名作为标准名称
            canonical = aliases[0]
            
            # 所有别名（包括标准名称本身）都映射到标准名称
            for alias in aliases:
                # 原始形式
                mapping[alias] = canonical
                # 小写形式
                mapping[alias.lower()] = canonical
                # 去空格形式
                mapping[alias.strip()] = canonical
        
        self._canonical_mapping = mapping
        return mapping
    
    def get_type_hierarchy_map(self) -> Dict[str, List[str]]:
        """
        获取类型到其所有父类的映射（用于 Neo4j 多级 Label）
        
        Returns:
            {type_name: [parent1, parent2, ..., type_name]}
            
        Example:
            {
                "Nematode": ["Organism", "Pathogen", "Nematode"],
                "Pine": ["Organism", "Host", "Pine"],
                ...
            }
        """
        if self._type_hierarchy is not None:
            return self._type_hierarchy
        
        hierarchy = self.load_hierarchy()
        type_map = {}
        
        def traverse(node: Dict, ancestors: List[str]):
            for type_name, type_info in node.items():
                # 当前类型的所有祖先 + 自己
                full_path = ancestors + [type_name]
                type_map[type_name] = full_path
                
                # 递归处理子类型
                if isinstance(type_info, dict) and 'children' in type_info:
                    traverse(type_info['children'], full_path)
        
        traverse(hierarchy.get('hierarchy', {}), [])
        
        self._type_hierarchy = type_map
        return type_map
    
    def get_category_for_entity(self, entity: str) -> Optional[str]:
        """
        根据实体名称获取其类别
        
        Args:
            entity: 实体名称（可以是别名）
        
        Returns:
            类别名称，如果未找到则返回 None
        """
        domain_dict = self.load_domain_dict()
        
        # 标准化输入
        entity_lower = entity.lower().strip()
        
        for category, aliases in domain_dict.items():
            for alias in aliases:
                if alias.lower().strip() == entity_lower:
                    return category
        
        return None
    
    def export_for_canonical_resolver(self) -> Dict:
        """
        导出适用于 CanonicalResolver 的配置格式
        
        Returns:
            {
                'canonical_names': {alias: canonical},
                'category_mapping': {canonical: category}
            }
        """
        domain_dict = self.load_domain_dict()
        canonical_names = {}
        category_mapping = {}
        
        for category, aliases in domain_dict.items():
            if not aliases:
                continue
            
            canonical = aliases[0]
            category_mapping[canonical] = category
            
            for alias in aliases:
                canonical_names[alias] = canonical
                canonical_names[alias.lower()] = canonical
        
        return {
            'canonical_names': canonical_names,
            'category_mapping': category_mapping
        }
    
    def export_for_import_script(self) -> Dict[str, List[str]]:
        """
        导出适用于 import_to_neo4j_final.py 的类型层级
        
        Returns:
            {type_name: [ancestors]}
        """
        return self.get_type_hierarchy_map()
    
    def reload(self):
        """重新加载所有配置（清除缓存）"""
        self._domain_dict = None
        self._hierarchy = None
        self._canonical_mapping = None
        self._type_hierarchy = None


def main():
    """示例用法"""
    loader = DomainConfigLoader()
    
    print("=" * 70)
    print(" 领域配置加载示例")
    print("=" * 70)
    print()
    
    # 1. 加载实体别名
    print("📋 实体别名配置:")
    domain_dict = loader.load_domain_dict()
    for category, aliases in list(domain_dict.items())[:3]:
        print(f"   {category}: {len(aliases)} 个别名")
        print(f"      标准名: {aliases[0]}")
        print(f"      别名: {', '.join(aliases[1:4])}...")
    print()
    
    # 2. 获取标准名称映射
    print("🔗 别名映射示例:")
    mapping = loader.get_canonical_mapping()
    examples = [
        "PWD",
        "pine wilt disease",
        "B. xylophilus",
        "天牛",
        "马尾松"
    ]
    for example in examples:
        canonical = mapping.get(example, "未找到")
        print(f"   '{example}' → '{canonical}'")
    print()
    
    # 3. 类型层级
    print("🌳 类型层级示例:")
    type_map = loader.get_type_hierarchy_map()
    examples = ["Nematode", "Pine", "Beetle", "ChemicalControl"]
    for example in examples:
        if example in type_map:
            path = " → ".join(type_map[example])
            print(f"   {example}: {path}")
    print()
    
    # 4. 查询类别
    print("🔍 实体类别查询:")
    entities = ["松材线虫", "马尾松", "松褐天牛", "清理病死树"]
    for entity in entities:
        category = loader.get_category_for_entity(entity)
        print(f"   '{entity}' 属于 {category}")
    print()
    
    print("✅ 配置加载成功！")


if __name__ == "__main__":
    main()
