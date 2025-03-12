# Dune API 项目

这是一个使用 Python 调用 Dune Analytics API 的项目模板。

## 功能特性

- 使用 `python-dotenv` 管理环境变量
- 集成 `dune-client` 进行数据查询
- 包含基本的错误处理
- 提供单元测试示例

## 项目结构

```
.
├── README.md
├── requirements.txt
├── .env                # 环境变量配置（需要自己创建）
├── src/
│   └── main.py        # 主程序
└── tests/
    └── test_main.py   # 测试文件
```

## 安装

1. 克隆项目并创建虚拟环境：

```bash
python -m venv venv
source venv/bin/activate  # 在 Unix 或 MacOS 上
# 或
.\venv\Scripts\activate  # 在 Windows 上
```

2. 安装依赖：

```bash
pip install -r requirements.txt
```

3. 配置环境变量：
   - 复制 `.env.example` 为 `.env`
   - 在 `.env` 文件中设置您的 Dune API key

## 使用方法

1. 确保已经设置了正确的环境变量
2. 在 `src/main.py` 中设置您的查询 ID 和参数
3. 运行程序：

```bash
python src/main.py
```

## 测试

运行测试：

```bash
pytest tests/
```

## 注意事项

- 请确保将您的 API key 保密，不要提交到版本控制系统
- 在使用前请仔细阅读 Dune Analytics 的 API 文档和使用条款
