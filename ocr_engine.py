"""
OCR引擎模块 - 使用 RapidOCR 进行本地文字识别
轻量级，易于打包
"""
import cv2
import numpy as np
from PIL import Image
import logging
import threading

# 禁用冗余日志
logging.getLogger("rapidocr").setLevel(logging.ERROR)


class OCREngine:
    """OCR引擎类，使用 RapidOCR 进行本地文字识别"""
    
    def __init__(self):
        """初始化 OCR 引擎"""
        self._lock = threading.Lock()
        
        try:
            from rapidocr_onnxruntime import RapidOCR
            
            print("[OCR] 正在初始化 RapidOCR...")
            # 使用轻量级模型
            self.ocr = RapidOCR(
                det_model_path=None,  # 使用默认模型
                cls_model_path=None,
                rec_model_path=None,
            )
            print("[OCR] RapidOCR 初始化成功")
            
        except Exception as e:
            raise RuntimeError(f"无法初始化 OCR 引擎: {e}")
    
    def recognize(self, image):
        """
        识别图片中的文字
        
        Args:
            image: PIL.Image 或 numpy.ndarray 或文件路径
            
        Returns:
            list: 识别结果列表，每项包含 {'text': 文字, 'confidence': 置信度}
        """
        # 统一转换为 numpy 数组
        if isinstance(image, Image.Image):
            image_array = np.array(image)
        elif isinstance(image, str):
            image_array = cv2.imread(image)
            if image_array is None:
                raise ValueError(f"无法读取图片: {image}")
            image_array = cv2.cvtColor(image_array, cv2.COLOR_BGR2RGB)
        else:
            image_array = image.copy()
        
        # 确保是 RGB 格式
        if len(image_array.shape) == 3 and image_array.shape[2] == 4:
            image_array = cv2.cvtColor(image_array, cv2.COLOR_RGBA2RGB)
        elif len(image_array.shape) == 2:
            image_array = cv2.cvtColor(image_array, cv2.COLOR_GRAY2RGB)
        
        # 执行 OCR 识别
        with self._lock:
            try:
                print(f"[OCR调试] 开始识别，图片尺寸: {image_array.shape}")
                
                # 如果图片太小，尝试放大
                h, w = image_array.shape[:2]
                if h < 100 or w < 100:
                    print(f"[OCR调试] 图片太小({h}x{w})，尝试放大...")
                    scale = max(2, int(200/min(h,w)))
                    image_array = cv2.resize(image_array, (w*scale, h*scale), interpolation=cv2.INTER_CUBIC)
                    print(f"[OCR调试] 放大后尺寸: {image_array.shape}")
                
                # RapidOCR 识别
                result, elapse = self.ocr(image_array)
                
                print(f"[OCR调试] 原始结果: {result}")
                
                texts = []
                if result:
                    for item in result:
                        # RapidOCR 返回格式: [bbox, text, confidence]
                        if len(item) >= 3:
                            bbox = item[0]
                            text = item[1]
                            confidence = item[2]
                            texts.append({
                                'text': text,
                                'confidence': confidence,
                                'bbox': bbox
                            })
                            print(f"[OCR调试] 识别到文字: {text}")
                
                print(f"[OCR调试] 最终识别到 {len(texts)} 个文本")
                return texts
                
            except Exception as e:
                print(f"[OCR错误] 识别失败: {e}")
                import traceback
                traceback.print_exc()
                return []
    
    def recognize_text_only(self, image):
        """
        仅返回识别的文字内容（合并所有文本）
        
        Args:
            image: 输入图片
            
        Returns:
            str: 合并后的文字
        """
        results = self.recognize(image)
        texts = [r['text'] for r in results if r.get('text')]
        return ' '.join(texts)
    
    def preprocess_image(self, image):
        """
        图像预处理，提高识别准确率
        
        Args:
            image: 输入图片
            
        Returns:
            numpy.ndarray: 处理后的图片
        """
        if isinstance(image, Image.Image):
            img = np.array(image)
        else:
            img = image.copy()
            
        # 转换为灰度图
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        else:
            gray = img
            
        # 自适应直方图均衡化
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        
        # 降噪
        denoised = cv2.fastNlMeansDenoising(enhanced, None, 10, 7, 21)
        
        # 二值化
        _, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        return binary
