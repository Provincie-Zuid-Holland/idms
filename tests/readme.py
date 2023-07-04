import pkg_resources

installed_packages = [pkg.key for pkg in pkg_resources.working_set]
print(installed_packages)

import os

if os.environ.get("VIRTUAL_ENV"):
    print(
        f"A virtual environment is currently activated: {os.environ.get('VIRTUAL_ENV')}"
    )
else:
    print("No virtual environment is currently activated.")

import getpass
import idms.api.contentserver as cs
import pandas as pd  # optional

import logging

logging.basicConfig(level=logging.DEBUG)

baseUrl = 'FILL IN URL'
idms_username = getpass.getpass(prompt="IDMS username:")
idms_password = getpass.getpass(prompt="IDMS password:")
idms = cs.crawler(baseUrl, idms_username, idms_password, verifySSL=False)
idms.debugJson = True
logging.debug(f"idms.ticket: {idms.ticket}")
idms.outputColumns.append("versions.version_number")
array = idms.search("test+zoekwoord", limit=10, slice="12345678")
print(f"Found {len(array)} search results")

# optional load results in a data frame to export results.
df = pd.DataFrame(array)
print(df)

# Export results to Excel
df.to_excel("searchresults.xlsx")
