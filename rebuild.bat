@echo on
pip uninstall -y dist\opentext-0.1.6-py3-none-any.whl
del /Q dist\
python setup.py bdist_wheel
pip install dist\opentext-0.1.6-py3-none-any.whl[dev]