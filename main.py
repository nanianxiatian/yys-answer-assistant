"""
阴阳师答题助手 - GUI界面
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import time
from PIL import Image, ImageTk
import ctypes
import sys

# 设置DPI感知（Windows）- 必须在创建任何窗口前设置
if sys.platform == 'win32':
    try:
        # 设置进程为DPI感知
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # 2 = Per Monitor DPI Aware
    except:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except:
            pass

# 固定窗口尺寸常量
WINDOW_WIDTH = 900
WINDOW_HEIGHT = 850


class YYSAssistantGUI:
    """阴阳师答题助手GUI类"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("阴阳师答题助手 v1.0")
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.resizable(True, True)
        
        # 初始化组件
        self.ocr_engine = None
        self.question_matcher = None
        self.loader = None
        self.capture_region = None
        self.is_running = False
        self.interval = 2.0
        self.overlay_window = None  # 遮罩窗口
        
        # 绑定关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        
        # 创建界面
        self._create_widgets()
        self._init_components()
        
    def _create_widgets(self):
        """创建界面组件"""
        # 主框架 - 使用左右分栏布局
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置行列权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=0)  # 左边按钮区域不扩展
        main_frame.columnconfigure(1, weight=3)  # 右边结果区域扩展（权重3）
        main_frame.rowconfigure(0, weight=3)  # 主要内容区域
        main_frame.rowconfigure(1, weight=0)  # 日志区域不扩展
        
        # === 左侧面板 - 控制区域 ===
        left_frame = ttk.Frame(main_frame, width=240)
        left_frame.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.W), padx=(0, 10))
        left_frame.grid_propagate(False)  # 固定宽度
        
        # === 题库设置区域 ===
        file_frame = ttk.LabelFrame(left_frame, text="题库设置", padding="5")
        file_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=3)
        file_frame.columnconfigure(0, weight=1)
        
        ttk.Label(file_frame, text="题库文件:").grid(row=0, column=0, sticky=tk.W, pady=1)
        self.file_path_var = tk.StringVar()
        self.file_entry = ttk.Entry(file_frame, textvariable=self.file_path_var, width=18)
        self.file_entry.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=1)
        self.file_entry.insert(0, "选择题库")
        self.file_entry.config(foreground='gray')
        
        # 点击时清除placeholder
        def on_entry_click(event):
            if self.file_entry.get() == "选择题库":
                self.file_entry.delete(0, tk.END)
                self.file_entry.config(foreground='black')
        
        def on_focus_out(event):
            if self.file_entry.get() == "":
                self.file_entry.insert(0, "选择题库")
                self.file_entry.config(foreground='gray')
        
        self.file_entry.bind('<FocusIn>', on_entry_click)
        self.file_entry.bind('<FocusOut>', on_focus_out)
        
        # 第一行按钮：浏览、加载(增量)
        btn_frame1 = ttk.Frame(file_frame)
        btn_frame1.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=2)
        ttk.Button(btn_frame1, text="浏览", command=self._browse_file, width=8).pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)
        ttk.Button(btn_frame1, text="加载(增量)", command=self._load_question_bank, width=10).pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)
        
        # 第二行按钮：导出、清空
        btn_frame2 = ttk.Frame(file_frame)
        btn_frame2.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=2)
        ttk.Button(btn_frame2, text="导出", command=self._export_bank, width=8).pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)
        ttk.Button(btn_frame2, text="清空", command=self._clear_question_bank, width=8).pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)
        
        # 题库状态显示（改为两行）
        self.bank_status_var = tk.StringVar(value="题库: 0 道")
        self.files_status_var = tk.StringVar(value="已加载: 0 个文件")
        ttk.Label(file_frame, textvariable=self.bank_status_var, 
                 font=('Microsoft YaHei', 9, 'bold'), foreground='blue').grid(row=4, column=0, sticky=tk.W, pady=1)
        ttk.Label(file_frame, textvariable=self.files_status_var, 
                 font=('Microsoft YaHei', 8, 'bold'), foreground='blue').grid(row=5, column=0, sticky=tk.W, pady=1)
        
        # === 识别区域设置 ===
        region_frame = ttk.LabelFrame(left_frame, text="识别区域", padding="5")
        region_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=3)
        region_frame.columnconfigure(0, weight=1)
        
        self.region_var = tk.StringVar(value="未设置")
        ttk.Label(region_frame, text="当前区域:").grid(row=0, column=0, sticky=tk.W, pady=1)
        ttk.Label(region_frame, textvariable=self.region_var, wraplength=160).grid(row=1, column=0, sticky=tk.W, pady=1)
        
        # 按钮行
        region_btn_frame = ttk.Frame(region_frame)
        region_btn_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=3)
        ttk.Button(region_btn_frame, text="选择区域", command=self._select_region, width=10).pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)
        ttk.Button(region_btn_frame, text="清除选区", command=self._clear_region, width=10).pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)
        
        # === 识别设置 ===
        settings_frame = ttk.LabelFrame(left_frame, text="识别设置", padding="5")
        settings_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=3)
        settings_frame.columnconfigure(0, weight=1)
        
        ttk.Label(settings_frame, text="识别间隔(秒):").grid(row=0, column=0, sticky=tk.W, pady=1)
        self.interval_var = tk.DoubleVar(value=2.0)
        ttk.Spinbox(settings_frame, from_=0.5, to=10.0, increment=0.5, 
                   textvariable=self.interval_var, width=8).grid(row=1, column=0, sticky=tk.W, pady=1)
        
        ttk.Label(settings_frame, text="匹配结果数:").grid(row=2, column=0, sticky=tk.W, pady=(5, 1))
        self.results_var = tk.IntVar(value=20)
        ttk.Spinbox(settings_frame, from_=1, to=20, increment=1,
                   textvariable=self.results_var, width=8).grid(row=3, column=0, sticky=tk.W, pady=1)
        
        # === 控制按钮 ===
        control_frame = ttk.LabelFrame(left_frame, text="控制", padding="5")
        control_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=3)
        control_frame.columnconfigure(0, weight=1)
        
        # 开始识别按钮
        self.start_btn = ttk.Button(control_frame, text="▶ 开始识别", command=self._start_capture, width=16)
        self.start_btn.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=3)
        
        # 停止识别按钮
        self.stop_btn = ttk.Button(control_frame, text="⏹ 停止识别", command=self._stop_capture, state=tk.DISABLED, width=16)
        self.stop_btn.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=3)
        
        # 测试识别按钮
        self.test_btn = ttk.Button(control_frame, text="🎯 测试识别", command=self._test_capture, width=16)
        self.test_btn.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=3)
        
        # === 状态显示 ===
        status_frame = ttk.LabelFrame(left_frame, text="状态", padding="5")
        status_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=3)
        status_frame.columnconfigure(0, weight=1)
        
        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(status_frame, textvariable=self.status_var, font=('Microsoft YaHei', 10, 'bold')).grid(row=0, column=0, sticky=tk.W, pady=1)
        
        self.last_capture_var = tk.StringVar(value="识别文本: 无")
        ttk.Label(status_frame, textvariable=self.last_capture_var, font=('Microsoft YaHei', 9), wraplength=160).grid(row=1, column=0, sticky=tk.W, pady=1)
        
        # === 右侧面板 - 结果显示区域 ===
        right_frame = ttk.LabelFrame(main_frame, text="识别结果", padding="10")
        right_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        right_frame.columnconfigure(0, weight=1)
        right_frame.rowconfigure(0, weight=1)
        
        # 创建结果展示区域 - 使用树形控件或自定义展示
        self.result_canvas = tk.Canvas(right_frame, bg='#f5f5f5', highlightthickness=0)
        self.result_canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 添加滚动条
        result_scrollbar = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=self.result_canvas.yview)
        result_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.result_canvas.configure(yscrollcommand=result_scrollbar.set)
        
        # 在canvas中创建可滚动框架
        self.result_frame = ttk.Frame(self.result_canvas)
        self.result_canvas_window = self.result_canvas.create_window((0, 0), window=self.result_frame, anchor=tk.NW)
        
        # 配置canvas滚动
        def configure_canvas(event):
            self.result_canvas.configure(scrollregion=self.result_canvas.bbox('all'))
            self.result_canvas.itemconfig(self.result_canvas_window, width=event.width)
        
        self.result_frame.bind('<Configure>', configure_canvas)
        self.result_canvas.bind('<Configure>', lambda e: self.result_canvas.itemconfig(self.result_canvas_window, width=e.width))
        
        # === 底部日志区域 ===
        log_frame = ttk.LabelFrame(main_frame, text="日志", padding="5")
        log_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        log_frame.columnconfigure(0, weight=1)
        
        self.log_text = tk.Text(log_frame, height=3, wrap=tk.WORD, font=('Consolas', 9))
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        log_scroll = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        log_scroll.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.log_text['yscrollcommand'] = log_scroll.set
        
    def _init_result_display(self):
        """初始化结果显示区域"""
        # 清空现有内容
        for widget in self.result_frame.winfo_children():
            widget.destroy()
        
        # 添加提示文字
        ttk.Label(self.result_frame, text="等待识别...", 
                 font=('Microsoft YaHei', 14), foreground='gray').pack(pady=50)
        
        # 更新canvas滚动区域
        self.result_frame.update_idletasks()
        self.result_canvas.configure(scrollregion=self.result_canvas.bbox('all'))
    
    def _display_results(self, matches, query_text):
        """显示匹配结果 - 简洁列表格式，最多20条"""
        # 清空现有内容
        for widget in self.result_frame.winfo_children():
            widget.destroy()
        
        # 创建主容器
        main_container = ttk.Frame(self.result_frame)
        main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 显示识别到的文本
        ttk.Label(main_container, text="识别文本:", 
                 font=('Microsoft YaHei', 9), foreground='gray').pack(anchor=tk.W)
        query_label = ttk.Label(main_container, text=query_text or "未识别到文字",
                               font=('Microsoft YaHei', 11, 'bold'), wraplength=550)
        query_label.pack(anchor=tk.W, pady=(2, 10))
        
        # 分隔线
        ttk.Separator(main_container, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)
        
        # 显示匹配结果 - 使用Text控件支持高亮
        if matches:
            # 限制最多20条
            matches = matches[:20]
            
            ttk.Label(main_container, text=f"匹配到 {len(matches)} 个结果:", 
                     font=('Microsoft YaHei', 9), foreground='gray').pack(anchor=tk.W, pady=(0, 5))
            
            # 创建Text控件显示结果
            result_text = tk.Text(main_container, wrap=tk.WORD, font=('Microsoft YaHei', 11),
                                 height=28, bg='white', padx=5, pady=5)
            result_text.pack(fill=tk.BOTH, expand=True)
            
            # 添加滚动条
            scrollbar = ttk.Scrollbar(main_container, orient=tk.VERTICAL, command=result_text.yview)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            result_text.configure(yscrollcommand=scrollbar.set)
            
            # 配置标签样式
            result_text.tag_configure('highlight', background='#ffeb3b')  # 黄色高亮
            result_text.tag_configure('number', foreground='#666666')
            result_text.tag_configure('question_label', foreground='#333333')
            result_text.tag_configure('question_text', foreground='#000000')
            result_text.tag_configure('answer_label', foreground='#666666')
            result_text.tag_configure('answer_text', foreground='#2196F3', font=('Microsoft YaHei', 11, 'bold'))
            
            # 获取查询文本用于高亮匹配
            query_text_for_match = query_text if query_text else ""
            
            def find_all_matches(text, query):
                """找到文本中所有匹配的子串位置"""
                if not query or not text:
                    return []
                matches = []
                text_lower = text.lower()
                query_lower = query.lower()
                
                # 尝试不同长度的子串匹配
                for length in range(len(query_lower), 1, -1):
                    for i in range(len(query_lower) - length + 1):
                        sub = query_lower[i:i+length]
                        if sub in text_lower:
                            # 找到所有出现位置
                            start = 0
                            while True:
                                idx = text_lower.find(sub, start)
                                if idx == -1:
                                    break
                                matches.append((idx, idx + length))
                                start = idx + 1
                
                # 去重并排序
                matches = list(set(matches))
                matches.sort()
                
                # 合并重叠的匹配
                if matches:
                    merged = [matches[0]]
                    for current in matches[1:]:
                        last = merged[-1]
                        if current[0] <= last[1]:
                            merged[-1] = (last[0], max(last[1], current[1]))
                        else:
                            merged.append(current)
                    return merged
                return []
            
            for i, match_item in enumerate(matches, 1):
                question = match_item.get('question', '未知问题')
                answer = match_item.get('answer', '未知答案')
                
                # 获取当前插入位置
                start_idx = result_text.index("insert")
                
                # 插入序号
                result_text.insert("insert", f"{i}.", 'number')
                
                # 找到问题中的匹配位置
                q_matches = find_all_matches(question, query_text_for_match)
                q_insert_idx = result_text.index("insert")
                
                # 插入"问题："
                result_text.insert("insert", "问题：", 'question_label')
                
                # 插入问题文本，带高亮
                last_end = 0
                for m_start, m_end in q_matches:
                    # 插入匹配前的文本
                    if m_start > last_end:
                        result_text.insert("insert", question[last_end:m_start], 'question_text')
                    # 插入高亮文本
                    result_text.insert("insert", question[m_start:m_end], ('question_text', 'highlight'))
                    last_end = m_end
                # 插入剩余文本
                if last_end < len(question):
                    result_text.insert("insert", question[last_end:], 'question_text')
                if not q_matches:
                    result_text.insert("insert", question, 'question_text')
                
                # 插入分隔
                result_text.insert("insert", "  ", 'question_text')
                
                # 找到答案中的匹配位置
                a_matches = find_all_matches(answer, query_text_for_match)
                
                # 插入"答案："
                result_text.insert("insert", "答案：", 'answer_label')
                
                # 插入答案文本，带高亮
                if a_matches:
                    last_end = 0
                    for m_start, m_end in a_matches:
                        # 插入匹配前的文本
                        if m_start > last_end:
                            result_text.insert("insert", answer[last_end:m_start], 'answer_text')
                        # 插入高亮文本
                        result_text.insert("insert", answer[m_start:m_end], ('answer_text', 'highlight'))
                        last_end = m_end
                    # 插入剩余文本
                    if last_end < len(answer):
                        result_text.insert("insert", answer[last_end:], 'answer_text')
                else:
                    # 没有匹配，直接插入全部
                    result_text.insert("insert", answer, 'answer_text')
                
                # 插入换行
                result_text.insert("insert", "\n\n", 'question_text')
            
            result_text.configure(state=tk.DISABLED)  # 设为只读
        else:
            # 未找到匹配
            ttk.Label(main_container, text="❌ 未找到匹配的答案", 
                     font=('Microsoft YaHei', 14, 'bold'), foreground='red').pack(pady=30)
            ttk.Label(main_container, text="请检查题库是否包含该题目",
                     font=('Microsoft YaHei', 10), foreground='gray').pack()
        
        # 更新canvas滚动区域
        self.result_frame.update_idletasks()
        self.result_canvas.configure(scrollregion=self.result_canvas.bbox('all'))
        
    def _init_components(self):
        """初始化OCR等组件"""
        try:
            from ocr_engine import OCREngine
            self.ocr_engine = OCREngine()
            self._log("OCR引擎初始化成功")
        except Exception as e:
            self._log(f"OCR引擎初始化失败: {e}", error=True)
            messagebox.showerror("错误", f"OCR引擎初始化失败:\n{e}\n\n请确保已安装依赖: pip install -r requirements.txt")
        
        # 尝试恢复之前的题库配置
        try:
            from question_bank_loader import QuestionBankLoader
            from question_matcher import QuestionMatcher
            
            # 初始化加载器（会自动连接SQLite数据库）
            self.loader = QuestionBankLoader()
            questions = self.loader.get_questions()
            
            if questions:
                self.question_matcher = QuestionMatcher(questions)
                self._update_bank_status()
                self._log(f"自动恢复题库: 共 {len(questions)} 道题目，来自 {len(self.loader.loaded_files)} 个文件")
            else:
                self._log("题库为空，请加载题库文件")
                
        except Exception as e:
            self._log(f"题库恢复失败: {e}", error=True)
    
    def _log(self, message, error=False):
        """添加日志"""
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        prefix = "[错误]" if error else "[信息]"
        self.log_text.insert(tk.END, f"{timestamp} {prefix} {message}\n")
        self.log_text.see(tk.END)
    
    def _browse_file(self):
        """浏览文件"""
        file_path = filedialog.askopenfilename(
            title="选择题库文件",
            filetypes=[("Excel文件", "*.xlsx *.xls"), ("所有文件", "*.*")]
        )
        if file_path:
            self.file_path_var.set(file_path)
    
    def _load_question_bank(self):
        """加载题库（增量模式）"""
        try:
            from question_bank_loader import QuestionBankLoader
            from question_matcher import QuestionMatcher
            
            file_path = self.file_path_var.get()
            
            # 如果没有初始化loader，创建新的
            if not self.loader:
                self.loader = QuestionBankLoader()
            
            # 增量加载
            result = self.loader.load_from_excel(file_path, append=True)
            
            if result['success']:
                # 更新匹配器
                questions = self.loader.get_questions()
                self.question_matcher = QuestionMatcher(questions)
                
                # 更新状态显示
                self._update_bank_status()
                
                # 显示加载结果
                msg = f"题库加载成功！\n\n" \
                      f"本次新增: {result['added']} 道\n" \
                      f"重复跳过: {result['duplicates']} 道\n" \
                      f"题库总数: {result['total']} 道\n\n" \
                      f"数据已保存到 SQLite 数据库"
                self._log(f"题库加载成功: 新增{result['added']}道, 重复{result['duplicates']}道, 共{result['total']}道")
                messagebox.showinfo("成功", msg)
            else:
                self._log("题库加载失败或文件不存在", error=True)
                messagebox.showwarning("警告", "题库加载失败或文件不存在")
                
        except Exception as e:
            self._log(f"加载题库失败: {e}", error=True)
            messagebox.showerror("错误", f"加载题库失败:\n{e}")
    
    def _clear_question_bank(self):
        """清空题库"""
        try:
            if not self.loader or self.loader.get_question_count() == 0:
                messagebox.showinfo("提示", "题库已经是空的")
                return
            
            # 确认对话框
            if messagebox.askyesno("确认", f"确定要清空题库吗？\n当前共有 {self.loader.get_question_count()} 道题目"):
                count = self.loader.clear_bank()
                self.question_matcher = None
                self._update_bank_status()
                self._log(f"题库已清空（SQLite），共移除 {count} 道题目")
                messagebox.showinfo("成功", f"题库已清空\n共移除 {count} 道题目")
                
        except Exception as e:
            self._log(f"清空题库失败: {e}", error=True)
            messagebox.showerror("错误", f"清空题库失败:\n{e}")
    
    def _update_bank_status(self):
        """更新题库状态显示"""
        if self.loader:
            question_count = self.loader.get_question_count()
            file_count = len(self.loader.loaded_files)
            self.bank_status_var.set(f"当前题库: {question_count} 道题目")
            self.files_status_var.set(f"已加载文件: {file_count} 个")
        else:
            self.bank_status_var.set("当前题库: 0 道题目")
            self.files_status_var.set("已加载文件: 0 个")
    
    def _select_region(self):
        """选择识别区域"""
        try:
            from screen_capture import RegionSelector
            
            # 保存当前窗口几何信息
            current_geometry = self.root.geometry()
            
            self._log("请框选游戏右上角的题目区域...")
            self._log("提示：拖动鼠标框选区域，区域要大于3x3像素")
            
            # 创建区域选择器，使用主窗口作为parent（不创建新Tk实例）
            selector = RegionSelector(parent=self.root)
            region = selector.select_region()
            
            # 强制恢复窗口几何信息（包括位置和大小）
            self.root.geometry(current_geometry)
            self.root.update_idletasks()
            
            if region:
                self.capture_region = region
                x, y, w, h = region
                self.region_var.set(f"X:{x} Y:{y} W:{w} H:{h}")
                self._log(f"区域设置成功: ({x}, {y}, {w}, {h})")
                # 创建遮罩
                self._create_overlay()
            else:
                self._log("区域选择已取消或区域太小")
                self._log("请确保拖动鼠标形成一个矩形区域")
                
        except Exception as e:
            self._log(f"选择区域失败: {e}", error=True)
            import traceback
            self._log(traceback.format_exc(), error=True)
    
    def _clear_region(self):
        """清除选区"""
        if self.capture_region:
            # 先停止当前识别任务
            if self.is_running:
                self._stop_capture()
            self.capture_region = None
            self.region_var.set("未设置")
            self._remove_overlay()
            self._log("识别区域已清除")
        else:
            self._log("当前没有设置识别区域")
    
    def _test_capture(self):
        """测试识别"""
        if not self.capture_region:
            messagebox.showwarning("警告", "请先设置识别区域")
            return
            
        if not self.ocr_engine:
            messagebox.showerror("错误", "OCR引擎未初始化")
            return
            
        if not self.question_matcher:
            messagebox.showwarning("警告", "请先加载题库")
            return
        
        try:
            from screen_capture import ScreenCapture
            
            self._log("正在测试识别...")
            self.status_var.set("正在识别...")
            
            # 截图
            x, y, w, h = self.capture_region
            self._log(f"截图区域: X:{x} Y:{y} W:{w} H:{h}")
            
            screenshot = ScreenCapture.capture_region(x, y, w, h)
            
            # 检查截图是否成功
            if screenshot is None:
                self._log("截图失败: 返回None", error=True)
                self.status_var.set("截图失败")
                return
            
            self._log(f"截图成功: {screenshot.size}, 模式: {screenshot.mode}")
            
            # 保存调试截图
            try:
                debug_path = "debug_capture.png"
                screenshot.save(debug_path)
                self._log(f"调试截图已保存: {debug_path}")
            except Exception as e:
                self._log(f"保存调试截图失败: {e}")
            
            # OCR识别
            text = self.ocr_engine.recognize_text_only(screenshot)
            self.last_capture_var.set(f"识别文本: {text[:50]}..." if len(text) > 50 else f"识别文本: {text}")
            
            if text and text.strip():
                self._log(f"识别结果: {text}")
                
                # 匹配题库
                matches = self.question_matcher.find_matches(
                    text, 
                    top_k=self.results_var.get(),
                    threshold=20
                )
                
                # 显示结果
                self._display_results(matches, text)
            else:
                self._log("未识别到文字（识别结果为空）", error=True)
                # 显示未识别到的提示
                for widget in self.result_frame.winfo_children():
                    widget.destroy()
                
                no_text_frame = ttk.Frame(self.result_frame)
                no_text_frame.pack(pady=30)
                
                ttk.Label(no_text_frame, text="❌ 未识别到文字", 
                         font=('Microsoft YaHei', 14, 'bold'), foreground='red').pack()
                ttk.Label(no_text_frame, text="请检查：\n1. 识别区域是否包含文字\n2. 文字是否清晰\n3. 截图是否成功",
                         font=('Microsoft YaHei', 10), foreground='gray').pack(pady=10)
                
                # 更新canvas滚动区域
                self.result_frame.update_idletasks()
                self.result_canvas.configure(scrollregion=self.result_canvas.bbox('all'))
                
            self.status_var.set("测试完成")
            
        except Exception as e:
            self._log(f"测试识别失败: {e}", error=True)
            import traceback
            self._log(traceback.format_exc(), error=True)
            self.status_var.set("测试失败")
    
    def _start_capture(self):
        """开始定时识别"""
        if not self.capture_region:
            messagebox.showwarning("警告", "请先设置识别区域")
            return
            
        if not self.ocr_engine:
            messagebox.showerror("错误", "OCR引擎未初始化")
            return
            
        if not self.question_matcher:
            messagebox.showwarning("警告", "请先加载题库")
            return
        
        self.is_running = True
        self.interval = self.interval_var.get()
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.status_var.set("正在运行...")
        self._log(f"开始识别，间隔 {self.interval} 秒")
        
        # 启动识别循环（在主线程中通过after定时执行）
        self._capture_loop()
    
    def _stop_capture(self):
        """停止定时识别"""
        self.is_running = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.status_var.set("已停止")
        self._log("识别已停止")
    
    def _capture_loop(self):
        """识别循环 - 在主线程中执行OCR以避免多线程问题"""
        from screen_capture import ScreenCapture
        
        if not self.is_running:
            return
        
        # 每次循环都重新读取最新的间隔设置
        self.interval = self.interval_var.get()
        
        try:
            # 截图（可以在后台线程中执行）
            x, y, w, h = self.capture_region
            screenshot = ScreenCapture.capture_region(x, y, w, h)
            
            if screenshot is None:
                self._log("截图失败: 返回None", error=True)
                # 安排下一次识别
                self.root.after(int(self.interval * 1000), self._capture_loop)
                return
            
            # 在主线程中执行OCR识别（避免多线程问题）
            self._perform_ocr_and_match(screenshot)
            
            # 安排下一次识别
            if self.is_running:
                self.root.after(int(self.interval * 1000), self._capture_loop)
                
        except Exception as e:
            import traceback
            error_msg = f"识别循环错误: {str(e)}\n{traceback.format_exc()}"
            self._log(error_msg, error=True)
            # 发生错误时也继续
            if self.is_running:
                self.root.after(int(self.interval * 1000), self._capture_loop)
    
    def _perform_ocr_and_match(self, screenshot):
        """执行OCR识别和匹配（在主线程中运行）"""
        try:
            # OCR识别
            text = self.ocr_engine.recognize_text_only(screenshot)
            
            if text:
                self.last_capture_var.set(
                    f"识别文本: {text[:50]}..." if len(text) > 50 else f"识别文本: {text}"
                )
                self._log(f"识别到文字: {text}")
                
                # 匹配题库
                if self.question_matcher:
                    matches = self.question_matcher.find_matches(
                        text,
                        top_k=self.results_var.get(),
                        threshold=10  # 降低阈值到10，显示更多结果
                    )
                    # 显示结果
                    self._display_results(matches, text)
            else:
                self._log("未识别到文字", error=True)
                
        except Exception as e:
            import traceback
            self._log(f"OCR识别失败: {str(e)}\n{traceback.format_exc()}", error=True)
    
    def _create_sample(self):
        """创建示例题库"""
        try:
            from question_bank_loader import create_sample_question_bank
            file_path = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel文件", "*.xlsx")],
                initialfile="sample_questions.xlsx"
            )
            if file_path:
                create_sample_question_bank(file_path)
                self.file_path_var.set(file_path)
                self._log(f"示例题库已创建: {file_path}")
                self._log("提示：加载Excel后，题目会自动保存到SQLite数据库")
                messagebox.showinfo("成功", f"示例题库已创建:\n{file_path}\n\n加载后题目将自动存入SQLite数据库")
        except Exception as e:
            self._log(f"创建示例题库失败: {e}", error=True)
    
    def _export_bank(self):
        """导出题库到Excel"""
        try:
            if not self.loader or self.loader.get_question_count() == 0:
                messagebox.showinfo("提示", "题库为空，无需导出")
                return
            
            file_path = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel文件", "*.xlsx")],
                initialfile="question_backup.xlsx"
            )
            if file_path:
                success = self.loader.export_to_excel(file_path)
                if success:
                    self._log(f"题库已导出: {file_path}")
                    messagebox.showinfo("成功", f"题库已导出:\n{file_path}")
                else:
                    messagebox.showwarning("警告", "导出失败")
        except Exception as e:
            self._log(f"导出题库失败: {e}", error=True)
            messagebox.showerror("错误", f"导出题库失败:\n{e}")
    
    def _create_overlay(self):
        """创建识别区域遮罩 - 使用虚线边框标记，避免被OCR识别"""
        # 先移除已有的遮罩
        self._remove_overlay()
        
        if not self.capture_region:
            return
        
        try:
            x, y, w, h = self.capture_region
            
            # 创建遮罩窗口（稍大于实际区域，显示边框）
            border_width = 2
            self.overlay_window = tk.Toplevel(self.root)
            self.overlay_window.overrideredirect(True)  # 无边框
            self.overlay_window.geometry(f"{w + border_width*2}x{h + border_width*2}+{x - border_width}+{y - border_width}")
            self.overlay_window.attributes('-topmost', True)  # 置顶
            self.overlay_window.attributes('-transparentcolor', 'white')  # 白色透明
            self.overlay_window.configure(bg='white')
            
            # 创建画布绘制虚线边框
            canvas = tk.Canvas(self.overlay_window, bg='white', highlightthickness=0)
            canvas.pack(fill=tk.BOTH, expand=True)
            
            # 绘制红色虚线边框（不填充内部）
            canvas.create_rectangle(
                border_width, border_width, 
                w + border_width, h + border_width,
                outline='red', width=3, dash=(5, 3)  # 虚线样式
            )
            
            # 在四角绘制小标记
            corner_size = 8
            # 左上角
            canvas.create_line(border_width, border_width, border_width + corner_size, border_width, fill='red', width=3)
            canvas.create_line(border_width, border_width, border_width, border_width + corner_size, fill='red', width=3)
            # 右上角
            canvas.create_line(w + border_width - corner_size, border_width, w + border_width, border_width, fill='red', width=3)
            canvas.create_line(w + border_width, border_width, w + border_width, border_width + corner_size, fill='red', width=3)
            # 左下角
            canvas.create_line(border_width, h + border_width - corner_size, border_width, h + border_width, fill='red', width=3)
            canvas.create_line(border_width, h + border_width, border_width + corner_size, h + border_width, fill='red', width=3)
            # 右下角
            canvas.create_line(w + border_width - corner_size, h + border_width, w + border_width, h + border_width, fill='red', width=3)
            canvas.create_line(w + border_width, h + border_width - corner_size, w + border_width, h + border_width, fill='red', width=3)
            
            self._log(f"遮罩已创建: ({x}, {y}, {w}, {h})")
        except Exception as e:
            self._log(f"创建遮罩失败: {e}", error=True)
    
    def _remove_overlay(self):
        """移除识别区域遮罩"""
        if self.overlay_window:
            try:
                self.overlay_window.destroy()
                self.overlay_window = None
                self._log("遮罩已移除")
            except:
                pass
    
    def _on_close(self):
        """软件关闭时的处理"""
        # 移除遮罩
        self._remove_overlay()
        # 停止识别
        if self.is_running:
            self.is_running = False
        # 关闭窗口
        self.root.destroy()


def main():
    """主函数"""
    root = tk.Tk()
    app = YYSAssistantGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
