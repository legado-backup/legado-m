from setuptools import setup, find_packages

setup(
    name="legado-client",
    version="3.0.0",
    description="Legado book source / RSS source debugging client",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "requests>=2.28.0",
        "beautifulsoup4>=4.11.0",
        "lxml>=4.9.0",
        "psutil>=5.9.0",
        "jsonpath-ng>=1.6.0",
        "pyyaml>=6.0",
        "aiosqlite>=0.20.0",
        "python-dotenv>=1.0.0",
        "sqlalchemy[asyncio]>=2.0.0",
        "alembic>=1.13.0",
        "httpx>=0.25.0",
    ],
    extras_require={
        "web": [
            "fastapi>=0.104.0",
            "uvicorn[standard]>=0.24.0",
            "python-multipart>=0.0.6",
            "websockets>=12.0",
            "slowapi>=0.1.9",
        ],
        "db": [
            "aiomysql>=0.2.0",
            "alembic>=1.13.0",
            "pymysql>=1.1.0",
        ],
        "fetcher": [
            "httpx>=0.25.0",
            "beautifulsoup4>=4.11.0",
            "lxml>=4.9.0",
        ],
        "test": ["pytest>=7.0", "pytest-cov>=4.0"],
        "crypto": ["pycryptodome>=3.18"],
        "playwright": ["playwright>=1.40.0"],
    },
    entry_points={
        "console_scripts": [
            "legado-client=legado_client.cli:main",
        ],
    },
)
