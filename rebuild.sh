pip uninstall -y dist/*.whl
rm -rf dist/
python setup.py bdist_wheel
pip install dist/*.whl