#!/usr/bin/env python3
"""
领域配置验证工具
检查 domain_dict.json 和 type_hierarchy.json 的有效性
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Set, Any

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class DomainConfigValidator:
    """领域配置验证器"""
    
    def __init__(self, domain_dict_path: str, hierarchy_path: str):
        self.domain_dict_path = Path(domain_dict_path)
        self.hierarchy_path = Path(hierarchy_path)
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.stats: Dict[str, Any] = {}
    
    def validate(self) -> bool:
        """执行所有验证检查"""
        print("=" * 70)
        print(" 领域配置验证工具")
        print("=" * 70)
        print()
        
        # 1. 检查文件存在性
        if not self._check_files_exist():
            return False
        
        # 2. 验证 JSON 格式
        domain_dict, hierarchy = self._validate_json_format()
        if domain_dict is None or hierarchy is None:
            return False
        
        # 3. 验证实体别名映射
        self._validate_domain_dict(domain_dict)
        
        # 4. 验证类型层级
        self._validate_hierarchy(hierarchy)
        
        # 5. 交叉验证
        self._cross_validate(domain_dict, hierarchy)
        
        # 6. 输出结果
        self._print_results()
        
        return len(self.errors) == 0
    
    def _check_files_exist(self) -> bool:
        """检查配置文件是否存在"""
        print("📁 检查配置文件...")
        
        if not self.domain_dict_path.exists():
            self.errors.append(f"实体别名配置文件不存在: {self.domain_dict_path}")
            return False
        
        if not self.hierarchy_path.exists():
            self.errors.append(f"类型层级配置文件不存在: {self.hierarchy_path}")
            return False
        
        print(f"   ✓ {self.domain_dict_path.name}")
        print(f"   ✓ {self.hierarchy_path.name}")
        print()
        return True
    
    def _validate_json_format(self) -> tuple:
        """验证 JSON 格式"""
        print("🔍 验证 JSON 格式...")
        
        # 验证 domain_dict.json
        try:
            with open(self.domain_dict_path, 'r', encoding='utf-8') as f:
                domain_dict = json.load(f)
            print(f"   ✓ {self.domain_dict_path.name} 格式正确")
        except json.JSONDecodeError as e:
            self.errors.append(f"domain_dict.json JSON 格式错误: {e}")
            domain_dict = None
        
        # 验证 type_hierarchy.json
        try:
            with open(self.hierarchy_path, 'r', encoding='utf-8') as f:
                hierarchy = json.load(f)
            print(f"   ✓ {self.hierarchy_path.name} 格式正确")
        except json.JSONDecodeError as e:
            self.errors.append(f"type_hierarchy.json JSON 格式错误: {e}")
            hierarchy = None
        
        print()
        return domain_dict, hierarchy
    
    def _validate_domain_dict(self, domain_dict: Dict):
        """验证实体别名映射"""
        print("🏷️  验证实体别名映射...")
        
        if not isinstance(domain_dict, dict):
            self.errors.append("domain_dict 应该是字典类型")
            return
        
        categories = list(domain_dict.keys())
        total_aliases = 0
        duplicates = self._find_duplicate_aliases(domain_dict)
        
        for category, aliases in domain_dict.items():
            if not isinstance(aliases, list):
                self.errors.append(f"类别 '{category}' 的值应该是列表")
                continue
            
            if len(aliases) == 0:
                self.warnings.append(f"类别 '{category}' 没有别名")
                continue
            
            # 检查空字符串
            empty_aliases = [i for i, a in enumerate(aliases) if not a.strip()]
            if empty_aliases:
                self.errors.append(
                    f"类别 '{category}' 包含空别名（位置：{empty_aliases}）"
                )
            
            total_aliases += len(aliases)
            print(f"   ✓ {category}: {len(aliases)} 个别名")
        
        self.stats['categories'] = len(categories)
        self.stats['total_aliases'] = total_aliases
        self.stats['duplicates'] = len(duplicates)
        
        if duplicates:
            self.warnings.append(f"发现 {len(duplicates)} 组重复别名")
            for alias, cats in list(duplicates.items())[:5]:
                self.warnings.append(f"  - '{alias}' 出现在: {', '.join(cats)}")
        
        print()
    
    def _find_duplicate_aliases(self, domain_dict: Dict) -> Dict[str, List[str]]:
        """查找重复的别名"""
        alias_to_categories: Dict[str, List[str]] = {}
        
        for category, aliases in domain_dict.items():
            for alias in aliases:
                normalized = alias.lower().strip()
                if normalized in alias_to_categories:
                    alias_to_categories[normalized].append(category)
                else:
                    alias_to_categories[normalized] = [category]
        
        # 只返回出现在多个类别中的别名
        return {
            alias: cats
            for alias, cats in alias_to_categories.items()
            if len(cats) > 1
        }
    
    def _validate_hierarchy(self, hierarchy: Dict):
        """验证类型层级"""
        print("🌳 验证类型层级...")
        
        if not isinstance(hierarchy, dict):
            self.errors.append("hierarchy 应该是字典类型")
            return
        
        if 'hierarchy' not in hierarchy:
            self.errors.append("类型层级配置应包含 'hierarchy' 键")
            return
        
        root_types = list(hierarchy['hierarchy'].keys())
        all_types = self._collect_all_types(hierarchy['hierarchy'])
        max_depth = self._calculate_max_depth(hierarchy['hierarchy'])
        
        print(f"   ✓ 根类型数量: {len(root_types)}")
        print(f"   ✓ 总类型数量: {len(all_types)}")
        print(f"   ✓ 最大深度: {max_depth}")
        
        self.stats['root_types'] = len(root_types)
        self.stats['all_types'] = len(all_types)
        self.stats['max_depth'] = max_depth
        
        # 检查循环依赖
        cycles = self._detect_cycles(hierarchy['hierarchy'])
        if cycles:
            self.errors.append(f"检测到循环依赖: {cycles}")
        
        print()
    
    def _collect_all_types(self, hierarchy: Dict, types: Set[str] = None) -> Set[str]:
        """收集所有类型"""
        if types is None:
            types = set()
        
        for type_name, type_info in hierarchy.items():
            types.add(type_name)
            if isinstance(type_info, dict) and 'children' in type_info:
                self._collect_all_types(type_info['children'], types)
        
        return types
    
    def _calculate_max_depth(self, hierarchy: Dict, current_depth: int = 0) -> int:
        """计算最大深度"""
        if not hierarchy:
            return current_depth
        
        max_child_depth = current_depth
        for type_info in hierarchy.values():
            if isinstance(type_info, dict) and 'children' in type_info:
                child_depth = self._calculate_max_depth(
                    type_info['children'],
                    current_depth + 1
                )
                max_child_depth = max(max_child_depth, child_depth)
        
        return max_child_depth
    
    def _detect_cycles(self, hierarchy: Dict, visited: Set[str] = None) -> List[str]:
        """检测循环依赖（简化版）"""
        # 对于树形结构，只要没有重复的类型名就不会有循环
        all_types = self._collect_all_types(hierarchy)
        type_counts = {}
        
        def count_types(h: Dict):
            for type_name, type_info in h.items():
                type_counts[type_name] = type_counts.get(type_name, 0) + 1
                if isinstance(type_info, dict) and 'children' in type_info:
                    count_types(type_info['children'])
        
        count_types(hierarchy)
        return [t for t, c in type_counts.items() if c > 1]
    
    def _cross_validate(self, domain_dict: Dict, hierarchy: Dict):
        """交叉验证配置一致性"""
        print("🔗 交叉验证...")
        
        # 收集所有类型
        hierarchy_types = self._collect_all_types(hierarchy['hierarchy'])
        domain_categories = set(domain_dict.keys())
        
        # 检查 domain_dict 中的类别是否在 hierarchy 中
        missing_in_hierarchy = domain_categories - hierarchy_types
        if missing_in_hierarchy:
            self.warnings.append(
                f"以下类别在 domain_dict 中但不在 type_hierarchy 中: "
                f"{', '.join(missing_in_hierarchy)}"
            )
        
        # 检查 hierarchy 中的类型是否在 domain_dict 中
        missing_in_domain = hierarchy_types - domain_categories
        if missing_in_domain:
            self.warnings.append(
                f"以下类型在 type_hierarchy 中但不在 domain_dict 中: "
                f"{', '.join(list(missing_in_domain)[:10])}"
            )
        
        overlap = len(domain_categories & hierarchy_types)
        print(f"   ✓ 类型重叠率: {overlap}/{len(domain_categories)} "
              f"({overlap/len(domain_categories)*100:.1f}%)")
        print()
    
    def _print_results(self):
        """输出验证结果"""
        print("=" * 70)
        print(" 验证结果")
        print("=" * 70)
        print()
        
        # 统计信息
        if self.stats:
            print("📊 统计信息:")
            for key, value in self.stats.items():
                print(f"   - {key}: {value}")
            print()
        
        # 错误
        if self.errors:
            print(f"❌ 发现 {len(self.errors)} 个错误:")
            for error in self.errors:
                print(f"   • {error}")
            print()
        else:
            print("✅ 没有发现错误")
            print()
        
        # 警告
        if self.warnings:
            print(f"⚠️  发现 {len(self.warnings)} 个警告:")
            for warning in self.warnings[:10]:  # 只显示前10个
                print(f"   • {warning}")
            if len(self.warnings) > 10:
                print(f"   ... 还有 {len(self.warnings) - 10} 个警告")
            print()
        
        # 总结
        if len(self.errors) == 0:
            print("✅ 配置验证通过！")
        else:
            print("❌ 配置验证失败，请修复错误后重试。")
        print()


def main():
    """主函数"""
    domain_dict_path = project_root / "config" / "domain_dict.json"
    hierarchy_path = project_root / "config" / "type_hierarchy.json"
    
    validator = DomainConfigValidator(
        str(domain_dict_path),
        str(hierarchy_path)
    )
    
    success = validator.validate()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
