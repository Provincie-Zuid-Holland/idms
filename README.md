# iDMS

![Upload Python Package](https://github.com/ProvZH/iDMS/workflows/Upload%20Python%20Package/badge.svg)


Python class to talk to iDMS REST and Search API within Provincie Zuid-Holland.

# Goal
The goal of the package is to have an easy interface to use the API in Python.

Mainly focussed to work with Content Server 20.2, see [API docs](
https://appworksdeveloper.opentext.com/webaccess/#url=%2Fawd%2Fresources%2Fapis%2Fcs-rest-api-for-cs-20-2&tab=501).

# Quick start
## Requirements
1. `pip install idms`
2. `pip install pandas` (optional - for easy data transformation)
3. `pip install openpyxl` (optional - to write to Excel file)

##  Sample code
```python
import getpass
import idms.api.contentserver as cs
import pandas # optional

baseUrl = "idms-url"
idms_username = getpass.getpass(prompt='IDMS username:')
idms_password = getpass.getpass(prompt='IDMS password:')
idms = cs.crawler(baseUrl, idms_username, idms_password)

array = idms.search("overdevest prox[1,f] daniel)")
print(f"Found {len(array)} search results")

# optional load results in a data frame to export results.
df = pd.DataFrame(arr)
print(df)

# Export results to Excel
df.to_excel("searchresults.xlsx")
```

# Development
Package is hosted on GitHub. After each change increase version number and create a new Release on GitHub. The pipeline will trigger a release to PyPi (see status batch above).

# Disclaimer
The developers of this package are not affiliated with OpenText.