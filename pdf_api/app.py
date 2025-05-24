#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PDF API应用

提供PDF分析和图像提取的Web服务
"""

import os
import sys

# 添加当前目录到系统路径，确保可以导入模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
from api.routes import pdf_api

def create_app(test_config=None):
    """创建并配置Flask应用"""
    # 创建应用
    app = Flask(__name__, instance_relative_config=True)
    
    # 启用CORS
    CORS(app)
    
    # 配置应用
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev'),
        UPLOAD_FOLDER=os.path.join(app.root_path, 'uploads'),
        STATIC_FOLDER=os.path.join(app.root_path, 'static'),
        MAX_CONTENT_LENGTH=50 * 1024 * 1024,  # 限制上传文件大小为50MB
    )
    
    # 如果提供了测试配置，则使用测试配置
    if test_config is not None:
        app.config.from_mapping(test_config)
    
    # 确保目录存在
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(os.path.join(app.config['STATIC_FOLDER'], 'images'), exist_ok=True)
    os.makedirs(os.path.join(app.config['STATIC_FOLDER'], 'downloads'), exist_ok=True)
    
    # 注册蓝图
    app.register_blueprint(pdf_api, url_prefix='/api')
    
    # 首页路由
    @app.route('/')
    def index():
        """渲染首页"""
        return render_template('index.html')
    
    # 错误处理
    @app.errorhandler(404)
    def not_found(error):
        """处理404错误"""
        return jsonify({'error': '资源不存在'}), 404
    
    @app.errorhandler(500)
    def server_error(error):
        """处理500错误"""
        return jsonify({'error': '服务器内部错误'}), 500
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=8888, debug=True)
