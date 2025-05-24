#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
改进版PDF图片提取工具 (使用pdfplumber和pypdfium2)

从PDF文件中提取图片并按页码分组保存到本地，
包含智能过滤功能，减少重叠和碎片化图像
"""

import os
import json
import hashlib
import numpy as np
import pdfplumber
import pypdfium2 as pdfium
from PIL import Image, ImageChops
from io import BytesIO
from collections import defaultdict


def is_similar_image(img1, img2, threshold=0.9):
    """
    比较两个PIL图像是否相似
    
    参数:
        img1 (PIL.Image): 第一个图像
        img2 (PIL.Image): 第二个图像
        threshold (float): 相似度阈值，0-1之间，越高要求越严格
        
    返回:
        bool: 如果图像相似则返回True，否则返回False
    """
    # 确保两个图像大小相同
    if img1.size != img2.size:
        # 调整大小以便比较
        img2 = img2.resize(img1.size, Image.LANCZOS)
    
    # 转换为相同模式
    if img1.mode != img2.mode:
        if 'A' in img1.mode:
            img1 = img1.convert('RGBA')
            img2 = img2.convert('RGBA')
        else:
            img1 = img1.convert('RGB')
            img2 = img2.convert('RGB')
    
    # 计算差异
    diff = ImageChops.difference(img1, img2)
    
    # 计算差异程度
    diff_array = np.array(diff)
    non_zero = np.count_nonzero(diff_array)
    total_pixels = diff_array.size
    
    # 计算相似度 (0-1)
    similarity = 1 - (non_zero / total_pixels)
    
    return similarity >= threshold


def is_too_small(img, min_pixels=100):
    """
    检查图像是否太小
    
    参数:
        img (PIL.Image): 图像
        min_pixels (int): 最小像素数
        
    返回:
        bool: 如果图像太小则返回True，否则返回False
    """
    width, height = img.size
    return width * height < min_pixels


def is_mostly_white(img, threshold=0.95):
    """
    检查图像是否主要是白色
    
    参数:
        img (PIL.Image): 图像
        threshold (float): 白色像素比例阈值
        
    返回:
        bool: 如果图像主要是白色则返回True，否则返回False
    """
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    # 将图像转换为numpy数组
    img_array = np.array(img)
    
    # 计算接近白色的像素数量
    # RGB值都大于240认为是白色
    white_pixels = np.sum((img_array > 240).all(axis=2))
    total_pixels = img_array.shape[0] * img_array.shape[1]
    
    return white_pixels / total_pixels >= threshold


def is_mostly_black(img, threshold=0.95):
    """
    检查图像是否主要是黑色
    
    参数:
        img (PIL.Image): 图像
        threshold (float): 黑色像素比例阈值
        
    返回:
        bool: 如果图像主要是黑色则返回True，否则返回False
    """
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    # 将图像转换为numpy数组
    img_array = np.array(img)
    
    # 计算接近黑色的像素数量
    # RGB值都小于15认为是黑色
    black_pixels = np.sum((img_array < 15).all(axis=2))
    total_pixels = img_array.shape[0] * img_array.shape[1]
    
    return black_pixels / total_pixels >= threshold


def is_contained_in(rect1, rect2, tolerance=0.9):
    """
    检查矩形1是否基本包含在矩形2中
    
    参数:
        rect1 (tuple): 第一个矩形 (x0, y0, x1, y1)
        rect2 (tuple): 第二个矩形 (x0, y0, x1, y1)
        tolerance (float): 容差，0-1之间
        
    返回:
        bool: 如果矩形1基本包含在矩形2中则返回True，否则返回False
    """
    x0_1, y0_1, x1_1, y1_1 = rect1
    x0_2, y0_2, x1_2, y1_2 = rect2
    
    # 计算矩形1的面积
    area1 = (x1_1 - x0_1) * (y1_1 - y0_1)
    
    # 计算重叠区域
    overlap_x0 = max(x0_1, x0_2)
    overlap_y0 = max(y0_1, y0_2)
    overlap_x1 = min(x1_1, x1_2)
    overlap_y1 = min(y1_1, y1_2)
    
    # 检查是否有重叠
    if overlap_x0 >= overlap_x1 or overlap_y0 >= overlap_y1:
        return False
    
    # 计算重叠面积
    overlap_area = (overlap_x1 - overlap_x0) * (overlap_y1 - overlap_y0)
    
    # 检查重叠比例
    return overlap_area / area1 >= tolerance


def extract_images_from_pdf(pdf_path, output_dir=None, save_images=True, group_by_page=True, 
                           min_size=100, filter_duplicates=True, filter_contained=True, overlap_threshold=0.8):
    """
    从PDF文件中提取所有图片及其信息，并进行智能过滤
    
    参数:
        pdf_path (str): PDF文件的路径
        output_dir (str, 可选): 保存图片的目录，如果save_images为True则必须提供
        save_images (bool, 可选): 是否将图片保存到文件系统，默认为True
        group_by_page (bool, 可选): 是否按页码分组创建子文件夹保存图片，默认为True
        min_size (int, 可选): 图像的最小像素数，小于此值的图像将被过滤，默认为100
        filter_duplicates (bool, 可选): 是否过滤重复图像，默认为True
        filter_contained (bool, 可选): 是否过滤被其他图像包含的小图像，默认为True
    
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
    
    # 用于存储每页的图像矩形信息，用于后处理过滤重叠图像
    page_rects = defaultdict(list)
    
    # 使用pdfplumber打开PDF获取元数据
    with pdfplumber.open(pdf_path) as pdf:
        # 使用pypdfium2打开PDF获取图片数据
        pdf_file = pdfium.PdfDocument(pdf_path)
        
        # 遍历PDF的每一页
        for page_index, page in enumerate(pdf.pages):
            print(f"处理第{page_index + 1}页...")
            
            # 获取页面上的图片列表
            image_list = page.images
            
            # 如果按页码分组并且有图片，创建页面目录
            if group_by_page and save_images and image_list:
                page_dir = os.path.join(output_dir, f"page_{page_index + 1}")
                os.makedirs(page_dir, exist_ok=True)
            
            # 存储当前页面的图像和坐标
            page_images = []
            
            # 遍历页面上的每个图片
            for img_index, img in enumerate(image_list):
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
                    pdf_page = pdf_file[page_index]
                    bitmap = pdf_page.render(
                        scale=1.0,
                        rotation=0,
                        crop=(x0, y0, x1, y1)
                    )
                    pil_image = bitmap.to_pil()
                    
                    # 过滤主要是白色或黑色的图像
                    if is_mostly_white(pil_image) or is_mostly_black(pil_image):
                        continue
                    
                    # 检查是否被其他图像包含
                    if filter_contained:
                        contained = False
                        for other_img in image_list:
                            if other_img == img:
                                continue
                            
                            other_x0, other_y0 = other_img['x0'], other_img['top']
                            other_x1, other_y1 = other_img['x1'], other_img['bottom']
                            
                            if is_contained_in((x0, y0, x1, y1), 
                                              (other_x0, other_y0, other_x1, other_y1)):
                                contained = True
                                break
                        
                        if contained:
                            continue
                    
                    # 检查是否与已提取的图像重复
                    if filter_duplicates and page_images:
                        duplicate = False
                        for existing_img, _ in page_images:
                            if is_similar_image(pil_image, existing_img):
                                duplicate = True
                                break
                        
                        if duplicate:
                            continue
                    
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
                    
                    # 添加到当前页面图像列表
                    page_images.append((pil_image, image_info))
                    
                    # 保存矩形信息用于后处理
                    page_rects[page_index].append({
                        "rect": (x0, y0, x1, y1),
                        "area": (x1 - x0) * (y1 - y0),
                        "index": len(all_images) - 1  # 图像在all_images中的索引
                    })
                    
                except Exception as e:
                    print(f"警告: 提取第{page_index+1}页第{img_index+1}张图片时出错: {e}")
                    continue
    
    # 后处理：进一步过滤重叠图像
    if filter_contained and overlap_threshold < 1.0:
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
        return filtered_images
    
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
    pages_with_images = defaultdict(list)
    for img in image_info:
        pages_with_images[img["page_index"]].append(img)
    
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
    
    # 统计图片尺寸分布
    sizes = {
        "小图 (<10KB)": 0,
        "中图 (10KB-100KB)": 0,
        "大图 (>100KB)": 0
    }
    
    for img in image_info:
        size_kb = img["size_bytes"] / 1024
        if size_kb < 10:
            sizes["小图 (<10KB)"] += 1
        elif size_kb < 100:
            sizes["中图 (10KB-100KB)"] += 1
        else:
            sizes["大图 (>100KB)"] += 1
    
    print("\n图片尺寸统计:")
    for size_cat, count in sizes.items():
        print(f"  - {size_cat}: {count}张")
    
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
    
    parser = argparse.ArgumentParser(description='从PDF中提取图片（改进版，带智能过滤）')
    parser.add_argument('pdf_path', help='PDF文件路径')
    parser.add_argument('--output-dir', '-o', help='图片输出目录', default='./extracted_images')
    parser.add_argument('--no-save', '-n', action='store_true', help='不保存图片到文件系统')
    parser.add_argument('--no-group', '-g', action='store_true', help='不按页码分组创建子文件夹')
    parser.add_argument('--min-size', '-m', type=int, default=100, help='图像的最小像素数，默认为100')
    parser.add_argument('--no-filter-duplicates', '-d', action='store_true', 
                        help='不过滤重复图像')
    parser.add_argument('--no-filter-contained', '-c', action='store_true', 
                        help='不过滤被其他图像包含的小图像')
    parser.add_argument('--overlap-threshold', '-t', type=float, default=0.8, 
                        help='重叠面积比例阈值，默认为0.8，范围0-1之间')
    parser.add_argument('--json', '-j', help='将图片信息保存为JSON文件')
    
    args = parser.parse_args()
    
    try:
        print(f"开始处理PDF: {args.pdf_path}")
        
        # 提取图片
        image_info = extract_images_from_pdf(
            args.pdf_path, 
            output_dir=args.output_dir,
            save_images=not args.no_save,
            group_by_page=not args.no_group,
            min_size=args.min_size,
            filter_duplicates=not args.no_filter_duplicates,
            filter_contained=not args.no_filter_contained,
            overlap_threshold=args.overlap_threshold
        )
        
        print(f"图片提取完成，共提取 {len(image_info)} 张图片")
        
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
    sys.exit(main())
