from setuptools import find_packages, setup

setup(
    name="pyssion",
    version="0.2.0",
    package_dir={"": "pyssion_lib"},
    packages=find_packages(where="pyssion_lib"),
    package_data={"pyssion.manager.provision": ["modules/*/*"]},
    include_package_data=True,
    install_requires=[],  # SDK, agent and reactor client are stdlib-only
    extras_require={
        "server": ["fastapi>=0.100", "uvicorn", "sqlalchemy>=2.0", "minio"],
        "postgres": ["psycopg[binary]"],
        "runpod": ["runpod"],
        "reactor": ["torch"],
        "legacy": ["kubernetes", "minio", "click", "docker", "flask"],
    },
    entry_points={"console_scripts": ["pyssion=pyssion.cli:main"]},
    author="CaptCore",
    description="Pack your code, ignite it on any node, bring the results home.",
    long_description=open("Readme.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    classifiers=["Programming Language :: Python :: 3", "Operating System :: OS Independent"],
    python_requires=">=3.9",
    zip_safe=False,
)
