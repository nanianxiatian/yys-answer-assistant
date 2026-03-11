"""
题库加载器模块 - 从Excel文件加载题库，保存到SQLite数据库
支持增量加载、重复检测、自动保存配置
"""
import pandas as pd
import os
import json
import sqlite3
import hashlib


class QuestionBankLoader:
    """题库加载器类 - 使用SQLite存储"""
    
    def __init__(self, file_path=None, config_file="bank_config.json", db_path="question_bank.db"):
        """
        初始化加载器
        
        Args:
            file_path: Excel文件路径（用于导入）
            config_file: 配置文件路径（用于保存其他配置）
            db_path: SQLite数据库文件路径
        """
        self.file_path = file_path
        self.config_file = config_file
        self.db_path = db_path
        self.loaded_files = set()  # 记录已加载的文件
        
        # 初始化数据库
        self._init_database()
        self._load_config()
    
    def _get_connection(self):
        """获取数据库连接"""
        return sqlite3.connect(self.db_path)
        
    def _init_database(self):
        """初始化SQLite数据库"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 创建题目表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS questions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    question TEXT NOT NULL UNIQUE,
                    answer TEXT,
                    source_file TEXT,
                    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 创建索引加速查询
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_question ON questions(question)
            """)
            
            conn.commit()
            conn.close()
            print(f"[数据库] 已初始化: {self.db_path}")
        except Exception as e:
            print(f"[数据库] 初始化失败: {e}")
    
    def _load_config(self):
        """加载配置文件"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # 恢复已加载文件列表
                    self.loaded_files = set(config.get('loaded_files', []))
                    # 数据库文件路径（允许从配置恢复）
                    self.db_path = config.get('db_path', self.db_path)
                    print(f"[配置] 已加载配置，已加载文件: {len(self.loaded_files)} 个")
        except Exception as e:
            print(f"[配置] 加载配置文件失败: {e}")
            self.loaded_files = set()
    
    def _save_config(self):
        """保存配置文件（只保存已加载文件列表等元数据）"""
        try:
            config = {
                'loaded_files': list(self.loaded_files),
                'db_path': self.db_path
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[配置] 保存配置文件失败: {e}")
    
    def load_from_excel(self, file_path=None, append=True):
        """
        从Excel文件加载题库
        
        Args:
            file_path: Excel文件路径，如果为None则使用初始化时的路径
            append: 是否追加模式（True=增量加载，False=清空后加载）
            
        Returns:
            dict: 加载结果 {'success': bool, 'added': int, 'duplicates': int, 'total': int}
        """
        if file_path:
            self.file_path = file_path
            
        if not self.file_path or not os.path.exists(self.file_path):
            return {'success': False, 'added': 0, 'duplicates': 0, 'total': 0}
        
        # 检查是否已经加载过这个文件
        file_realpath = os.path.realpath(self.file_path)
        current_count = self.get_question_count()
        
        if file_realpath in self.loaded_files and append:
            # 如果数据库为空但文件记录还在，说明之前清空过，重新加载
            if current_count == 0:
                print(f"[提示] 检测到文件已记录但数据库为空，重新加载: {self.file_path}")
                self.loaded_files.discard(file_realpath)  # 移除记录，允许重新加载
            else:
                print(f"[提示] 文件已加载过: {self.file_path}")
                return {'success': True, 'added': 0, 'duplicates': 0, 'total': current_count}
        
        try:
            # 如果不追加，清空数据库
            if not append:
                self.clear_bank()
            
            # 读取Excel文件
            df = pd.read_excel(self.file_path)
            
            # 自动识别列名
            question_col = None
            answer_col = None
            
            # 常见的问题列名
            question_keywords = ['问题', '题目', 'question', 'quiz', '题干', '试题']
            # 常见的答案列名
            answer_keywords = ['答案', 'answer', 'ans', '解答', '回答']
            
            columns = df.columns.tolist()
            
            # 尝试自动识别列
            for col in columns:
                col_lower = str(col).lower()
                for keyword in question_keywords:
                    if keyword in col_lower:
                        question_col = col
                        break
                        
            for col in columns:
                col_lower = str(col).lower()
                for keyword in answer_keywords:
                    if keyword in col_lower:
                        answer_col = col
                        break
            
            # 如果没有自动识别到，使用前两列
            if question_col is None and len(columns) >= 1:
                question_col = columns[0]
            if answer_col is None and len(columns) >= 2:
                answer_col = columns[1]
            elif answer_col is None and len(columns) == 1:
                answer_col = columns[0]
            
            # 加载数据到数据库
            conn = self._get_connection()
            cursor = conn.cursor()
            
            added_count = 0
            duplicate_count = 0
            
            for _, row in df.iterrows():
                question = str(row.get(question_col, '')).strip()
                answer = str(row.get(answer_col, '')).strip()
                
                if question and question != 'nan':
                    try:
                        cursor.execute(
                            "INSERT INTO questions (question, answer, source_file) VALUES (?, ?, ?)",
                            (question, answer if answer != 'nan' else '', file_realpath)
                        )
                        added_count += 1
                    except sqlite3.IntegrityError:
                        # 重复问题
                        duplicate_count += 1
            
            conn.commit()
            conn.close()
            
            # 记录已加载的文件
            if added_count > 0:
                self.loaded_files.add(file_realpath)
                self._save_config()
            
            return {
                'success': True,
                'added': added_count,
                'duplicates': duplicate_count,
                'total': self.get_question_count()
            }
            
        except Exception as e:
            print(f"加载题库失败: {e}")
            return {'success': False, 'added': 0, 'duplicates': 0, 'total': 0}
    
    def clear_bank(self):
        """
        清空题库
        
        Returns:
            int: 清空的题目数量
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 获取当前数量
            cursor.execute("SELECT COUNT(*) FROM questions")
            count = cursor.fetchone()[0]
            
            # 清空表
            cursor.execute("DELETE FROM questions")
            
            # 重置自增ID
            cursor.execute("DELETE FROM sqlite_sequence WHERE name='questions'")
            
            conn.commit()
            conn.close()
            
            # 清空已加载文件记录
            self.loaded_files = set()
            self._save_config()
            
            return count
        except Exception as e:
            print(f"清空题库失败: {e}")
            return 0
    
    def get_questions(self, limit=None, offset=0):
        """
        获取已加载的题目列表
        
        Args:
            limit: 限制返回数量
            offset: 起始偏移量
            
        Returns:
            list: 题目数据
        """
        try:
            conn = self._get_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if limit:
                cursor.execute(
                    "SELECT question, answer FROM questions LIMIT ? OFFSET ?",
                    (limit, offset)
                )
            else:
                cursor.execute("SELECT question, answer FROM questions")
            
            rows = cursor.fetchall()
            conn.close()
            
            return [{'question': row['question'], 'answer': row['answer']} for row in rows]
        except Exception as e:
            print(f"获取题目失败: {e}")
            return []
    
    def get_question_count(self):
        """
        获取题目数量
        
        Returns:
            int: 题目数量
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM questions")
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except Exception as e:
            print(f"获取题目数量失败: {e}")
            return 0
    
    def add_question(self, question, answer, source_file=None):
        """
        添加新题目
        
        Args:
            question: 问题
            answer: 答案
            source_file: 来源文件（可选）
            
        Returns:
            bool: 是否成功添加（False表示重复）
        """
        question = question.strip()
        answer = answer.strip()
        
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                "INSERT INTO questions (question, answer, source_file) VALUES (?, ?, ?)",
                (question, answer, source_file)
            )
            
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            return False
        except Exception as e:
            print(f"添加题目失败: {e}")
            return False
    
    def export_to_excel(self, file_path=None):
        """
        导出题库到Excel文件（可选，用于备份）
        
        Args:
            file_path: 保存路径，如果为None则使用默认路径
            
        Returns:
            bool: 是否成功
        """
        if not file_path:
            file_path = "question_backup.xlsx"
            
        try:
            questions = self.get_questions()
            if not questions:
                print("题库为空，无需导出")
                return False
                
            df = pd.DataFrame(questions)
            df.to_excel(file_path, index=False, engine='openpyxl')
            print(f"题库已导出到: {file_path}")
            return True
        except Exception as e:
            print(f"导出题库失败: {e}")
            return False
    
    def search_questions(self, keyword):
        """
        搜索题目
        
        Args:
            keyword: 搜索关键词
            
        Returns:
            list: 匹配的题目列表
        """
        try:
            conn = self._get_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT question, answer FROM questions WHERE question LIKE ?",
                (f"%{keyword}%",)
            )
            
            rows = cursor.fetchall()
            conn.close()
            
            return [{'question': row['question'], 'answer': row['answer']} for row in rows]
        except Exception as e:
            print(f"搜索题目失败: {e}")
            return []


def create_sample_question_bank(file_path="questions.xlsx"):
    """
    创建示例题库文件（Excel格式，用于导入）
    
    Args:
        file_path: 输出文件路径
    """
    sample_data = {
        '问题': [
            '以下哪个不是阴阳师中的SSR式神？',
            '阴阳师中，姑获鸟的别称是什么？',
            '以下哪个御魂适合输出型式神？',
            '阴阳师中，鬼火的上限是多少？',
            '以下哪个不是阴阳师的日常活动？',
            '阴阳师中，速度最快的式神是？',
            '以下哪个是防御型御魂？',
            '阴阳师中，结界突破的门票叫什么？',
            '以下哪个式神擅长治疗？',
            '阴阳师中，御魂副本第八层被称为什么？'
        ],
        '答案': [
            'N卡',
            '鸟姐',
            '针女',
            '8',
            '排位赛',
            '镰鼬',
            '被服',
            '结界券',
            '桃花妖',
            '魂八'
        ]
    }
    
    df = pd.DataFrame(sample_data)
    df.to_excel(file_path, index=False, engine='openpyxl')
    print(f"示例题库已创建: {file_path}")
    return file_path


def migrate_from_excel(excel_path, db_path="question_bank.db"):
    """
    从Excel迁移到SQLite数据库
    
    Args:
        excel_path: Excel文件路径
        db_path: SQLite数据库路径
        
    Returns:
        dict: 迁移结果
    """
    try:
        loader = QuestionBankLoader(db_path=db_path)
        result = loader.load_from_excel(excel_path, append=True)
        return {
            'success': result['success'],
            'migrated': result['added'],
            'duplicates': result['duplicates'],
            'total': result['total']
        }
    except Exception as e:
        print(f"迁移失败: {e}")
        return {'success': False, 'migrated': 0, 'duplicates': 0, 'total': 0}


if __name__ == "__main__":
    # 测试SQLite存储
    print("测试SQLite题库存储...")
    
    # 创建示例题库
    create_sample_question_bank("sample_questions.xlsx")
    
    # 加载示例题库到SQLite
    loader = QuestionBankLoader(db_path="test_question_bank.db")
    result = loader.load_from_excel("sample_questions.xlsx")
    print(f"\n加载结果: {result}")
    print(f"题库总数: {loader.get_question_count()}")
    
    # 测试重复加载（应该被忽略）
    result2 = loader.load_from_excel("sample_questions.xlsx")
    print(f"\n重复加载结果: {result2}")
    
    # 测试添加新题
    loader.add_question("测试问题", "测试答案")
    print(f"\n添加后总数: {loader.get_question_count()}")
    
    # 测试搜索
    results = loader.search_questions("阴阳师")
    print(f"\n搜索'阴阳师'找到 {len(results)} 条结果")
    
    # 导出备份
    loader.export_to_excel("backup.xlsx")
    
    # 清空测试数据
    loader.clear_bank()
    print(f"\n清空后总数: {loader.get_question_count()}")
