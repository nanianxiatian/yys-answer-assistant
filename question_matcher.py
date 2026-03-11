"""
题目匹配器模块 - 使用模糊匹配算法匹配题库
"""
import re
from difflib import SequenceMatcher
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
import jieba


class QuestionMatcher:
    """题目匹配器类，使用多种模糊匹配算法"""
    
    def __init__(self, questions_data):
        """
        初始化匹配器
        
        Args:
            questions_data: list of dict, 每个dict包含 'question' 和 'answer' 键
        """
        self.questions_data = questions_data
        self.question_texts = [q['question'] for q in questions_data]
        
    def _preprocess_text(self, text):
        """
        预处理文本：去除多余空格，统一标点
        
        Args:
            text: 原始文本
            
        Returns:
            str: 处理后的文本
        """
        # 去除多余空格
        text = re.sub(r'\s+', '', text)
        # 统一标点
        text = text.replace('？', '?').replace('。', '.')
        return text.strip()
    
    def _calculate_keyword_match(self, text1, text2):
        """
        计算关键字匹配度 - 使用jieba分词
        
        Args:
            text1: 识别的文本
            text2: 题库中的文本
            
        Returns:
            float: 匹配度分数 (0-100)
        """
        # 使用jieba分词，将中文句子拆分成词语
        keywords1 = set(jieba.lcut(text1))
        keywords2 = set(jieba.lcut(text2))
        
        # 过滤掉单字和标点，只保留有意义的词（长度>=2）
        keywords1 = {w for w in keywords1 if len(w) >= 2 and re.match(r'[\u4e00-\u9fff]+', w)}
        keywords2 = {w for w in keywords2 if len(w) >= 2 and re.match(r'[\u4e00-\u9fff]+', w)}
        
        if not keywords1 or not keywords2:
            return 0
            
        # 计算交集
        intersection = keywords1 & keywords2
        
        # 基于较短文本的匹配度
        min_len = min(len(keywords1), len(keywords2))
        if min_len == 0:
            return 0
            
        keyword_score = len(intersection) / min_len * 100
        
        return keyword_score
    
    def _calculate_similarity(self, text1, text2):
        """
        计算两段文本的综合相似度
        
        Args:
            text1: 识别的文本
            text2: 题库中的文本
            
        Returns:
            float: 综合相似度分数 (0-100)
        """
        text1 = self._preprocess_text(text1)
        text2 = self._preprocess_text(text2)
        
        # 1. 使用fuzzywuzzy的partial_ratio（适合子串匹配）
        partial_score = fuzz.partial_ratio(text1, text2)
        
        # 2. 使用token_sort_ratio（忽略词序）
        token_score = fuzz.token_sort_ratio(text1, text2)
        
        # 3. 使用SequenceMatcher（基于最长公共子序列）
        seq_score = SequenceMatcher(None, text1, text2).ratio() * 100
        
        # 4. 关键字匹配度
        keyword_score = self._calculate_keyword_match(text1, text2)
        
        # 加权综合分数
        # 关键字匹配权重最高，因为题目通常有关键词
        final_score = (
            partial_score * 0.25 +
            token_score * 0.20 +
            seq_score * 0.15 +
            keyword_score * 0.40
        )
        
        return final_score
    
    def find_matches(self, query_text, top_k=5, threshold=30):
        """
        查找最匹配的题目
        
        Args:
            query_text: 查询文本（OCR识别结果）
            top_k: 返回前k个结果
            threshold: 最低匹配阈值
            
        Returns:
            list: 匹配结果列表，每项包含题目、答案和匹配度
        """
        if not self.questions_data:
            return []
            
        # 计算所有题目的匹配度
        scored_results = []
        for item in self.questions_data:
            score = self._calculate_similarity(query_text, item['question'])
            if score >= threshold:
                scored_results.append({
                    'question': item['question'],
                    'answer': item['answer'],
                    'score': score
                })
        
        # 按匹配度降序排序
        scored_results.sort(key=lambda x: x['score'], reverse=True)
        
        # 返回前k个结果
        return scored_results[:top_k]
    
    def find_best_match(self, query_text, threshold=50):
        """
        查找最佳匹配
        
        Args:
            query_text: 查询文本
            threshold: 最低匹配阈值
            
        Returns:
            dict or None: 最佳匹配结果
        """
        matches = self.find_matches(query_text, top_k=1, threshold=threshold)
        return matches[0] if matches else None
