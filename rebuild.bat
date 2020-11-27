@echo on
pip uninstall -y dist\idms-0.1.7-py3-none-any.whl
del /Q dist\
python setup.py bdist_wheel
pip install dist\idms-0.1.7-py3-none-any.whl[dev]