"""
屏幕截图模块 - 支持区域选择和截图
"""
import tkinter as tk
from tkinter import Toplevel, Canvas
import pyautogui
from PIL import Image, ImageGrab, ImageTk
import threading


class RegionSelector:
    """区域选择器类，用于框选截图区域"""
    
    def __init__(self, parent=None):
        self.selected_region = None
        self.selection_window = None
        self.parent = parent
        
    def select_region(self, callback=None):
        """
        打开区域选择窗口
        
        Args:
            callback: 选择完成后的回调函数，参数为 (x, y, width, height)
            
        Returns:
            tuple: (x, y, width, height) 或 None
        """
        self.selected_region = None
        self.callback = callback
        
        # 使用传入的parent或创建新的Tk
        if self.parent:
            self.root = self.parent
        else:
            self.root = tk.Tk()
            self.root.withdraw()
        
        # 使用pyautogui获取实际屏幕尺寸
        screen_width, screen_height = pyautogui.size()
        
        print(f"[调试] tkinter屏幕尺寸: {self.root.winfo_screenwidth()}x{self.root.winfo_screenheight()}")
        print(f"[调试] pyautogui屏幕尺寸: {screen_width}x{screen_height}")
        
        # 创建全屏透明窗口
        self.selection_window = Toplevel(self.root)
        
        # 设置为全屏覆盖整个屏幕
        self.selection_window.overrideredirect(True)  # 无边框
        self.selection_window.geometry(f"{screen_width}x{screen_height}+0+0")
        self.selection_window.attributes('-topmost', True)  # 置顶
        self.selection_window.attributes('-alpha', 0.3)  # 透明度
        self.selection_window.configure(bg='black')
        
        # 创建画布，覆盖整个屏幕（使用实际像素尺寸）
        self.canvas = Canvas(
            self.selection_window,
            width=screen_width,
            height=screen_height,
            highlightthickness=0,
            bg='black'
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # 添加提示文字
        self.canvas.create_text(
            screen_width // 2,
            screen_height // 2,
            text="请拖动鼠标框选识别区域\n按ESC取消",
            fill='white',
            font=('Microsoft YaHei', 24)
        )
        
        # 绑定事件
        self.canvas.bind('<Button-1>', self._on_mouse_down)
        self.canvas.bind('<B1-Motion>', self._on_mouse_drag)
        self.canvas.bind('<ButtonRelease-1>', self._on_mouse_up)
        self.selection_window.bind('<Escape>', self._on_escape)
        
        self.start_x = None
        self.start_y = None
        self.rect_id = None
        
        # 等待窗口关闭
        self.root.wait_window(self.selection_window)
        
        return self.selected_region
    
    def _on_mouse_down(self, event):
        """鼠标按下事件"""
        self.start_x = event.x
        self.start_y = event.y
        
        # 创建选择框
        if self.rect_id:
            self.canvas.delete(self.rect_id)
        self.rect_id = self.canvas.create_rectangle(
            self.start_x, self.start_y, self.start_x, self.start_y,
            outline='red', width=3
        )
    
    def _on_mouse_drag(self, event):
        """鼠标拖动事件"""
        if self.rect_id:
            self.canvas.coords(
                self.rect_id,
                self.start_x, self.start_y,
                event.x, event.y
            )
    
    def _on_mouse_up(self, event):
        """鼠标释放事件"""
        if self.start_x is None or self.start_y is None:
            return
            
        # 计算区域坐标
        start_x = self.start_x if self.start_x is not None else event.x
        start_y = self.start_y if self.start_y is not None else event.y
        
        x1 = min(start_x, event.x)
        y1 = min(start_y, event.y)
        x2 = max(start_x, event.x)
        y2 = max(start_y, event.y)
        
        width = x2 - x1
        height = y2 - y1
        
        print(f"[调试] 选择区域: x1={x1}, y1={y1}, x2={x2}, y2={y2}, width={width}, height={height}")
        
        # 确保区域有效（降低最小尺寸要求到3像素）
        if width > 3 and height > 3:
            self.selected_region = (x1, y1, width, height)
            print(f"[调试] 区域已保存: {self.selected_region}")
        else:
            print(f"[调试] 区域太小，被拒绝: {width}x{height}")
            
        self._close_window()
        
        if self.callback and self.selected_region:
            self.callback(self.selected_region)
    
    def _on_escape(self, event):
        """ESC键取消"""
        self._close_window()
    
    def _close_window(self):
        """关闭选择窗口"""
        if self.selection_window:
            self.selection_window.destroy()
        # 不要销毁root，因为可能是parent传入的


class ScreenCapture:
    """屏幕截图类"""
    
    @staticmethod
    def capture_fullscreen():
        """截取全屏"""
        screenshot = ImageGrab.grab()
        return screenshot
    
    @staticmethod
    def capture_region(x, y, width, height):
        """
        截取指定区域
        
        Args:
            x, y: 左上角坐标
            width, height: 宽度和高度
            
        Returns:
            PIL.Image: 截图
        """
        screenshot = ImageGrab.grab(bbox=(x, y, x + width, y + height))
        return screenshot
    
    @staticmethod
    def capture_window(window_title=None):
        """
        截取指定窗口（实验性功能，可能需要根据系统调整）
        
        Args:
            window_title: 窗口标题，如果为None则截取活动窗口
            
        Returns:
            PIL.Image or None: 截图
        """
        try:
            import win32gui
            import win32ui
            import win32con
            from ctypes import windll
            
            if window_title:
                hwnd = win32gui.FindWindow(None, window_title)
            else:
                hwnd = win32gui.GetForegroundWindow()
                
            if not hwnd:
                return None
                
            # 获取窗口DC
            hwndDC = win32gui.GetWindowDC(hwnd)
            mfcDC = win32ui.CreateDCFromHandle(hwndDC)
            saveDC = mfcDC.CreateCompatibleDC()
            
            # 获取窗口大小
            left, top, right, bot = win32gui.GetWindowRect(hwnd)
            width = right - left
            height = bot - top
            
            # 创建位图
            saveBitMap = win32ui.CreateBitmap()
            saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)
            saveDC.SelectObject(saveBitMap)
            
            # 截取窗口
            windll.user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), 2)
            
            # 转换为PIL Image
            bmpinfo = saveBitMap.GetInfo()
            bmpstr = saveBitMap.GetBitmapBits(True)
            im = Image.frombuffer(
                'RGB',
                (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
                bmpstr, 'raw', 'BGRX', 0, 1
            )
            
            # 清理
            win32gui.DeleteObject(saveBitMap.GetHandle())
            saveDC.DeleteDC()
            mfcDC.DeleteDC()
            win32gui.ReleaseDC(hwnd, hwndDC)
            
            return im
            
        except Exception as e:
            print(f"窗口截图失败: {e}")
            return None


if __name__ == "__main__":
    # 测试区域选择
    selector = RegionSelector()
    region = selector.select_region()
    print(f"选择的区域: {region}")
    
    if region:
        # 测试截图
        x, y, w, h = region
        img = ScreenCapture.capture_region(x, y, w, h)
        img.save("capture_test.png")
        print(f"截图已保存到 capture_test.png")
