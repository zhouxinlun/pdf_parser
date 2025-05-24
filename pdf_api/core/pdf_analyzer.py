#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PDF分析器

用于分析PDF文件的类型和结构
"""

import os
import pdfplumber
from enum import Enum

class PDFType(Enum):
    """PDF类型枚举"""
    VECTOR = "vector"  # 矢量PDF (CAD或矢量图形)
    SCANNED = "scanned"  # 扫描PDF (主要是图像)
    DIGITAL = "digital"  # 数字PDF (包含文本和图像)
    TEXT = "text"  # 文本PDF (主要是文本)

class PDFAnalyzer:
    """PDF分析器类，用于分析PDF文件类型和结构"""
    
    def __init__(self, pdf_path):
        """
        初始化PDF分析器
        
        参数:
            pdf_path (str): PDF文件路径
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF文件不存在: {pdf_path}")
            
        self.pdf_path = pdf_path
        self.pdf_type = None
        self.analysis_result = None
        
        # 打开PDF文件
        self.pdf = pdfplumber.open(pdf_path)
        
        # 获取基本信息
        self.page_count = len(self.pdf.pages)
        self.metadata = self.pdf.metadata or {}
        
        # 分析PDF类型
        self._analyze()
    
    def _analyze(self):
        """分析PDF文件类型和结构"""
        # 初始化分析结果
        self.analysis_result = {
            "file_name": os.path.basename(self.pdf_path),
            "file_path": self.pdf_path,
            "page_count": self.page_count,
            "metadata": self.metadata,
            "pages_info": [],
            "total_text_chars": 0,
            "total_images": 0,
            "total_vector_objects": 0,
            "total_curves": 0,
            "total_lines": 0,
            "total_rects": 0
        }
        
        # 分析前3页或所有页面（取较小值）
        pages_to_analyze = min(3, self.page_count)
        
        for i in range(pages_to_analyze):
            page = self.pdf.pages[i]
            
            # 获取页面文本
            text = page.extract_text() or ""
            text_chars = len(text)
            
            # 获取页面图像
            images = page.images
            image_count = len(images)
            
            # 获取矢量图形
            curves = page.curves
            curves_count = len(curves)
            
            lines = page.lines
            lines_count = len(lines)
            
            rects = page.rects
            rects_count = len(rects)
            
            vector_count = curves_count + lines_count + rects_count
            
            # 更新页面信息
            page_info = {
                "page_number": i + 1,
                "width": page.width,
                "height": page.height,
                "rotation": page.rotation,
                "text_chars": text_chars,
                "image_count": image_count,
                "vector_count": vector_count,
                "curves_count": curves_count,
                "lines_count": lines_count,
                "rects_count": rects_count
            }
            
            self.analysis_result["pages_info"].append(page_info)
            
            # 更新总计
            self.analysis_result["total_text_chars"] += text_chars
            self.analysis_result["total_images"] += image_count
            self.analysis_result["total_vector_objects"] += vector_count
            self.analysis_result["total_curves"] += curves_count
            self.analysis_result["total_lines"] += lines_count
            self.analysis_result["total_rects"] += rects_count
        
        # 确定PDF类型
        self._determine_pdf_type()
    
    def _determine_pdf_type(self):
        """根据分析结果确定PDF类型"""
        total_text = self.analysis_result["total_text_chars"]
        total_images = self.analysis_result["total_images"]
        total_vectors = self.analysis_result["total_vector_objects"]
        
        # 判断PDF类型
        if total_vectors > 1000:
            # 如果矢量图形数量很多，判断为矢量PDF (CAD)
            self.pdf_type = PDFType.VECTOR
        elif total_images > 0 and total_text < 100:
            # 如果有图像但几乎没有文本，判断为扫描PDF
            self.pdf_type = PDFType.SCANNED
        elif total_images > 0 and total_text > 100:
            # 如果有图像也有文本，判断为数字PDF
            self.pdf_type = PDFType.DIGITAL
        else:
            # 如果主要是文本，判断为文本PDF
            self.pdf_type = PDFType.TEXT
        
        # 添加到分析结果
        self.analysis_result["pdf_type"] = self.pdf_type.value
    
    def get_pdf_type(self):
        """获取PDF类型"""
        return self.pdf_type
    
    def get_analysis_result(self):
        """获取完整的分析结果"""
        return self.analysis_result
    
    def get_summary(self):
        """获取PDF分析摘要"""
        summary = {
            "file_name": self.analysis_result["file_name"],
            "page_count": self.analysis_result["page_count"],
            "pdf_type": self.analysis_result["pdf_type"],
            "total_text_chars": self.analysis_result["total_text_chars"],
            "total_images": self.analysis_result["total_images"],
            "total_vector_objects": self.analysis_result["total_vector_objects"]
        }
        
        # 添加创建工具信息（如果有）
        if "Creator" in self.metadata:
            summary["creator"] = self.metadata["Creator"]
        
        return summary
    
    def close(self):
        """关闭PDF文件"""
        if hasattr(self, 'pdf') and self.pdf:
            self.pdf.close()
    
    def __enter__(self):
        """支持with语句"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出with语句时关闭文档"""
        self.close()
