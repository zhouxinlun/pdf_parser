#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
智能PDF图像提取器

能够自动识别PDF类型并使用最适合的方法提取图像
"""

import os
import sys
import argparse
import pdfplumber
from PIL import Image
import fitz  # PyMuPDF
import shutil
from datetime import datetime
from pdf_analyzer import PDFAnalyzer, PDFType

class PDFImageExtractor:
    """智能PDF图像提取器类"""
    
    def __init__(self, pdf_path, output_dir=None, min_size=100, 
                 filter_duplicates=True, filter_contained=True, 
                 overlap_threshold=0.8, force_mode=None, dpi=300):
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
        
        # 打印PDF信息
        self._print_pdf_info()
    
    def _print_pdf_info(self):
        """打印PDF基本信息"""
        summary = self.analyzer.get_summary()
        
        print("PDF信息:")
        print(f"  文件名: {summary['文件名']}")
        print(f"  页数: {summary['页数']}")
        print(f"  PDF类型: {summary['PDF类型']}")
        
        if "创建工具" in summary:
            print(f"  创建工具: {summary['创建工具']}")
        
        # 打印元数据
        metadata = self.analyzer.get_analysis_result()["元数据"]
        for key in ["Title", "Author", "Producer", "CreationDate", "ModDate"]:
            if key in metadata and metadata[key]:
                print(f"  {key}: {metadata[key]}")
    
    def _extract_vector_pdf(self):
        """
        提取矢量PDF (CAD或矢量图形) 的图像
        使用整页渲染方法
        """
        print(f"处理矢量PDF (CAD或矢量图形)，使用整页渲染模式...")
        
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
                # 渲染页面为像素图
                pix = page.get_pixmap(matrix=mat, alpha=False)
                
                # 构建输出文件路径
                output_path = os.path.join(self.output_dir, f"page_{page_num + 1}.png")
                
                # 保存图像
                pix.save(output_path)
                
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
                # 渲染页面为像素图
                pix = page.get_pixmap(matrix=mat, alpha=False)
                
                # 构建输出文件路径
                output_path = os.path.join(self.output_dir, f"page_{page_num + 1}.png")
                
                # 保存图像
                pix.save(output_path)
                
                print(f"已提取第 {page_num + 1} 页到 {output_path}")
                extracted_count += 1
                
            except Exception as e:
                print(f"  警告: 提取第{page_num + 1}页时出错: {e}")
        
        # 关闭文档
        doc.close()
        
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
                
                # 如果需要过滤重叠图像
                if self.filter_contained or self.overlap_threshold < 1.0:
                    images = self._filter_overlapping_images(images)
                
                # 提取每个图像
                for i, img in enumerate(images):
                    try:
                        # 获取图像尺寸
                        width = img["width"]
                        height = img["height"]
                        
                        # 如果图像太小，跳过
                        if width * height < self.min_size * self.min_size:
                            continue
                        
                        # 提取图像
                        image = page.crop((img["x0"], img["top"], img["x1"], img["bottom"]))
                        
                        # 如果提取失败，跳过
                        if image is None:
                            print(f"  警告: 提取第{page_num + 1}页第{i + 1}张图片时出错: 提取结果为空")
                            continue
                        
                        # 转换为PIL图像
                        pil_image = Image.frombytes("RGB", (image.width, image.height), image.original.tobytes())
                        
                        # 如果需要过滤重复图像
                        if self.filter_duplicates:
                            # 计算图像哈希
                            image_hash = hash(pil_image.tobytes())
                            
                            # 如果是重复图像，跳过
                            if image_hash in image_hashes:
                                continue
                            
                            # 添加到哈希集合
                            image_hashes.add(image_hash)
                        
                        # 构建输出文件路径
                        output_path = os.path.join(self.output_dir, f"page_{page_num + 1}_image_{i + 1}.png")
                        
                        # 保存图像
                        pil_image.save(output_path)
                        
                        print(f"  已提取第{page_num + 1}页第{i + 1}张图片到 {output_path}")
                        extracted_count += 1
                        
                    except Exception as e:
                        print(f"  警告: 提取第{page_num + 1}页第{i + 1}张图片时出错: {e}")
        
        return extracted_count
    
    def extract_images(self):
        """
        根据PDF类型提取图像
        
        返回:
            int: 提取的图像数量
        """
        extracted_count = 0
        
        try:
            # 根据PDF类型选择提取方法
            if self.pdf_type == PDFType.VECTOR:
                extracted_count = self._extract_vector_pdf()
            elif self.pdf_type == PDFType.SCANNED:
                extracted_count = self._extract_scanned_pdf()
            elif self.pdf_type == PDFType.DIGITAL:
                extracted_count = self._extract_digital_pdf()
            else:
                # 对于文本PDF，使用整页渲染方法
                print(f"处理文本PDF，使用整页渲染模式...")
                extracted_count = self._extract_vector_pdf()
            
            # 如果没有提取到图像，尝试使用另一种方法
            if extracted_count == 0:
                print("\n未找到图像，尝试使用备用方法...")
                
                if self.pdf_type == PDFType.DIGITAL:
                    print("尝试使用整页渲染模式...")
                    extracted_count = self._extract_vector_pdf()
                else:
                    print("尝试使用图像对象提取模式...")
                    extracted_count = self._extract_digital_pdf()
        
        finally:
            # 关闭分析器
            self.analyzer.close()
        
        # 如果仍然没有提取到图像，打印提示
        if extracted_count == 0:
            print("\nPDF中未找到图像")
            # 如果输出目录是空的，删除它
            if len(os.listdir(self.output_dir)) == 0:
                shutil.rmtree(self.output_dir)
        else:
            print(f"\n提取完成！共提取 {extracted_count} 张图像")
            print(f"输出目录: {os.path.abspath(self.output_dir)}")
        
        return extracted_count


def main():
    """命令行入口函数"""
    parser = argparse.ArgumentParser(description='智能PDF图像提取器')
    parser.add_argument('pdf_path', help='PDF文件路径')
    parser.add_argument('--output-dir', '-o', help='输出目录路径')
    parser.add_argument('--min-size', '-m', type=int, default=100, help='最小图像尺寸（像素）')
    parser.add_argument('--no-filter-duplicates', '-d', action='store_false', dest='filter_duplicates', 
                        help='不过滤重复图像')
    parser.add_argument('--no-filter-contained', '-c', action='store_false', dest='filter_contained', 
                        help='不过滤被包含的小图像')
    parser.add_argument('--overlap-threshold', '-t', type=float, default=0.8, 
                        help='重叠面积比例阈值（0-1之间）')
    parser.add_argument('--force-vector-mode', '-v', action='store_const', const='vector', dest='force_mode',
                        help='强制使用矢量PDF提取模式（整页渲染）')
    parser.add_argument('--force-scanned-mode', '-s', action='store_const', const='scanned', dest='force_mode',
                        help='强制使用扫描PDF提取模式（整页渲染）')
    parser.add_argument('--force-digital-mode', '-g', action='store_const', const='digital', dest='force_mode',
                        help='强制使用数字PDF提取模式（图像对象提取）')
    parser.add_argument('--dpi', '-p', type=int, default=300, help='输出图像的DPI（适用于整页渲染模式）')
    
    args = parser.parse_args()
    
    try:
        # 创建提取器
        extractor = PDFImageExtractor(
            pdf_path=args.pdf_path,
            output_dir=args.output_dir,
            min_size=args.min_size,
            filter_duplicates=args.filter_duplicates,
            filter_contained=args.filter_contained,
            overlap_threshold=args.overlap_threshold,
            force_mode=args.force_mode,
            dpi=args.dpi
        )
        
        # 提取图像
        extractor.extract_images()
        
    except Exception as e:
        print(f"错误: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
