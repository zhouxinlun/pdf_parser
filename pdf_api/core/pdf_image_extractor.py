#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
智能PDF图像提取器

能够自动识别PDF类型并使用最适合的方法提取图像
"""

import os
import sys
import uuid
from PIL import Image
import fitz  # PyMuPDF
import pdfplumber
from datetime import datetime
from .pdf_analyzer import PDFAnalyzer, PDFType

class PDFImageExtractor:
    """智能PDF图像提取器类"""
    
    def __init__(self, pdf_path, output_dir=None, min_size=100, 
                 filter_duplicates=True, filter_contained=True, 
                 overlap_threshold=0.8, force_mode=None, dpi=300,
                 filter_text=False):
        """
        初始化PDF图像提取器
        
        参数:
            pdf_path (str): PDF文件路径
            output_dir (str): 输出目录路径，默认为当前目录下的"pdf_images_<时间戳>"
            min_size (int): 最小图像尺寸（像素），小于此尺寸的图像将被忽略
            filter_duplicates (bool): 是否过滤重复图像
            filter_contained (bool): 是否过滤被其他图像包含的小图像
            overlap_threshold (float): 重叠面积比例阈值，范围0-1
            force_mode (str): 强制使用指定的提取模式，可选值：'vector', 'scanned', 'digital'
            dpi (int): 输出图像的DPI，默认为300
            filter_text (bool): 是否跳过只包含文字的页面或PDF，只输出包含图像的页面，默认为False
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF文件不存在: {pdf_path}")
        
        self.pdf_path = pdf_path
        self.min_size = min_size
        self.filter_duplicates = filter_duplicates
        self.filter_contained = filter_contained
        self.overlap_threshold = overlap_threshold
        self.force_mode = force_mode
        self.dpi = dpi
        self.filter_text = filter_text
        
        # 设置输出目录
        if output_dir is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = f"pdf_images_{timestamp}"
        
        self.output_dir = output_dir
        
        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 分析PDF类型
        self.analyzer = PDFAnalyzer(pdf_path)
        self.pdf_type = self.analyzer.get_pdf_type()
        
        # 如果指定了强制模式，覆盖自动检测的类型
        if self.force_mode:
            try:
                self.pdf_type = PDFType(self.force_mode)
            except ValueError:
                print(f"警告: 无效的强制模式 '{self.force_mode}'，使用自动检测的类型: {self.pdf_type.value}")
        
        # 存储提取结果
        self.extracted_images = []
    
    def get_pdf_info(self):
        """获取PDF基本信息"""
        return self.analyzer.get_summary()
    
    def _extract_vector_pdf(self):
        """
        提取矢量PDF (CAD或矢量图形) 的图像
        使用整页渲染方法
        """
        print(f"处理矢量PDF (CAD或矢量图形)，使用整页渲染模式...")
        
        # 导入专用CAD渲染器
        from .cad_pdf_renderer import render_cad_pdf
        
        # 检查是否是复杂的CAD PDF
        is_complex_cad = False
        
        # 基于矢量对象数量判断是否是复杂CAD图纸
        try:
            # 获取矢量对象数量
            doc_temp = fitz.open(self.pdf_path)
            page0 = doc_temp[0]
            vector_objects_count = len(page0.get_drawings())
            doc_temp.close()
            
            if vector_objects_count > 10000:
                is_complex_cad = True
                print(f"检测到复杂CAD图纸（包含 {vector_objects_count} 个矢量对象），将使用专用CAD渲染器...")
            else:
                print(f"检测到普通矢量PDF（包含 {vector_objects_count} 个矢量对象）")
        except Exception as e:
            print(f"检查矢量对象数量时出错: {e}")
        
        # 打开PDF文件
        doc = fitz.open(self.pdf_path)
        extracted_count = 0
        
        # 遍历所有页面
        for page_num in range(doc.page_count):
            print(f"处理第 {page_num + 1} 页...")
            
            try:
                # 如果启用了跳过只包含文字的页面
                if self.filter_text:
                    # 获取页面
                    page = doc[page_num]
                    
                    # 检查是否是纯文本页面
                    # 对于矢量PDF，我们不进行过滤，因为它们是图纸类型
                    if self.pdf_type != PDFType.VECTOR:
                        # 检查页面上的图像对象
                        images = page.get_images()
                        
                        # 检查页面上的矢量图形
                        drawings = page.get_drawings()
                        
                        # 获取页面上的文本
                        text = page.get_text()
                        
                        # 如果页面上没有图像对象，且矢量图形很少，但有大量文本，则认为是纯文本页面
                        if len(images) == 0 and len(drawings) < 20 and len(text) > 500:
                            print(f"  第 {page_num + 1} 页上只有文本，无图像对象，跳过该页")
                            continue
                
                # 初始化页面渲染对象
                page_for_render = None
                
                # 选择渲染方法：对于复杂CAD PDF使用专用渲染器，否则使用标准渲染
                if is_complex_cad:
                    # 使用专用CAD渲染器
                    output_filename = f"page_{page_num + 1}.png"
                    output_path = os.path.join(self.output_dir, output_filename)
                    
                    # 渲染CAD PDF
                    render_result = render_cad_pdf(self.pdf_path, self.output_dir, page_num, self.dpi)
                    
                    # 记录提取的图像信息
                    image_info = {
                        "page": page_num + 1,
                        "image_index": 1,
                        "width": render_result["width"],
                        "height": render_result["height"],
                        "dpi": self.dpi,
                        "file_path": render_result["file_path"],
                        "file_name": output_filename,
                        "extraction_method": "cad_render",
                        "text_filtered": self.filter_text
                    }
                    
                    self.extracted_images.append(image_info)
                    print(f"已提取第 {page_num + 1} 页到 {output_path}")
                    extracted_count += 1
                
                # 对于非复杂CAD PDF，使用标准渲染
                else:
                    # 获取页面
                    page = doc[page_num]
                    
                    # 计算缩放因子 (DPI / 72，因为PDF的默认DPI是72)
                    zoom_factor = self.dpi / 72
                    
                    # 创建一个矩阵来应用缩放
                    mat = fitz.Matrix(zoom_factor, zoom_factor)
                    
                    # 定义默认的页面渲染对象
                    page_for_render = page
                    
                    try:
                        # 如果需要过滤文字内容
                        if self.filter_text:
                            # 获取页面上的所有文本区域
                            text_areas = []
                            text_page = page.get_textpage()
                            blocks = text_page.extractBLOCKS()
                            
                            # 收集所有文本块的区域
                            for block in blocks:
                                if block[6] == 0:  # 文本块
                                    x0, y0, x1, y1 = block[:4]
                                    text_areas.append((x0, y0, x1, y1))
                            
                            if text_areas:
                                print(f"  过滤第 {page_num + 1} 页上的 {len(text_areas)} 个文本区域")
                                
                                # 创建一个新页面，不包含文本
                                temp_doc = fitz.open()
                                temp_page = temp_doc.new_page(width=page.rect.width, height=page.rect.height)
                                
                                # 复制所有非文本内容
                                # 复制图像
                                for img in page.get_images(full=True):
                                    xref = img[0]
                                    temp_page.insert_image(page.rect, xref=xref)
                                
                                # 复制矢量图形（线条、曲线、矩形等）
                                # 注意：这是一个简化的方法，可能不会复制所有矢量内容
                                shapes = page.get_drawings()
                                for shape in shapes:
                                    # 使用shape信息在新页面上绘制
                                    temp_page.draw_rect(shape["rect"])
                                
                                # 使用临时页面进行渲染
                                page_for_render = temp_page
                            else:
                                print(f"  第 {page_num + 1} 页上未找到文本区域")
                        else:
                            # 如果不需要过滤文字内容，直接使用原始页面
                            text_areas = []
                        
                        # 渲染页面为像素图
                        pix = page_for_render.get_pixmap(matrix=mat, alpha=False)
                        
                        # 构建输出文件路径
                        output_filename = f"page_{page_num + 1}.png"
                        output_path = os.path.join(self.output_dir, output_filename)
                        
                        # 保存图像
                        pix.save(output_path)
                        
                        # 记录提取的图像信息
                        image_info = {
                            "page": page_num + 1,
                            "image_index": 1,
                            "width": pix.width,
                            "height": pix.height,
                            "dpi": self.dpi,
                            "file_path": output_path,
                            "file_name": output_filename,
                            "extraction_method": "page_render",
                            "text_filtered": self.filter_text
                        }
                        
                        self.extracted_images.append(image_info)
                        print(f"已提取第 {page_num + 1} 页到 {output_path}")
                        extracted_count += 1
                    except Exception as e:
                        print(f"  警告: 渲染第{page_num + 1}页时出错: {e}")
                    
                    # 计算缩放因子 (DPI / 72，因为PDF的默认DPI是72)
                    zoom_factor = self.dpi / 72
                    
                    # 创建一个矩阵来应用缩放
                    mat = fitz.Matrix(zoom_factor, zoom_factor)
                    
                    # 渲染页面为像素图
                    pix = page.get_pixmap(matrix=mat, alpha=False)
                    
                    # 构建输出文件路径
                    output_filename = f"page_{page_num + 1}.png"
                    output_path = os.path.join(self.output_dir, output_filename)
                    
                    # 保存图像
                    pix.save(output_path)
                    
                    # 记录提取的图像信息
                    image_info = {
                        "page": page_num + 1,
                        "image_index": 1,
                        "width": pix.width,
                        "height": pix.height,
                        "dpi": self.dpi,
                        "file_path": output_path,
                        "file_name": output_filename,
                        "extraction_method": "page_render",
                        "text_filtered": self.filter_text
                    }
                    
                    self.extracted_images.append(image_info)
                    print(f"已提取第 {page_num + 1} 页到 {output_path}")
                    extracted_count += 1
                
            except Exception as e:
                print(f"  警告: 提取第{page_num + 1}页时出错: {e}")
        
        # 关闭文档
        doc.close()
        
        return extracted_count
    
    def _extract_scanned_pdf(self):
        """
        提取扫描PDF的图像
        使用整页渲染方法
        """
        print(f"处理扫描PDF，使用整页渲染模式...")
        
        # 打开PDF文件
        doc = fitz.open(self.pdf_path)
        extracted_count = 0
        
        # 遍历所有页面
        for page_num in range(doc.page_count):
            print(f"处理第 {page_num + 1} 页...")
            
            # 获取页面
            page = doc[page_num]
            
            # 计算缩放因子 (DPI / 72，因为PDF的默认DPI是72)
            zoom_factor = self.dpi / 72
            
            # 创建一个矩阵来应用缩放
            mat = fitz.Matrix(zoom_factor, zoom_factor)
            
            try:
                # 如果需要过滤文字内容
                if self.filter_text:
                    # 扫描PDF通常文字是已经内嵌在图像中的，但我们仍然可以尝试识别和过滤
                    # 获取页面上的所有文本区域
                    text_areas = []
                    text_page = page.get_textpage()
                    blocks = text_page.extractBLOCKS()
                    
                    # 收集所有文本块的区域
                    for block in blocks:
                        if block[6] == 0:  # 文本块
                            x0, y0, x1, y1 = block[:4]
                            text_areas.append((x0, y0, x1, y1))
                    
                    if text_areas:
                        print(f"  在扫描PDF中检测到 {len(text_areas)} 个文本区域，尝试过滤")
                        # 对于扫描PDF，我们可以尝试使用OCR或其他方法过滤文字
                        # 这里我们只是标记一下文本区域，实际处理可能需要更复杂的方法
                    else:
                        print(f"  第 {page_num + 1} 页上未找到文本区域，可能是纯图像扫描")
                
                # 渲染页面为像素图
                pix = page.get_pixmap(matrix=mat, alpha=False)
                
                # 构建输出文件路径
                output_filename = f"page_{page_num + 1}.png"
                output_path = os.path.join(self.output_dir, output_filename)
                
                # 保存图像
                pix.save(output_path)
                
                # 记录提取的图像信息
                image_info = {
                    "page": page_num + 1,
                    "image_index": 1,
                    "width": pix.width,
                    "height": pix.height,
                    "dpi": self.dpi,
                    "file_path": output_path,
                    "file_name": output_filename,
                    "extraction_method": "page_render",
                    "text_filtered": self.filter_text
                }
                
                self.extracted_images.append(image_info)
                
                print(f"已提取第 {page_num + 1} 页到 {output_path}")
                extracted_count += 1
                
            except Exception as e:
                print(f"  警告: 提取第{page_num + 1}页时出错: {e}")
        
        # 关闭文档
        doc.close()
        
        return extracted_count
    
    def _extract_digital_pdf(self):
        """
        提取数字PDF的图像
        使用图像对象提取方法
        """
        print(f"处理数字PDF，使用图像对象提取模式...")
        
        # 打开PDF文件
        with pdfplumber.open(self.pdf_path) as pdf:
            extracted_count = 0
            image_hashes = set()  # 用于检测重复图像
            
            # 遍历所有页面
            for page_num, page in enumerate(pdf.pages):
                print(f"处理第 {page_num + 1} 页...")
                
                # 获取页面上的所有图像
                images = page.images
                
                # 如果启用了跳过只包含文字的页面
                if self.filter_text:
                    # 检查是否有有效的图像（过滤掉边界框超出页面的图像）
                    valid_images = []
                    for img in images:
                        # 检查图像边界是否在页面内
                        if img["x0"] < 0 or img["top"] < 0 or img["x1"] > page.width or img["bottom"] > page.height:
                            continue
                        
                        # 检查图像尺寸是否足够大
                        if img["width"] * img["height"] < self.min_size * self.min_size:
                            continue
                        
                        valid_images.append(img)
                    
                    # 如果没有有效图像，跳过这一页
                    if len(valid_images) == 0:
                        print(f"  第 {page_num + 1} 页上未找到有效图像对象，跳过该页")
                        continue
                    
                    # 替换为有效图像列表
                    images = valid_images
                
                # 如果需要过滤重叠图像
                if self.filter_contained or self.overlap_threshold < 1.0:
                    images = self._filter_overlapping_images(images)
                
                # 如果过滤后没有图像，跳过这一页
                if len(images) == 0:
                    print(f"  第 {page_num + 1} 页上没有符合要求的图像，跳过该页")
                    continue
                
                # 提取每个图像
                page_extracted_count = 0
                for i, img in enumerate(images):
                    try:
                        # 获取图像尺寸
                        width = img["width"]
                        height = img["height"]
                        
                        # 检查图像边界是否在页面内
                        if img["x0"] < 0 or img["top"] < 0 or img["x1"] > page.width or img["bottom"] > page.height:
                            print(f"  警告: 第{page_num + 1}页第{i + 1}张图片边界超出页面范围，跳过")
                            continue
                        
                        # 提取图像
                        try:
                            image = page.crop((img["x0"], img["top"], img["x1"], img["bottom"]))
                        except Exception as crop_error:
                            print(f"  警告: 裁剪第{page_num + 1}页第{i + 1}张图片时出错: {crop_error}")
                            continue
                        
                        # 如果提取失败，跳过
                        if image is None:
                            print(f"  警告: 提取第{page_num + 1}页第{i + 1}张图片时出错: 提取结果为空")
                            continue
                        
                        # 转换为PIL图像
                        try:
                            pil_image = Image.frombytes("RGB", (image.width, image.height), image.original.tobytes())
                        except Exception as convert_error:
                            print(f"  警告: 转换第{page_num + 1}页第{i + 1}张图片时出错: {convert_error}")
                            continue
                        
                        # 如果需要过滤重复图像
                        if self.filter_duplicates:
                            # 计算图像哈希
                            image_hash = hash(pil_image.tobytes())
                            
                            # 如果是重复图像，跳过
                            if image_hash in image_hashes:
                                print(f"  警告: 第{page_num + 1}页第{i + 1}张图片与先前提取的图像重复，跳过")
                                continue
                            
                            # 添加到哈希集合
                            image_hashes.add(image_hash)
                        
                        # 构建输出文件路径
                        output_filename = f"page_{page_num + 1}_image_{i + 1}.png"
                        output_path = os.path.join(self.output_dir, output_filename)
                        
                        # 保存图像
                        pil_image.save(output_path)
                        
                        # 记录提取的图像信息
                        image_info = {
                            "page": page_num + 1,
                            "image_index": i + 1,
                            "width": width,
                            "height": height,
                            "x0": img["x0"],
                            "y0": img["top"],
                            "x1": img["x1"],
                            "y1": img["bottom"],
                            "file_path": output_path,
                            "file_name": output_filename,
                            "extraction_method": "object_extraction"
                        }
                        
                        self.extracted_images.append(image_info)
                        
                        print(f"  已提取第{page_num + 1}页第{i + 1}张图片到 {output_path}")
                        extracted_count += 1
                        page_extracted_count += 1
                        
                    except Exception as e:
                        print(f"  警告: 提取第{page_num + 1}页第{i + 1}张图片时出错: {e}")
                
                # 如果这一页没有成功提取任何图像，我们认为它是纯文本页
                if page_extracted_count == 0 and self.filter_text:
                    print(f"  第 {page_num + 1} 页没有成功提取到任何图像，将其视为纯文本页")
        
        return extracted_count
    
    def _is_overlap(self, box1, box2):
        """
        检查两个边界框是否重叠
        
        参数:
            box1: 第一个边界框 (x0, y0, x1, y1)
            box2: 第二个边界框 (x0, y0, x1, y1)
            
        返回:
            bool: 是否重叠
        """
        # 检查是否有重叠
        if box1[0] > box2[2] or box2[0] > box1[2]:  # 一个在另一个的右侧
            return False
        if box1[1] > box2[3] or box2[1] > box1[3]:  # 一个在另一个的下方
            return False
        return True
    
    def _calculate_overlap_area(self, box1, box2):
        """
        计算两个边界框的重叠面积
        
        参数:
            box1: 第一个边界框 (x0, y0, x1, y1)
            box2: 第二个边界框 (x0, y0, x1, y1)
            
        返回:
            float: 重叠面积占较小边界框的比例
        """
        if not self._is_overlap(box1, box2):
            return 0.0
        
        # 计算重叠区域
        x_overlap = max(0, min(box1[2], box2[2]) - max(box1[0], box2[0]))
        y_overlap = max(0, min(box1[3], box2[3]) - max(box1[1], box2[1]))
        overlap_area = x_overlap * y_overlap
        
        # 计算两个边界框的面积
        area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
        area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
        
        # 返回重叠面积占较小边界框的比例
        return overlap_area / min(area1, area2)
    
    def _is_contained(self, box1, box2):
        """
        检查边界框1是否被边界框2包含
        
        参数:
            box1: 第一个边界框 (x0, y0, x1, y1)
            box2: 第二个边界框 (x0, y0, x1, y1)
            
        返回:
            bool: 边界框1是否被边界框2包含
        """
        return (box1[0] >= box2[0] and box1[1] >= box2[1] and 
                box1[2] <= box2[2] and box1[3] <= box2[3])
    
    def _filter_overlapping_images(self, images):
        """
        过滤重叠的图像，保留最全面的图像
        
        参数:
            images: 图像列表，每个图像包含边界框信息
            
        返回:
            list: 过滤后的图像列表
        """
        if not images:
            return []
        
        # 按面积从大到小排序
        sorted_images = sorted(images, 
                              key=lambda img: (img["width"] * img["height"]), 
                              reverse=True)
        
        filtered_images = []
        for i, img1 in enumerate(sorted_images):
            box1 = (img1["x0"], img1["top"], img1["x1"], img1["bottom"])
            area1 = img1["width"] * img1["height"]
            
            # 如果面积太小，跳过
            if area1 < self.min_size * self.min_size:
                continue
            
            # 检查是否被之前添加的更大图像包含或严重重叠
            should_add = True
            for img2 in filtered_images:
                box2 = (img2["x0"], img2["top"], img2["x1"], img2["bottom"])
                
                # 如果启用了包含过滤，检查当前图像是否被已添加的图像包含
                if self.filter_contained and self._is_contained(box1, box2):
                    should_add = False
                    break
                
                # 检查重叠程度
                overlap_ratio = self._calculate_overlap_area(box1, box2)
                if overlap_ratio > self.overlap_threshold:
                    should_add = False
                    break
            
            if should_add:
                filtered_images.append(img1)
        
        return filtered_images
    
    def extract_images(self):
        """
        根据PDF类型提取图像
        
        返回:
            dict: 提取结果，包含提取的图像信息和PDF信息
        """
        print(f"\n开始提取PDF图像，PDF类型: {self.pdf_type.value}")
        
        extracted_count = 0
        
        # 对于文本PDF (test3.pdf)，如果启用了跳过选项，则不提取图像
        # 对于矢量PDF (test1.pdf) 和数字PDF (test2.pdf)，无论filter_text设置如何，都必须提取图像
        if self.filter_text and self.pdf_type == PDFType.TEXT:
                print(f"\n检查PDF是否包含图像...")
                has_images = False
                
                # 使用pdfplumber检查是否有图像
                pdfplumber_images_count = 0
                try:
                    pdf = pdfplumber.open(self.pdf_path)
                    for page_num in range(min(3, len(pdf.pages))):
                        page = pdf.pages[page_num]
                        images = page.images
                        pdfplumber_images_count += len(images)
                        if len(images) > 0:
                            print(f"  在第 {page_num+1} 页发现 {len(images)} 个图像对象 (pdfplumber)")
                            has_images = True
                            break
                    pdf.close()
                except Exception as e:
                    print(f"  pdfplumber检查图像时出错: {e}")
                
                # 使用PyMuPDF检查是否有图像
                pymupdf_images_count = 0
                if not has_images:
                    try:
                        doc = fitz.open(self.pdf_path)
                        for page_num in range(min(3, doc.page_count)):
                            page = doc[page_num]
                            images = page.get_images()
                            pymupdf_images_count += len(images)
                            if len(images) > 0:
                                print(f"  在第 {page_num+1} 页发现 {len(images)} 个图像对象 (PyMuPDF)")
                                has_images = True
                                break
                        doc.close()
                    except Exception as e:
                        print(f"  PyMuPDF检查图像时出错: {e}")
            
                print(f"  图像检测结果: pdfplumber={pdfplumber_images_count}, PyMuPDF={pymupdf_images_count}")
                
                # 如果没有图像且启用了跳过只有文字的PDF选项
                if not has_images:
                    print(f"\n本 PDF 文件不包含图像，由于启用了跳过只包含文字的PDF选项，因此不进行提取")
                    return {
                        "success": False,
                        "extracted_count": 0,
                        "pdf_info": self.analyzer.get_summary(),
                        "images": [],
                        "output_dir": os.path.abspath(self.output_dir),
                        "message": "本 PDF 文件不包含图像，由于启用了跳过只包含文字的PDF选项，因此不进行提取"
                    }
            
        extracted_count = 0
        
        try:
            # 根据PDF类型选择提取方法
            if self.pdf_type == PDFType.VECTOR:
                # 矢量PDF (test1.pdf) - 无论filter_text设置如何，都需要生成图像
                extracted_count = self._extract_vector_pdf()
            elif self.pdf_type == PDFType.SCANNED:
                extracted_count = self._extract_scanned_pdf()
            elif self.pdf_type == PDFType.DIGITAL:
                # 数字PDF (test5.pdf) - 如果启用了filter_text，需要检查是否实际包含图像
                if self.filter_text:
                    # 检查是否实际包含图像对象，而不是仅包含文字
                    has_real_images = False
                    try:
                        with pdfplumber.open(self.pdf_path) as pdf:
                            for page_num in range(min(3, len(pdf.pages))):
                                page = pdf.pages[page_num]
                                images = page.images
                                if len(images) > 0:
                                    print(f"  在第 {page_num+1} 页发现 {len(images)} 个图像对象，将提取图像")
                                    has_real_images = True
                                    break
                    except Exception as e:
                        print(f"  检查图像对象时出错: {e}")
                    
                    if not has_real_images:
                        print(f"  数字PDF中未发现实际图像对象，由于启用了跳过只包含文字的PDF选项，因此不进行提取")
                        return {
                            "success": False,
                            "extracted_count": 0,
                            "pdf_info": self.analyzer.get_summary(),
                            "images": [],
                            "output_dir": os.path.abspath(self.output_dir),
                            "message": "数字PDF中未发现实际图像对象，由于启用了跳过只包含文字的PDF选项，因此不进行提取"
                        }
                
                # 有实际图像或未启用filter_text，正常提取
                extracted_count = self._extract_digital_pdf()
            else:
                # 对于文本PDF (test3.pdf)，如果启用了跳过只包含文字的PDF选项，则不进行提取
                if self.filter_text:
                    print(f"检测到纯文本PDF，由于启用了跳过只包含文字的PDF选项，因此不进行提取")
                    return {
                        "success": False,
                        "extracted_count": 0,
                        "pdf_info": self.analyzer.get_summary(),
                        "images": [],
                        "output_dir": os.path.abspath(self.output_dir),
                        "message": "检测到纯文本PDF，由于启用了跳过只包含文字的PDF选项，因此不进行提取"
                    }
                else:
                    print(f"处理文本PDF，使用整页渲染模式...")
                    extracted_count = self._extract_vector_pdf()
            
            # 如果没有提取到图像，且没有启用跳过选项，才尝试备用方法
            if extracted_count == 0 and not self.filter_text:
                print("未找到图像，尝试使用备用方法...")
                
                # 只在需要时使用备用方法，避免重复提取
                if self.pdf_type == PDFType.DIGITAL and not hasattr(self, '_used_vector_method'):
                    print("尝试使用整页渲染模式...")
                    self._used_vector_method = True
                    # 直接使用下面的代码渲染，而不是调用_extract_vector_pdf
                    try:
                        # 打开PDF文件
                        doc = fitz.open(self.pdf_path)
                        
                        for page_num in range(doc.page_count):
                            print(f"备用渲染模式处理第 {page_num + 1} 页...")
                            
                            # 获取页面
                            page = doc[page_num]
                            
                            # 计算缩放因子 (DPI / 72，因为PDF的默认DPI是72)
                            zoom_factor = self.dpi / 72
                            
                            # 创建一个矩阵来应用缩放
                            mat = fitz.Matrix(zoom_factor, zoom_factor)
                            
                            # 渲染页面为像素图
                            pix = page.get_pixmap(matrix=mat, alpha=False)
                            
                            # 构建输出文件路径
                            output_filename = f"page_{page_num + 1}.png"
                            output_path = os.path.join(self.output_dir, output_filename)
                            
                            # 保存图像
                            pix.save(output_path)
                            
                            # 记录提取的图像信息
                            image_info = {
                                "page": page_num + 1,
                                "image_index": 1,
                                "width": pix.width,
                                "height": pix.height,
                                "dpi": self.dpi,
                                "file_path": output_path,
                                "file_name": output_filename,
                                "extraction_method": "backup_page_render",
                                "text_filtered": self.filter_text
                            }
                            
                            self.extracted_images.append(image_info)
                            print(f"已提取第 {page_num + 1} 页到 {output_path}")
                            extracted_count += 1
                        
                        # 关闭文档
                        doc.close()
                    except Exception as e:
                        print(f"  备用渲染模式出错: {e}")
                
                elif self.pdf_type != PDFType.DIGITAL and not hasattr(self, '_used_digital_method'):
                    print("尝试使用图像对象提取模式...")
                    self._used_digital_method = True
                    extracted_count = self._extract_digital_pdf()
        except Exception as e:
            print(f"提取过程中出错: {e}")
            extracted_count = 0
            # 异常情况下不再尝试备用方法，避免重复提取
        
        finally:
            # 关闭分析器
            self.analyzer.close()
        
        # 准备结果
        result = {
            "success": extracted_count > 0,
            "extracted_count": extracted_count,
            "pdf_info": self.analyzer.get_summary(),
            "images": self.extracted_images,
            "output_dir": os.path.abspath(self.output_dir)
        }
        
        # 打印结果
        if extracted_count == 0:
            print("\nPDF中未找到图像")
        else:
            print(f"\n提取完成！共提取 {extracted_count} 张图像")
            print(f"输出目录: {os.path.abspath(self.output_dir)}")
        
        return result
