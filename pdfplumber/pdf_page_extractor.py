#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PDF页面提取器

将PDF的页面提取为图像，适用于扫描PDF或包含复杂图像的PDF文件
"""

import os
import sys
import fitz  # PyMuPDF
import argparse
from datetime import datetime

class PDFPageExtractor:
    """PDF页面提取器类，用于将PDF页面转换为图像"""
    
    def __init__(self, pdf_path):
        """
        初始化PDF页面提取器
        
        参数:
            pdf_path (str): PDF文件路径
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF文件不存在: {pdf_path}")
            
        self.pdf_path = pdf_path
        self.doc = fitz.open(pdf_path)
        self.page_count = len(self.doc)
        
        # 获取PDF基本信息
        self.pdf_info = {
            "文件名": os.path.basename(pdf_path),
            "页数": self.page_count,
            "标题": self.doc.metadata.get("title", "未知"),
            "作者": self.doc.metadata.get("author", "未知"),
            "创建日期": self._format_date(self.doc.metadata.get("creationDate")),
            "修改日期": self._format_date(self.doc.metadata.get("modDate")),
        }
    
    def _format_date(self, date_str):
        """格式化PDF日期字符串"""
        if not date_str:
            return "未知"
        try:
            # PDF日期格式通常为: D:YYYYMMDDHHmmSS
            if date_str.startswith("D:"):
                date_str = date_str[2:]
                year = int(date_str[0:4])
                month = int(date_str[4:6])
                day = int(date_str[6:8])
                hour = int(date_str[8:10]) if len(date_str) > 8 else 0
                minute = int(date_str[10:12]) if len(date_str) > 10 else 0
                second = int(date_str[12:14]) if len(date_str) > 12 else 0
                return datetime(year, month, day, hour, minute, second).strftime("%Y-%m-%d %H:%M:%S")
        except:
            pass
        return date_str
    
    def get_pdf_info(self):
        """获取PDF文件的基本信息"""
        return self.pdf_info
    
    def extract_page(self, page_num, output_path, dpi=300, output_format="png"):
        """
        提取单个页面为图像
        
        参数:
            page_num (int): 页码 (从1开始)
            output_path (str): 输出文件路径
            dpi (int): 输出图像的DPI (每英寸点数)，默认300
            output_format (str): 输出格式，支持png、jpg等
            
        返回:
            str: 输出文件路径
        """
        if page_num < 1 or page_num > self.page_count:
            raise ValueError(f"页码超出范围: {page_num}，PDF共有 {self.page_count} 页")
        
        # 获取页面
        page = self.doc[page_num - 1]
        
        # 计算缩放因子 (DPI / 72，因为PDF的默认DPI是72)
        zoom_factor = dpi / 72
        
        # 渲染页面为图像
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom_factor, zoom_factor))
        
        # 确保输出目录存在
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # 保存图像
        pix.save(output_path)
        
        return output_path
    
    def extract_all_pages(self, output_dir, dpi=300, output_format="png", page_range=None):
        """
        提取所有页面为图像
        
        参数:
            output_dir (str): 输出目录
            dpi (int): 输出图像的DPI (每英寸点数)，默认300
            output_format (str): 输出格式，支持png、jpg等
            page_range (tuple): 页码范围 (start, end)，例如 (1, 5) 表示提取第1-5页
            
        返回:
            list: 输出文件路径列表
        """
        # 确保输出目录存在
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # 确定页码范围
        start_page = 1
        end_page = self.page_count
        
        if page_range:
            start_page = max(1, page_range[0])
            end_page = min(self.page_count, page_range[1])
        
        output_files = []
        
        # 提取每一页
        for page_num in range(start_page, end_page + 1):
            output_file = os.path.join(output_dir, f"page_{page_num}.{output_format}")
            self.extract_page(page_num, output_file, dpi, output_format)
            output_files.append(output_file)
            print(f"已提取第 {page_num} 页到 {output_file}")
        
        return output_files
    
    def close(self):
        """关闭PDF文档"""
        if hasattr(self, 'doc') and self.doc:
            self.doc.close()
    
    def __enter__(self):
        """支持with语句"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出with语句时关闭文档"""
        self.close()


def main():
    """命令行入口函数"""
    parser = argparse.ArgumentParser(description='将PDF页面提取为图像')
    parser.add_argument('pdf_path', help='PDF文件路径')
    parser.add_argument('--output-dir', '-o', help='输出目录', default='./extracted_pages')
    parser.add_argument('--dpi', '-d', type=int, default=300, help='输出图像的DPI，默认300')
    parser.add_argument('--format', '-f', default='png', help='输出图像格式，默认png')
    parser.add_argument('--page', '-p', type=int, help='指定提取单页，例如 -p 1 表示只提取第1页')
    parser.add_argument('--start-page', '-s', type=int, help='起始页码，默认为1')
    parser.add_argument('--end-page', '-e', type=int, help='结束页码，默认为最后一页')
    
    args = parser.parse_args()
    
    try:
        # 创建PDF页面提取器
        extractor = PDFPageExtractor(args.pdf_path)
        
        # 显示PDF信息
        pdf_info = extractor.get_pdf_info()
        print("PDF信息:")
        for key, value in pdf_info.items():
            print(f"  {key}: {value}")
        
        # 确定页码范围
        page_range = None
        if args.start_page or args.end_page:
            start = args.start_page or 1
            end = args.end_page or pdf_info["页数"]
            page_range = (start, end)
        
        # 提取页面
        if args.page:
            # 提取单页
            output_file = os.path.join(args.output_dir, f"page_{args.page}.{args.format}")
            extractor.extract_page(args.page, output_file, args.dpi, args.format)
            print(f"已提取第 {args.page} 页到 {output_file}")
        else:
            # 提取所有页面或指定范围的页面
            extractor.extract_all_pages(args.output_dir, args.dpi, args.format, page_range)
        
        # 关闭提取器
        extractor.close()
        
        print(f"\n提取完成！输出目录: {os.path.abspath(args.output_dir)}")
        
    except Exception as e:
        print(f"错误: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
