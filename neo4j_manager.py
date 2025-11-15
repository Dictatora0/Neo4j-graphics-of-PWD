#!/usr/bin/env python3
"""
Neo4j 数据库管理器
功能：清空数据库、备份、回滚
"""

import os
import shutil
from datetime import datetime
from neo4j import GraphDatabase, basic_auth
from logger_config import get_logger

logger = get_logger('Neo4jManager')


class Neo4jManager:
    """Neo4j 数据库管理器"""
    
    def __init__(self, uri="bolt://localhost:7687", user="neo4j", password="password"):
        """
        初始化 Neo4j 管理器
        
        Args:
            uri: Neo4j 连接 URI
            user: 用户名
            password: 密码
        """
        self.uri = uri
        self.user = str(user)  # 确保是字符串
        self.password = str(password)  # 确保是字符串
        self.driver = None
        self.backup_dir = "./output/neo4j_backups"
        
        # 确保备份目录存在
        os.makedirs(self.backup_dir, exist_ok=True)
    
    def connect(self):
        """连接到 Neo4j"""
        try:
            self.driver = GraphDatabase.driver(self.uri, auth=basic_auth(self.user, self.password))
            # 测试连接
            with self.driver.session() as session:
                session.run("RETURN 1")
            logger.info(f"✓ 成功连接到 Neo4j: {self.uri}")
            return True
        except Exception as e:
            logger.warning(f"⚠️  无法连接到 Neo4j: {e}")
            logger.info("如果 Neo4j 未运行，可以跳过数据库操作")
            return False
    
    def close(self):
        """关闭连接"""
        if self.driver:
            self.driver.close()
            logger.info("✓ Neo4j 连接已关闭")
    
    def backup_database(self):
        """
        备份当前数据库内容
        
        Returns:
            str: 备份文件路径，失败返回 None
        """
        if not self.driver:
            logger.warning("未连接到 Neo4j，跳过备份")
            return None
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(self.backup_dir, f"backup_{timestamp}.cypher")
            
            with self.driver.session() as session:
                # 获取节点数量
                result = session.run("MATCH (n) RETURN count(n) as count")
                node_count = result.single()["count"]
                
                # 获取关系数量
                result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
                rel_count = result.single()["count"]
                
                if node_count == 0 and rel_count == 0:
                    logger.info("数据库为空，无需备份")
                    return None
                
                logger.info(f"开始备份数据库: {node_count} 个节点, {rel_count} 个关系")
                
                with open(backup_file, 'w', encoding='utf-8') as f:
                    # 写入备份信息
                    f.write(f"// Neo4j 数据库备份\n")
                    f.write(f"// 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"// 节点数: {node_count}, 关系数: {rel_count}\n\n")
                    
                    # 导出节点
                    f.write("// ========== 节点 ==========\n")
                    result = session.run("""
                        MATCH (n)
                        RETURN n, labels(n) as labels, properties(n) as props
                    """)
                    
                    for record in result:
                        labels = ':'.join(record['labels'])
                        props = record['props']
                        props_str = ', '.join([f"{k}: {repr(v)}" for k, v in props.items()])
                        f.write(f"CREATE (:{labels} {{{props_str}}});\n")
                    
                    # 导出关系
                    f.write("\n// ========== 关系 ==========\n")
                    result = session.run("""
                        MATCH (a)-[r]->(b)
                        RETURN a.id as start_id, type(r) as rel_type, 
                               properties(r) as props, b.id as end_id
                    """)
                    
                    for record in result:
                        start_id = record['start_id']
                        end_id = record['end_id']
                        rel_type = record['rel_type']
                        props = record['props']
                        props_str = ', '.join([f"{k}: {repr(v)}" for k, v in props.items()])
                        
                        f.write(f"MATCH (a {{id: {repr(start_id)}}}), (b {{id: {repr(end_id)}}})\n")
                        f.write(f"CREATE (a)-[:{rel_type} {{{props_str}}}]->(b);\n")
                
                logger.info(f"✓ 备份完成: {backup_file}")
                return backup_file
                
        except Exception as e:
            logger.error(f"备份失败: {e}")
            return None
    
    def clear_database(self):
        """
        清空数据库
        
        Returns:
            bool: 是否成功
        """
        if not self.driver:
            logger.warning("未连接到 Neo4j，跳过清空操作")
            return False
        
        try:
            with self.driver.session() as session:
                # 获取当前数据量
                result = session.run("MATCH (n) RETURN count(n) as count")
                node_count = result.single()["count"]
                
                if node_count == 0:
                    logger.info("数据库已经为空")
                    return True
                
                logger.info(f"清空数据库: {node_count} 个节点")
                
                # 删除所有节点和关系
                session.run("MATCH (n) DETACH DELETE n")
                
                logger.info("✓ 数据库已清空")
                return True
                
        except Exception as e:
            logger.error(f"清空数据库失败: {e}")
            return False
    
    def restore_from_backup(self, backup_file):
        """
        从备份恢复数据库
        
        Args:
            backup_file: 备份文件路径
            
        Returns:
            bool: 是否成功
        """
        if not self.driver:
            logger.warning("未连接到 Neo4j，跳过恢复操作")
            return False
        
        if not os.path.exists(backup_file):
            logger.error(f"备份文件不存在: {backup_file}")
            return False
        
        try:
            logger.info(f"从备份恢复: {backup_file}")
            
            # 先清空数据库
            self.clear_database()
            
            # 读取并执行备份文件
            with open(backup_file, 'r', encoding='utf-8') as f:
                cypher_script = f.read()
            
            with self.driver.session() as session:
                # 分割并执行每条语句
                statements = [s.strip() for s in cypher_script.split(';') if s.strip() and not s.strip().startswith('//')]
                
                for stmt in statements:
                    if stmt:
                        session.run(stmt)
            
            logger.info("✓ 数据库恢复完成")
            return True
            
        except Exception as e:
            logger.error(f"恢复数据库失败: {e}")
            return False
    
    def get_latest_backup(self):
        """
        获取最新的备份文件
        
        Returns:
            str: 备份文件路径，无备份返回 None
        """
        if not os.path.exists(self.backup_dir):
            return None
        
        backups = [f for f in os.listdir(self.backup_dir) if f.startswith('backup_') and f.endswith('.cypher')]
        
        if not backups:
            return None
        
        backups.sort(reverse=True)
        return os.path.join(self.backup_dir, backups[0])
    
    def list_backups(self):
        """
        列出所有备份
        
        Returns:
            list: 备份文件列表
        """
        if not os.path.exists(self.backup_dir):
            return []
        
        backups = [f for f in os.listdir(self.backup_dir) if f.startswith('backup_') and f.endswith('.cypher')]
        backups.sort(reverse=True)
        
        return [os.path.join(self.backup_dir, b) for b in backups]


def main():
    """测试函数"""
    import sys
    
    if len(sys.argv) < 2:
        print("用法:")
        print("  python neo4j_manager.py backup    # 备份数据库")
        print("  python neo4j_manager.py clear     # 清空数据库")
        print("  python neo4j_manager.py restore   # 恢复最新备份")
        print("  python neo4j_manager.py list      # 列出所有备份")
        sys.exit(1)
    
    command = sys.argv[1]
    
    # 从配置文件读取 Neo4j 连接信息
    try:
        from config_loader import load_config
        config = load_config()
        uri = config.get('neo4j.uri', 'bolt://localhost:7687')
        user = config.get('neo4j.user', 'neo4j')
        password = config.get('neo4j.password', 'password')
    except:
        uri = 'bolt://localhost:7687'
        user = 'neo4j'
        password = 'password'
    
    manager = Neo4jManager(uri, user, password)
    
    if command == 'backup':
        if manager.connect():
            backup_file = manager.backup_database()
            if backup_file:
                print(f"✓ 备份完成: {backup_file}")
            manager.close()
    
    elif command == 'clear':
        if manager.connect():
            manager.clear_database()
            manager.close()
    
    elif command == 'restore':
        if manager.connect():
            latest = manager.get_latest_backup()
            if latest:
                manager.restore_from_backup(latest)
            else:
                print("没有找到备份文件")
            manager.close()
    
    elif command == 'list':
        backups = manager.list_backups()
        if backups:
            print("可用的备份:")
            for b in backups:
                print(f"  - {b}")
        else:
            print("没有找到备份文件")
    
    else:
        print(f"未知命令: {command}")
        sys.exit(1)


if __name__ == '__main__':
    main()
