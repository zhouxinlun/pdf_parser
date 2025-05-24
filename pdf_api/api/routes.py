#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PDF API路由

提供PDF分析和图像提取的HTTP接口
"""

import os
import json
import uuid
import shutil
from datetime import datetime
from flask import Blueprint, request, jsonify, send_file, current_app, url_for
from werkzeug.utils import secure_filename
from core.pdf_analyzer import PDFAnalyzer
from core.pdf_image_extractor import PDFImageExtractor

# 创建蓝图
pdf_api = Blueprint('pdf_api', __name__)

# 允许的文件扩展名
ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@pdf_api.route('/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        'status': 'ok',
        'message': 'PDF API服务正常运行',
        'timestamp': datetime.now().isoformat()
    })

@pdf_api.route('/analyze', methods=['POST'])
def analyze_pdf():
    """
    分析PDF文件
    
    请求:
        - 文件上传: 'pdf_file'
        
    响应:
        - JSON: PDF分析结果
    """
    # 检查是否有文件
    if 'pdf_file' not in request.files:
        return jsonify({'error': '没有上传文件'}), 400
    
    file = request.files['pdf_file']
    
    # 检查文件名是否为空
    if file.filename == '':
        return jsonify({'error': '没有选择文件'}), 400
    
    # 检查文件类型
    if not allowed_file(file.filename):
        return jsonify({'error': '不支持的文件类型，仅支持PDF文件'}), 400
    
    try:
        # 生成唯一文件名
        filename = secure_filename(file.filename)
        unique_id = str(uuid.uuid4())
        unique_filename = f"{unique_id}_{filename}"
        
        # 保存文件
        upload_folder = current_app.config['UPLOAD_FOLDER']
        file_path = os.path.join(upload_folder, unique_filename)
        file.save(file_path)
        
        # 分析PDF
        analyzer = PDFAnalyzer(file_path)
        result = analyzer.get_analysis_result()
        analyzer.close()
        
        # 添加文件信息
        result['file_id'] = unique_id
        result['original_filename'] = filename
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    finally:
        # 清理文件
        if os.path.exists(file_path):
            os.remove(file_path)

@pdf_api.route('/extract', methods=['POST'])
def extract_images():
    """
    从PDF中提取图像
    
    请求:
        - 文件上传: 'pdf_file'
        - 表单参数:
            - min_size: 最小图像尺寸（像素），默认为100
            - filter_duplicates: 是否过滤重复图像，默认为True
            - filter_contained: 是否过滤被包含的小图像，默认为True
            - overlap_threshold: 重叠面积比例阈值（0-1之间），默认为0.8
            - force_mode: 强制使用指定的提取模式，可选值：'vector', 'scanned', 'digital'
            - dpi: 输出图像的DPI，默认为300
        
    响应:
        - JSON: 提取结果，包含提取的图像信息和下载链接
    """
    # 检查是否有文件
    if 'pdf_file' not in request.files:
        return jsonify({'error': '没有上传文件'}), 400
    
    file = request.files['pdf_file']
    
    # 检查文件名是否为空
    if file.filename == '':
        return jsonify({'error': '没有选择文件'}), 400
    
    # 检查文件类型
    if not allowed_file(file.filename):
        return jsonify({'error': '不支持的文件类型，仅支持PDF文件'}), 400
    
    try:
        # 获取参数
        min_size = int(request.form.get('min_size', 100))
        filter_duplicates = request.form.get('filter_duplicates', 'true').lower() == 'true'
        filter_contained = request.form.get('filter_contained', 'true').lower() == 'true'
        overlap_threshold = float(request.form.get('overlap_threshold', 0.8))
        force_mode = request.form.get('force_mode', None)
        dpi = int(request.form.get('dpi', 300))
        filter_text = request.form.get('filter_text', 'false').lower() == 'true'
        
        # 生成唯一文件名和目录
        filename = secure_filename(file.filename)
        unique_id = str(uuid.uuid4())
        unique_filename = f"{unique_id}_{filename}"
        
        # 保存文件
        upload_folder = current_app.config['UPLOAD_FOLDER']
        file_path = os.path.join(upload_folder, unique_filename)
        file.save(file_path)
        
        # 创建输出目录
        output_dir = os.path.join(current_app.config['STATIC_FOLDER'], 'images', unique_id)
        os.makedirs(output_dir, exist_ok=True)
        
        # 提取图像
        extractor = PDFImageExtractor(
            pdf_path=file_path,
            output_dir=output_dir,
            min_size=min_size,
            filter_duplicates=filter_duplicates,
            filter_contained=filter_contained,
            overlap_threshold=overlap_threshold,
            force_mode=force_mode,
            dpi=dpi,
            filter_text=filter_text
        )
        
        result = extractor.extract_images()
        
        # 添加下载链接
        for image in result['images']:
            image_filename = image['file_name']
            image['download_url'] = url_for('static', filename=f"images/{unique_id}/{image_filename}", _external=True)
        
        # 添加文件信息
        result['file_id'] = unique_id
        result['original_filename'] = filename
        
        # 创建压缩包
        if result['extracted_count'] > 0:
            zip_filename = f"{unique_id}_images.zip"
            zip_path = os.path.join(current_app.config['STATIC_FOLDER'], 'downloads', zip_filename)
            os.makedirs(os.path.dirname(zip_path), exist_ok=True)
            
            # 创建压缩包
            shutil.make_archive(zip_path[:-4], 'zip', output_dir)
            
            # 添加压缩包下载链接
            result['zip_download_url'] = url_for('static', filename=f"downloads/{zip_filename}", _external=True)
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    finally:
        # 清理上传的PDF文件
        if os.path.exists(file_path):
            os.remove(file_path)

@pdf_api.route('/download/<file_id>', methods=['GET'])
def download_images(file_id):
    """
    下载提取的图像压缩包
    
    参数:
        - file_id: 文件ID
        
    响应:
        - 文件: 图像压缩包
    """
    try:
        zip_filename = f"{file_id}_images.zip"
        zip_path = os.path.join(current_app.config['STATIC_FOLDER'], 'downloads', zip_filename)
        
        if not os.path.exists(zip_path):
            return jsonify({'error': '文件不存在'}), 404
        
        return send_file(zip_path, as_attachment=True, download_name=zip_filename)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
