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
import pandas  # optional

import logging

logging.basicConfig(level=logging.DEBUG)

baseUrl = "FILL IN YOUR CONTENT SERVER URL HERE"
idms_username = getpass.getpass(prompt="IDMS username:")
idms_password = getpass.getpass(prompt="IDMS password:")
idms = cs.crawler(baseUrl, idms_username, idms_password, verifySSL=False)

array = idms.search("overdevest prox[1,f] daniel)")
print(f"Found {len(array)} search results")

# optional load results in a data frame to export results.
df = pd.DataFrame(arr)
print(df)

# Export results to Excel
df.to_excel("searchresults.xlsx")
