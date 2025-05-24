#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
智能PDF图像提取器

自动检测PDF类型并选择最合适的图像提取方法
"""

import os
import sys
import argparse
import pdfplumber
import pypdfium2 as pdfium
from PIL import Image
from io import BytesIO
import hashlib
from collections import defaultdict

class SmartPDFExtractor:
    """智能PDF提取器，可自动检测PDF类型并选择合适的提取方法"""
    
    def __init__(self, pdf_path):
        """
        初始化智能PDF提取器
        
        参数:
            pdf_path (str): PDF文件路径
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF文件不存在: {pdf_path}")
            
        self.pdf_path = pdf_path
        self.pdf_type = None  # 'scanned' 或 'digital'
        
        # 打开PDF文件
        self.pdf_plumber = pdfplumber.open(pdf_path)
        self.pdf_pdfium = pdfium.PdfDocument(pdf_path)
        
        # 获取基本信息
        self.page_count = len(self.pdf_plumber.pages)
        
        # 分析PDF类型
        self._analyze_pdf_type()
    
    def _analyze_pdf_type(self):
        """分析PDF类型，判断是扫描PDF还是数字PDF"""
        # 初始化计数器
        text_pages = 0
        image_pages = 0
        
        # 分析前3页或所有页面（取较小值）
        pages_to_analyze = min(3, self.page_count)
        
        for i in range(pages_to_analyze):
            page = self.pdf_plumber.pages[i]
            
            # 获取页面文本
            text = page.extract_text() or ""
            
            # 获取页面图像
            images = page.images
            
            # 计算文本字符数和图像数量
            text_chars = len(text)
            image_count = len(images)
            
            # 判断页面类型
            if text_chars > 100:  # 如果页面包含大量文本
                text_pages += 1
            if image_count > 0:  # 如果页面包含图像
                image_pages += 1
        
        # 根据分析结果判断PDF类型
        if text_pages > 0 and text_pages >= image_pages:
            self.pdf_type = 'digital'  # 数字PDF（包含可选择的文本）
        else:
            self.pdf_type = 'scanned'  # 扫描PDF或主要是图像的PDF
    
    def get_pdf_type(self):
        """获取PDF类型"""
        return self.pdf_type
    
    def get_pdf_info(self):
        """获取PDF文件的基本信息"""
        info = {
            "文件名": os.path.basename(self.pdf_path),
            "页数": self.page_count,
            "PDF类型": "扫描PDF" if self.pdf_type == 'scanned' else "数字PDF",
        }
        
        # 尝试获取更多元数据
        try:
            metadata = self.pdf_plumber.metadata
            if metadata:
                for key, value in metadata.items():
                    if value:
                        info[key] = value
        except:
            pass
        
        return info
    
    def extract_images(self, output_dir, min_size=100, filter_duplicates=True, 
                      filter_contained=True, overlap_threshold=0.8):
        """
        提取PDF中的图像
        
        参数:
            output_dir (str): 输出目录
            min_size (int): 最小图像尺寸（像素）
            filter_duplicates (bool): 是否过滤重复图像
            filter_contained (bool): 是否过滤被包含的图像
            overlap_threshold (float): 重叠阈值
            
        返回:
            list: 提取的图像信息列表
        """
        # 确保输出目录存在
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # 根据PDF类型选择提取方法
        if self.pdf_type == 'scanned':
            print("检测到扫描PDF，使用整页提取模式...")
            return self._extract_pages_as_images(output_dir)
        else:
            print("检测到数字PDF，使用图像对象提取模式...")
            return self._extract_image_objects(output_dir, min_size, 
                                              filter_duplicates, filter_contained, 
                                              overlap_threshold)
    
    def _extract_pages_as_images(self, output_dir, dpi=300, format="png"):
        """将PDF页面作为图像提取（适用于扫描PDF）"""
        extracted_images = []
        
        # 遍历每一页
        for page_idx in range(self.page_count):
            print(f"处理第 {page_idx + 1} 页...")
            
            # 创建页面子目录
            page_dir = os.path.join(output_dir, f"page_{page_idx + 1}")
            os.makedirs(page_dir, exist_ok=True)
            
            # 获取页面
            pdf_page = self.pdf_pdfium[page_idx]
            
            # 计算缩放因子 (DPI / 72，因为PDF的默认DPI是72)
            scale = dpi / 72
            
            # 渲染页面为图像
            bitmap = pdf_page.render(scale=scale)
            
            # 转换为PIL图像
            pil_image = bitmap.to_pil()
            
            # 计算图像哈希值
            img_byte_arr = BytesIO()
            pil_image.save(img_byte_arr, format=format)
            image_bytes = img_byte_arr.getvalue()
            img_hash = hashlib.md5(image_bytes).hexdigest()
            
            # 构建输出文件名
            output_filename = f"page_{page_idx+1}_{img_hash[:8]}.{format.lower()}"
            output_path = os.path.join(page_dir, output_filename)
            
            # 保存图像
            pil_image.save(output_path)
            
            # 记录图像信息
            width, height = pil_image.size
            image_info = {
                "page_index": page_idx + 1,
                "width": width,
                "height": height,
                "format": format.upper(),
                "size_bytes": len(image_bytes),
                "hash": img_hash,
                "saved_path": output_path,
                "extraction_method": "page_render"
            }
            
            extracted_images.append(image_info)
            print(f"  保存页面图像: {output_filename}")
        
        return extracted_images
    
    def _extract_image_objects(self, output_dir, min_size=100, filter_duplicates=True, 
                              filter_contained=True, overlap_threshold=0.8):
        """提取PDF中的图像对象（适用于数字PDF）"""
        # 存储图像信息
        all_images = []
        
        # 用于检测重复图像的哈希集合
        image_hashes = set()
        
        # 用于存储每页的图像矩形信息，用于后处理过滤重叠图像
        page_rects = defaultdict(list)
        
        # 遍历PDF的每一页
        for page_index in range(self.page_count):
            print(f"处理第 {page_index + 1} 页...")
            
            # 获取页面
            page = self.pdf_plumber.pages[page_index]
            
            # 如果按页码分组，创建页面目录
            page_dir = os.path.join(output_dir, f"page_{page_index + 1}")
            os.makedirs(page_dir, exist_ok=True)
            
            # 存储当前页面的图像和坐标
            page_images = []
            
            # 遍历页面上的每个图片
            for img_index, img in enumerate(page.images):
                # 使用pypdfium2提取图片内容
                try:
                    # 获取图片位置信息
                    x0, y0, x1, y1 = img['x0'], img['top'], img['x1'], img['bottom']
                    width = int(x1 - x0)
                    height = int(y1 - y0)
                    
                    # 跳过太小的图像
                    if width * height < min_size:
                        continue
                    
                    # 使用pypdfium2从PDF中提取图片
                    pdf_page = self.pdf_pdfium[page_index]
                    try:
                        bitmap = pdf_page.render(
                            scale=1.0,
                            rotation=0,
                            crop=(x0, y0, x1, y1)
                        )
                        pil_image = bitmap.to_pil()
                    except Exception as e:
                        print(f"  警告: 提取第{page_index+1}页第{img_index+1}张图片时出错: {e}")
                        continue
                    
                    # 将图片转换为字节流以计算哈希值
                    img_byte_arr = BytesIO()
                    pil_image.save(img_byte_arr, format=pil_image.format or 'PNG')
                    image_bytes = img_byte_arr.getvalue()
                    
                    # 计算图片哈希值，用于唯一标识
                    img_hash = hashlib.md5(image_bytes).hexdigest()
                    
                    # 如果需要过滤重复图片且哈希值已存在，则跳过
                    if filter_duplicates and img_hash in image_hashes:
                        print(f"  跳过重复图片: 第{page_index+1}页第{img_index+1}张图片")
                        continue
                    
                    # 添加哈希值到集合
                    image_hashes.add(img_hash)
                    
                    # 确定图片格式
                    image_format = pil_image.format or 'PNG'
                    image_ext = image_format.lower()
                    
                    # 构建输出文件名
                    output_filename = f"img{img_index+1}_{img_hash[:8]}.{image_ext}"
                    output_path = os.path.join(page_dir, output_filename)
                    
                    # 保存图片
                    pil_image.save(output_path)
                    
                    # 收集图片信息
                    image_info = {
                        "page_index": page_index + 1,
                        "img_index": img_index + 1,
                        "width": width,
                        "height": height,
                        "format": image_ext.upper(),
                        "size_bytes": len(image_bytes),
                        "hash": img_hash,
                        "saved_path": output_path,
                        "x0": x0,
                        "y0": y0,
                        "x1": x1,
                        "y1": y1,
                        "extraction_method": "image_object"
                    }
                    
                    # 添加到结果列表
                    all_images.append(image_info)
                    
                    # 保存矩形信息用于后处理
                    page_rects[page_index].append({
                        "rect": (x0, y0, x1, y1),
                        "area": (x1 - x0) * (y1 - y0),
                        "index": len(all_images) - 1
                    })
                    
                    print(f"  提取图像: {output_filename}")
                    
                except Exception as e:
                    print(f"  警告: 处理第{page_index+1}页第{img_index+1}张图片时出错: {e}")
                    continue
        
        # 后处理：过滤重叠图像
        if filter_contained and overlap_threshold < 1.0 and all_images:
            # 存储要保留的图像索引
            indices_to_keep = set()
            
            # 按页面处理
            for page_idx, rects in page_rects.items():
                # 按面积从大到小排序
                sorted_rects = sorted(rects, key=lambda x: x["area"], reverse=True)
                
                # 处理每个矩形
                for i, rect1 in enumerate(sorted_rects):
                    # 如果已经决定保留这个图像，跳过进一步检查
                    if rect1["index"] in indices_to_keep:
                        continue
                        
                    # 默认保留这个图像
                    keep = True
                    
                    # 检查这个矩形是否与已保留的任何矩形有显著重叠
                    for kept_idx in indices_to_keep:
                        # 找到已保留矩形的信息
                        kept_rect_info = next((r for r in sorted_rects if r["index"] == kept_idx), None)
                        if not kept_rect_info:
                            continue
                            
                        # 获取两个矩形的坐标
                        x0_1, y0_1, x1_1, y1_1 = rect1["rect"]
                        x0_2, y0_2, x1_2, y1_2 = kept_rect_info["rect"]
                        
                        # 计算重叠区域
                        overlap_x0 = max(x0_1, x0_2)
                        overlap_y0 = max(y0_1, y0_2)
                        overlap_x1 = min(x1_1, x1_2)
                        overlap_y1 = min(y1_1, y1_2)
                        
                        # 检查是否有重叠
                        if overlap_x0 < overlap_x1 and overlap_y0 < overlap_y1:
                            # 计算重叠面积
                            overlap_area = (overlap_x1 - overlap_x0) * (overlap_y1 - overlap_y0)
                            
                            # 计算当前矩形的面积
                            rect1_area = rect1["area"]
                            
                            # 如果重叠面积占当前矩形的比例超过阈值，则不保留当前矩形
                            if overlap_area / rect1_area > overlap_threshold:
                                keep = False
                                break
                    
                    # 如果决定保留这个图像
                    if keep:
                        indices_to_keep.add(rect1["index"])
            
            # 只保留选定的图像
            filtered_images = [img for i, img in enumerate(all_images) if i in indices_to_keep]
            print(f"过滤后保留 {len(filtered_images)}/{len(all_images)} 张图像")
            all_images = filtered_images
        
        return all_images
    
    def print_summary(self, images):
        """打印提取图像的摘要信息"""
        if not images:
            print("\nPDF中未找到图像")
            return
        
        print(f"\n成功提取 {len(images)} 张图像")
        
        # 按页面统计
        pages_count = {}
        for img in images:
            page = img["page_index"]
            pages_count[page] = pages_count.get(page, 0) + 1
        
        print(f"包含图像的页面数: {len(pages_count)}")
        
        # 打印每页的图像数量
        print("\n每页图像数量:")
        for page, count in sorted(pages_count.items()):
            print(f"  - 第{page}页: {count}张图像")
        
        # 统计图像格式
        formats = {}
        for img in images:
            fmt = img["format"]
            formats[fmt] = formats.get(fmt, 0) + 1
        
        print("\n图像格式统计:")
        for fmt, count in formats.items():
            print(f"  - {fmt}: {count}张")
        
        # 统计图像尺寸分布
        sizes = {
            "小图 (<10KB)": 0,
            "中图 (10KB-100KB)": 0,
            "大图 (>100KB)": 0
        }
        
        for img in images:
            size_kb = img["size_bytes"] / 1024
            if size_kb < 10:
                sizes["小图 (<10KB)"] += 1
            elif size_kb < 100:
                sizes["中图 (10KB-100KB)"] += 1
            else:
                sizes["大图 (>100KB)"] += 1
        
        print("\n图像尺寸统计:")
        for size_cat, count in sizes.items():
            print(f"  - {size_cat}: {count}张")
        
        # 统计提取方法
        methods = {}
        for img in images:
            method = img.get("extraction_method", "未知")
            methods[method] = methods.get(method, 0) + 1
        
        print("\n提取方法统计:")
        for method, count in methods.items():
            method_name = "整页渲染" if method == "page_render" else "图像对象提取"
            print(f"  - {method_name}: {count}张")
        
        # 打印前5张图像的详细信息
        print("\n前5张图像的详细信息:")
        for i, img in enumerate(images[:5]):
            print(f"\n图像 #{i+1}:")
            print(f"  页码: {img['page_index']}")
            print(f"  尺寸: {img['width']}x{img['height']}像素")
            print(f"  格式: {img['format']}")
            print(f"  大小: {img['size_bytes']/1024:.2f} KB")
            if "saved_path" in img:
                print(f"  保存路径: {img['saved_path']}")
    
    def close(self):
        """关闭PDF文档"""
        if hasattr(self, 'pdf_plumber'):
            self.pdf_plumber.close()
        if hasattr(self, 'pdf_pdfium'):
            self.pdf_pdfium.close()
    
    def __enter__(self):
        """支持with语句"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出with语句时关闭文档"""
        self.close()


def main():
    """命令行入口函数"""
    parser = argparse.ArgumentParser(description='智能PDF图像提取器')
    parser.add_argument('pdf_path', help='PDF文件路径')
    parser.add_argument('--output-dir', '-o', help='输出目录', default='./extracted_images')
    parser.add_argument('--min-size', '-m', type=int, default=100, help='图像的最小像素数，默认为100')
    parser.add_argument('--no-filter-duplicates', '-d', action='store_true', help='不过滤重复图像')
    parser.add_argument('--no-filter-contained', '-c', action='store_true', help='不过滤被其他图像包含的小图像')
    parser.add_argument('--overlap-threshold', '-t', type=float, default=0.8, 
                        help='重叠面积比例阈值，默认为0.8，范围0-1之间')
    parser.add_argument('--force-page-mode', '-p', action='store_true', 
                        help='强制使用整页提取模式，忽略自动检测')
    parser.add_argument('--force-object-mode', '-b', action='store_true',
                        help='强制使用图像对象提取模式，忽略自动检测')
    
    args = parser.parse_args()
    
    try:
        # 创建智能PDF提取器
        extractor = SmartPDFExtractor(args.pdf_path)
        
        # 显示PDF信息
        pdf_info = extractor.get_pdf_info()
        print("PDF信息:")
        for key, value in pdf_info.items():
            print(f"  {key}: {value}")
        
        # 强制设置PDF类型（如果指定）
        if args.force_page_mode:
            extractor.pdf_type = 'scanned'
            print("已强制设置为整页提取模式")
        elif args.force_object_mode:
            extractor.pdf_type = 'digital'
            print("已强制设置为图像对象提取模式")
        
        # 提取图像
        extracted_images = extractor.extract_images(
            args.output_dir,
            min_size=args.min_size,
            filter_duplicates=not args.no_filter_duplicates,
            filter_contained=not args.no_filter_contained,
            overlap_threshold=args.overlap_threshold
        )
        
        # 打印摘要
        extractor.print_summary(extracted_images)
        
        # 关闭提取器
        extractor.close()
        
        print(f"\n提取完成！输出目录: {os.path.abspath(args.output_dir)}")
        
    except Exception as e:
        print(f"错误: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
