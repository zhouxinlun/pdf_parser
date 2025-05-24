# PDF图像提取API

这是一个基于Flask的Web API，用于智能提取PDF文件中的图像。它能够自动识别PDF类型（矢量PDF、扫描PDF、数字PDF）并使用最合适的方法提取图像。

## 功能特点

- 自动识别PDF类型（矢量PDF、扫描PDF、数字PDF、文本PDF）
- 根据PDF类型选择最合适的图像提取方法
- 支持过滤重复图像和重叠图像
- 支持整页渲染和图像对象提取两种模式
- 提供详细的PDF分析信息
- 提供RESTful API和Web界面

## 安装

1. 克隆仓库：

```bash
git clone <repository-url>
cd pdf_api
```

2. 创建虚拟环境并激活：

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows
```

3. 安装依赖：

```bash
pip install -r requirements.txt
```

## 运行

```bash
python app.py
```

服务将在 http://localhost:5000 启动。

## API文档

### 1. 健康检查

```
GET /api/health
```

返回API服务的状态信息。

### 2. 分析PDF

```
POST /api/analyze
```

分析PDF文件并返回其类型和结构信息。

**请求参数**：
- `pdf_file`：PDF文件（multipart/form-data）

**响应**：
```json
{
  "file_id": "uuid",
  "file_name": "example.pdf",
  "file_path": "/path/to/pdf",
  "metadata": {},
  "original_filename": "example.pdf",
  "page_count": 5,
  "pages_info": [],
  "pdf_type": "digital",
  "total_curves": 10,
  "total_images": 8,
  "total_lines": 50,
  "total_rects": 20,
  "total_text_chars": 1000,
  "total_vector_objects": 80
}
```

### 3. 提取图像

```
POST /api/extract
```

从PDF中提取图像并返回图像信息和下载链接。

**请求参数**：
- `pdf_file`：PDF文件（multipart/form-data）
- `min_size`：最小图像尺寸（像素），默认为100
- `filter_duplicates`：是否过滤重复图像，默认为true
- `filter_contained`：是否过滤被包含的小图像，默认为true
- `overlap_threshold`：重叠面积比例阈值（0-1之间），默认为0.8
- `force_mode`：强制使用指定的提取模式，可选值：'vector', 'scanned', 'digital'
- `dpi`：输出图像的DPI，默认为300

**响应**：
```json
{
  "extracted_count": 5,
  "file_id": "uuid",
  "images": [
    {
      "download_url": "http://localhost:5000/static/images/uuid/page_1.png",
      "extraction_method": "page_render",
      "file_name": "page_1.png",
      "file_path": "/path/to/images/page_1.png",
      "height": 1000,
      "image_index": 1,
      "page": 1,
      "width": 800
    }
  ],
  "original_filename": "example.pdf",
  "output_dir": "/path/to/output",
  "pdf_info": {
    "file_name": "example.pdf",
    "page_count": 5,
    "pdf_type": "vector",
    "total_images": 0,
    "total_text_chars": 500,
    "total_vector_objects": 1000
  },
  "success": true,
  "zip_download_url": "http://localhost:5000/static/downloads/uuid_images.zip"
}
```

### 4. 下载图像

```
GET /api/download/<file_id>
```

下载提取的图像压缩包。

**路径参数**：
- `file_id`：文件ID

**响应**：
- 图像压缩包文件

## Web界面

访问 http://localhost:5000 可以使用Web界面上传PDF文件并提取图像。

## 开发

### 项目结构

```
pdf_api/
├── api/                # API路由
│   ├── __init__.py
│   └── routes.py
├── core/               # 核心功能
│   ├── __init__.py
│   ├── pdf_analyzer.py
│   └── pdf_image_extractor.py
├── static/             # 静态文件
│   ├── downloads/      # 下载文件
│   └── images/         # 提取的图像
├── templates/          # HTML模板
│   └── index.html
├── uploads/            # 上传的文件
├── app.py              # 应用入口
├── README.md
└── requirements.txt    # 依赖项
```

### 环境变量

- `SECRET_KEY`：应用密钥，默认为'dev'
- `FLASK_ENV`：环境（development/production），默认为'development'
- `FLASK_DEBUG`：是否开启调试模式，默认为1（开启）

## 部署

### 使用Gunicorn部署

```bash
gunicorn -w 4 -b 0.0.0.0:5000 'app:create_app()'
```

### 使用Docker部署

1. 构建Docker镜像：

```bash
docker build -t pdf-api .
```

2. 运行容器：

```bash
docker run -p 5000:5000 pdf-api
```

## 许可证

[MIT](LICENSE)
