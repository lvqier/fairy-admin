import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="Fairy_Admin-0.1.11",
    version="0.1.11",
    author="Qier LU",
    author_email="lvqier@gmail.com",
    description="Fairy Admin add template based on Layui to Flask Admin",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/lvqier/fairy-admin",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    include_package_data=True,
    python_requires='>=3.5',
    install_requires=[
        "sqlalchemy",
        "flask_admin",
        "flask_security",
        "email_validator",
        "Pillow",
        "tablib"
    ]
)
