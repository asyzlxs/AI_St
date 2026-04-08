from setuptools import setup, find_packages

setup(
    name="stock-cli",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "yfinance>=0.2.0",
        "click>=8.0.0",
        "matplotlib>=3.5.0",
        "pandas>=1.4.0",
        "openpyxl>=3.0.0",
        "akshare>=1.10.0",
    ],
    entry_points={
        "console_scripts": [
            "stock=stock_cli.main:cli",
        ],
    },
)
