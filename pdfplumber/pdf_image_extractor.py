#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PDF图片提取工具 (使用pdfplumber和pypdfium2)

从PDF文件中提取图片并按页码分组保存到本地
"""

import os
import json
import hashlib
import pdfplumber
import pypdfium2 as pdfium
from PIL import Image
from io import BytesIO


def extract_images_from_pdf(pdf_path, output_dir=None, save_images=True, group_by_page=True):
    """
    从PDF文件中提取所有图片及其信息
    
    参数:
        pdf_path (str): PDF文件的路径
        output_dir (str, 可选): 保存图片的目录，如果save_images为True则必须提供
        save_images (bool, 可选): 是否将图片保存到文件系统，默认为True
        group_by_page (bool, 可选): 是否按页码分组创建子文件夹保存图片，默认为True
    
    返回:
        list: 包含所有图片信息的列表，每个元素是一个字典，包含图片的页码、索引、尺寸、格式等信息
    """
    # 检查PDF文件是否存在
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF文件不存在: {pdf_path}")
    
    # 如果需要保存图片，检查输出目录
    if save_images:
        if not output_dir:
            raise ValueError("如果save_images为True，则必须提供output_dir参数")
        
        # 创建输出目录（如果不存在）
        os.makedirs(output_dir, exist_ok=True)
    
    # 用于存储所有图片信息的列表
    all_images = []
    
    # 使用pdfplumber打开PDF获取元数据
    with pdfplumber.open(pdf_path) as pdf:
        # 使用pypdfium2打开PDF获取图片数据
        pdf_file = pdfium.PdfDocument(pdf_path)
        
        # 遍历PDF的每一页
        for page_index, page in enumerate(pdf.pages):
            # 获取页面上的图片列表
            image_list = page.images
            
            # 如果按页码分组并且有图片，创建页面目录
            if group_by_page and save_images and image_list:
                page_dir = os.path.join(output_dir, f"page_{page_index + 1}")
                os.makedirs(page_dir, exist_ok=True)
            
            # 遍历页面上的每个图片
            for img_index, img in enumerate(image_list):
                # 使用pypdfium2提取图片内容
                try:
                    # 获取图片位置信息
                    x0, y0, x1, y1 = img['x0'], img['top'], img['x1'], img['bottom']
                    width = int(x1 - x0)
                    height = int(y1 - y0)
                    
                    # 使用pypdfium2从PDF中提取图片
                    pdf_page = pdf_file[page_index]
                    bitmap = pdf_page.render(
                        scale=1.0,
                        rotation=0,
                        crop=(x0, y0, x1, y1)
                    )
                    pil_image = bitmap.to_pil()
                    
                    # 将图片转换为字节流以计算哈希值
                    img_byte_arr = BytesIO()
                    pil_image.save(img_byte_arr, format=pil_image.format or 'PNG')
                    image_bytes = img_byte_arr.getvalue()
                    
                    # 计算图片哈希值，用于唯一标识
                    img_hash = hashlib.md5(image_bytes).hexdigest()
                    
                    # 确定图片格式
                    image_format = pil_image.format or 'PNG'
                    image_ext = image_format.lower()
                    
                    # 收集图片信息
                    image_info = {
                        "page_index": page_index + 1,  # 页码（从1开始）
                        "img_index": img_index + 1,    # 图片在页面中的索引（从1开始）
                        "width": width,                # 宽度（像素）
                        "height": height,              # 高度（像素）
                        "format": image_ext,           # 格式（扩展名）
                        "format_description": image_format,  # 格式描述
                        "color_mode": pil_image.mode,  # 颜色模式
                        "size_bytes": len(image_bytes),  # 图片大小（字节）
                        "md5_hash": img_hash,          # MD5哈希值
                        "x0": x0,                      # 左上角X坐标
                        "y0": y0,                      # 左上角Y坐标
                        "x1": x1,                      # 右下角X坐标
                        "y1": y1,                      # 右下角Y坐标
                    }
                    
                    # 如果需要保存图片
                    if save_images:
                        # 确定保存路径
                        if group_by_page:
                            # 按页码分组创建子文件夹
                            filename = f"img{img_index+1}_{img_hash[:8]}.{image_ext}"
                            filepath = os.path.join(page_dir, filename)
                        else:
                            # 不分组，直接保存到输出目录
                            filename = f"page{page_index+1}_img{img_index+1}_{img_hash[:8]}.{image_ext}"
                            filepath = os.path.join(output_dir, filename)
                        
                        # 保存图片
                        pil_image.save(filepath)
                        
                        # 添加文件路径到图片信息
                        image_info["saved_path"] = filepath
                    
                    # 添加到结果列表
                    all_images.append(image_info)
                    
                except Exception as e:
                    print(f"警告: 提取第{page_index+1}页第{img_index+1}张图片时出错: {e}")
                    continue
    
    return all_images


def save_image_info_to_json(image_info, output_json_path):
    """
    将图片信息保存为JSON文件
    
    参数:
        image_info (list): 图片信息列表
        output_json_path (str): 输出JSON文件的路径
    """
    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(image_info, f, ensure_ascii=False, indent=2)


def print_image_summary(image_info):
    """
    打印图片信息摘要并按页面分组统计
    
    参数:
        image_info (list): 图片信息列表
    """
    if not image_info:
        print("PDF中未找到图片")
        return
    
    print(f"共找到 {len(image_info)} 张图片")
    
    # 按页面分组统计
    pages_with_images = {}
    for img in image_info:
        page_idx = img["page_index"]
        if page_idx not in pages_with_images:
            pages_with_images[page_idx] = []
        pages_with_images[page_idx].append(img)
    
    print(f"包含图片的页面数: {len(pages_with_images)}")
    
    # 打印每页的图片数量
    print("\n每页图片数量:")
    for page, images in sorted(pages_with_images.items()):
        print(f"  - 第{page}页: {len(images)}张图片")
    
    # 统计图片格式
    formats = {}
    for img in image_info:
        fmt = img.get("format", "未知").upper()
        formats[fmt] = formats.get(fmt, 0) + 1
    
    print("\n图片格式统计:")
    for fmt, count in formats.items():
        print(f"  - {fmt}: {count}张")
    
    # 打印前5张图片的详细信息
    print("\n前5张图片的详细信息:")
    for i, img in enumerate(image_info[:5]):
        print(f"\n图片 #{i+1}:")
        print(f"  页码: {img['page_index']}")
        print(f"  位置: ({img['x0']:.1f}, {img['y0']:.1f}) - ({img['x1']:.1f}, {img['y1']:.1f})")
        print(f"  尺寸: {img['width']}x{img['height']}像素")
        print(f"  格式: {img.get('format', '未知').upper()}")
        print(f"  大小: {img['size_bytes']/1024:.2f} KB")
        if "saved_path" in img:
            print(f"  保存路径: {img['saved_path']}")


def main():
    """
    主函数，用于命令行调用
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='从PDF中提取图片')
    parser.add_argument('pdf_path', help='PDF文件路径')
    parser.add_argument('--output-dir', '-o', help='图片输出目录', default='./extracted_images')
    parser.add_argument('--no-save', '-n', action='store_true', help='不保存图片到文件系统')
    parser.add_argument('--no-group', '-g', action='store_true', help='不按页码分组创建子文件夹')
    parser.add_argument('--json', '-j', help='将图片信息保存为JSON文件')
    
    args = parser.parse_args()
    
    try:
        # 提取图片
        image_info = extract_images_from_pdf(
            args.pdf_path, 
            output_dir=args.output_dir,
            save_images=not args.no_save,
            group_by_page=not args.no_group
        )
        
        # 打印摘要
        print_image_summary(image_info)
        
        # 如果指定了JSON输出路径，保存为JSON
        if args.json:
            save_image_info_to_json(image_info, args.json)
            print(f"\n图片信息已保存到: {args.json}")
            
    except Exception as e:
        print(f"错误: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    import sys
    # python pdf_image_extractor.py "/Users/zhouxinlun/Downloads/IVR Drawing.pdf" -o ./images
    sys.exit(main())
