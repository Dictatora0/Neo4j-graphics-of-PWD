#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""\
将 Jupyter Notebook 导出为 PDF（支持中文显示）的小工具。

实现思路：
- 使用 nbconvert 的 WebPDFExporter，通过无头 Chromium 将 HTML 打印为 PDF。
- WebPDF 路线直接走浏览器渲染路径，天然支持 UTF-8 与系统中的中文字体
  （如 macOS 上的苹方、宋体、黑体、微软雅黑等），避免 LaTeX 模板中繁琐的中文字体配置。

使用示例：

1. 在项目根目录下运行（默认导出当前仓库里的 PWD_Knowledge_Graph_Analysis.ipynb）：

   python export_notebook_to_pdf.py

2. 指定其它 Notebook：

   python export_notebook_to_pdf.py \
       --notebook PWD_KG_Notebook.ipynb \
       --output-dir output \
       --output-name PWD_KG_Notebook_CN

先决条件：
- 已安装 Jupyter & nbconvert >= 6
- 已安装 WebPDF 相关依赖：
    pip install "nbconvert[webpdf]"
  首次运行时 nbconvert 会自动下载一份 Chromium。下载完成后再次运行脚本即可。
"""

import argparse
import sys
from pathlib import Path

import nbformat


def export_notebook_to_pdf(notebook_path: Path, output_dir: Path, output_name: str | None = None) -> Path:
    """使用 nbconvert 的 WebPDFExporter 将 Notebook 导出为 PDF。

    参数
    ----
    notebook_path : Path
        要导出的 .ipynb 文件路径。
    output_dir : Path
        PDF 输出目录，会自动创建。
    output_name : str | None
        输出 PDF 文件名（不含后缀）。若为 None，则使用 notebook 文件名。
    """
    try:
        from nbconvert.exporters import WebPDFExporter  # type: ignore[import]
        from traitlets.config import Config  # type: ignore[import]
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            "导出失败：未能导入 nbconvert 的 WebPDFExporter。\n"
            "请先安装依赖：pip install \"nbconvert[webpdf]\"，\n"
            "并确保 nbconvert 版本 >= 6。原始错误：" + repr(exc)
        ) from exc

    if not notebook_path.is_file():
        raise FileNotFoundError(f"找不到 Notebook 文件: {notebook_path}")

    output_dir.mkdir(parents=True, exist_ok=True)
    if output_name is None or not output_name.strip():
        output_name = notebook_path.stem

    # 读取 Notebook
    nb = nbformat.read(notebook_path, as_version=4)

    # WebPDF 配置：
    # - paginate=True 便于分页
    # - template_name 使用默认/lab 模板，能较好还原 notebook 外观
    c = Config()
    c.WebPDFExporter.paginate = True
    # 如需固定字体，可在这里切换为带自定义 CSS 的模板
    # c.WebPDFExporter.template_name = "lab"

    exporter = WebPDFExporter(config=c)

    # 运行导出
    print(f"[INFO] 正在导出为 PDF（WebPDF 模式），文件：{notebook_path}")
    try:
        pdf_data, _ = exporter.from_notebook_node(nb)
    except Exception as exc:  # noqa: BLE001
        # 常见错误：首次运行时 Chromium 尚未下载完成，或网络被阻断
        raise RuntimeError(
            "WebPDF 导出失败，常见原因：\n"
            "1. 首次运行时 Chromium 尚未下载完成，可稍候再试；\n"
            "2. 网络环境阻止了 Chromium 下载；\n"
            "3. nbconvert[webpdf] 版本不兼容。\n"
            "原始错误：" + repr(exc)
        ) from exc

    output_pdf = output_dir / f"{output_name}.pdf"
    output_pdf.write_bytes(pdf_data)
    print(f"[OK] 导出成功：{output_pdf}")
    print("提示：PDF 中的中文显示依赖系统字体。若发现个别字体样式不符合预期，\n"
          "可以在系统中调整默认中文字体，或在 Notebook 中通过 Matplotlib/HTML 指定字体族。")
    return output_pdf


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="将 Jupyter Notebook 导出为支持中文显示的 PDF (nbconvert WebPDF 模式)",
    )
    parser.add_argument(
        "--notebook",
        type=str,
        default="PWD_Knowledge_Graph_Analysis.ipynb",
        help="要导出的 Notebook 相对路径，默认：PWD_Knowledge_Graph_Analysis.ipynb",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="output",
        help="PDF 输出目录，默认：output",
    )
    parser.add_argument(
        "--output-name",
        type=str,
        default=None,
        help="输出 PDF 文件名（不含 .pdf 后缀），默认使用 notebook 文件名",
    )

    args = parser.parse_args(argv)

    notebook_path = Path(args.notebook).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()

    try:
        export_notebook_to_pdf(
            notebook_path=notebook_path,
            output_dir=output_dir,
            output_name=args.output_name,
        )
    except Exception as exc:  # noqa: BLE001
        print("[ERROR] 导出过程中出现错误：", file=sys.stderr)
        print(repr(exc), file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
