from setuptools import setup, find_packages

requirements = """
BeautifulSoup==3.2.1
mechanize==0.2.5
numpy
nltk==2.0.1
python-twitter==0.8.2
""".split()

setup(
 name='Yammer',
 version='0.1.1',
 author='David Grant',
 packages=find_packages(),
 install_requires=requirements
)
