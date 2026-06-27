# 运行环境说明

## 推荐环境

| 项目 | 版本 |
| --- | --- |
| 操作系统 | Windows 10 / 11、macOS 或 Linux |
| Python | 3.12（最低支持 3.10） |
| Streamlit | 1.41.1 |
| Pandas | 2.2.3 |
| NumPy | 2.2.1 |
| Plotly | 5.24.1 |
| openpyxl | 3.1.5 |
| Pytest | 8.3.4 |

所有 Python 依赖均已固定在根目录的 `requirements.txt` 中。

## 最简单的运行方式

Windows 用户直接双击：

```text
run_app.bat
```

启动程序会自动完成：

1. 创建项目专属的 `.venv` 虚拟环境；
2. 安装固定版本的依赖；
3. 检查端口是否被占用；
4. 启动产品并显示浏览器地址。

## `.env` 配置

本地 `.env` 已整理为：

```dotenv
APP_HOST=127.0.0.1
APP_PORT=8501
```

- `APP_HOST`：本机访问地址，通常不需要修改。
- `APP_PORT`：默认端口；如果被占用，启动程序会自动寻找下一个端口。
- 当前产品无需 API Key，业务数据只在本机计算。

GitHub 中提供 `.env.example`，实际 `.env` 不会提交，避免以后误传密钥。

## Conda 用户

项目也提供 `environment.yml`：

```bash
conda env create -f environment.yml
conda activate home-deal-insight-agent
streamlit run app.py
```

## 环境检查

```bash
python -m pytest -q
python evaluation/evaluate.py
```

正常结果应为：

```text
9 passed
准确率：24/24 = 100.0%
```

