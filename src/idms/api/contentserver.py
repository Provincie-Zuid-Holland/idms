import copy
import datetime
import json
import logging
import os
import time
from functools import reduce
from urllib.parse import parse_qs, urlparse, urlunparse
from urllib.request import pathname2url

import numpy as np
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

import idms.functions as otfunc


def dotfield(input_dict: dict, input_key: str, notFound=None) -> str:
    """
    Magic function to get nested properties from dictionary writen as level1.level2.level3.

    Example:
    dotfield({"a": {"b": {"c": "def"}}}, "a.b.c") -> "def"

    TODO: Add support for list (error: AttributeError: 'list' object has no attribute 'get')
    """
    try:
        return reduce(lambda d, k: d.get(k) if d else notFound, input_key.split("."), input_dict)
    except Exception as err:
        logging.debug(f"Dotfield error: {err}\n{input_key}")
        return ""


class crawler:
    def __init__(
        self,
        baseUrl: str,
        username: str = None,
        password: str = None,
        ticket: str = None,
        verifySSL: bool = True,
        maxErrorRetry: int = 10,
        post_error_retries: int = 10,
    ):
        # Settings for retry and auto retry if error code 500 is given
        retry = Retry(
            total=post_error_retries,
            read=post_error_retries,
            connect=post_error_retries,
            backoff_factor=1,
            status_forcelist=(500, 502, 503, 504),
        )

        # Mounts a session for re-use authorization
        self.baseUrl = baseUrl
        self.session = requests.Session()
        self.session.verify = verifySSL
        self.session.mount(baseUrl, HTTPAdapter(max_retries=retry))

        # Safety measures to not to overload the server.
        self.maxCallsPerFolder = 10000
        self.gracefulSleepSeconds = 0.01

        # Type 0 is always a folder, 751 is for ProvZH and E-mailmap and 136 for Samengesteld document and 298 for a Collectie.
        self.folderTypes = [0, 751, 136, 298]
        self.folderTypesStopRecursive = [136, 298]

        self.includeParentsPath = True
        self.outputColumns = [
            "properties.parent_id",
            "properties.id",
            "properties.size",
            "properties.create_date",
            "properties.modify_date",
            "properties.owner",
            "properties.create_user_id",
            "properties.name",
            "properties.description",
            "properties.type",
            "properties.type_name",
            "properties.summary",
            "properties.description_multilingual.nl",
            "regions.OTLocation",
            "systemattributes.Dossiernummer",
        ]

        self.debugJson = True

        # Retry faulty urls, extra fall back when it's not a HTTP code.
        self.maxErrorRetry = maxErrorRetry

        if ticket:
            self.ticket = ticket
        else:
            self.ticket = self.authorize(username, password)

    def authorize(self, username: str, password: str) -> str:
        """
        Function to authenticate yourself and get token for future requests.
        """
        url = self.baseUrl + "/api/v1/auth"
        body = {"username": username, "password": password}
        response = self.session.post(url, data=body)
        try:
            r = response.json()
            error = r.get("error")
            if error:
                raise Exception("Username or password not correct!")
            else:
                logging.info("Succesfull logged in to ContentServer.")
            return r.get("ticket")
        except:
            print(response)
            raise Exception("Username or password not correct!")

    def flattenParents(self, listParents: list, lastNode: str = None) -> str:
        """
        Function to concat parents to string.
        listParents: [] (list)
        lastNode: DocumentName (str)
        Example: Central > Map 1 > Map 2 > DocumentName
        """
        joinedString = " > ".join([a.get("name") for a in listParents])
        if lastNode:
            return joinedString + " > " + str(lastNode)
        else:
            return joinedString

    def parents(self, nodeId: str) -> list:
        """
        Recursive function to craw all parents of node.
        """
        headers = {"otcsticket": self.ticket}

        url = self.baseUrl + f"/api/v1/nodes/{nodeId}/ancestors"
        logging.debug(f"url: {url}")
        logging.debug(headers)
        r = self.session.get(url, headers=headers, timeout=60 * 30)
        r.raise_for_status()
        data = r.json()
        return data.get("ancestors", [])

    def parseNodeColumns(self, dataRow: dict, parents: list = []) -> dict:
        """
        Reduce dict to only usefull output columns based on: `self.outputColumns`
        """
        row = {}

        nodeId = dotfield(dataRow, "properties.id")
        row["downloadUrl"] = f"/otcs/llisapi.dll?func=ll&objId={nodeId}&objAction=download"
        row["viewUrl"] = f"/otcs/llisapi.dll?func=ll&objId={nodeId}&objAction=browse"
        row["nodeType"] = otfunc.mimetype2FileType(dotfield(dataRow, "properties.mime_type"))
        for colName in self.outputColumns:
            row[colName] = dotfield(dataRow, colName)

        if self.includeParentsPath:
            row["locationPathString"] = self.flattenParents(parents)

        return row

    def children(self, nodeId: str, parents: list = None, stopRecursive: bool = False) -> list:
        """
        Recursive function to craw children of node.
        """
        headers = {"otcsticket": self.ticket}

        if not parents and self.includeParentsPath:
            parents = self.parents(nodeId)
        page = 1
        counter = 1
        limit = 100
        page_total = 9999999999999
        results = []
        while page <= page_total and counter < self.maxCallsPerFolder:
            counter = counter + 1
            url = self.baseUrl + f"/api/v2/nodes/{nodeId}/nodes?limit={limit}&page={page}"
            logging.debug(f"url: {url}")
            logging.debug(headers)
            r = self.session.get(url, headers=headers, timeout=60 * 30)
            r.raise_for_status()
            page = page + 1
            data = r.json()
            if self.debugJson:
                yyyymmddhhmmss = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
                with open(f"debug_{yyyymmddhhmmss}.json", "w") as f:
                    json.dump(data, f)

            page_total = dotfield(data, "collection.paging.page_total", 0)
            for result in data.get("results", []):
                dataRow = result.get("data")

                # Check if a node is a folder type. Some folder types are collections of other nodes
                # the risk of recursive call a collection is that it can end in an infinity loop.
                # folderTypesStopRecursive is a list of collectiontypes and children will be fetched.
                # If there are also subfolders in that collection it won't fetch further.
                if dotfield(dataRow, "properties.type") in self.folderTypes and stopRecursive == False:
                    time.sleep(self.gracefulSleepSeconds)
                    # Recursive call
                    newParents = copy.deepcopy(parents)
                    newParents.append(
                        {
                            "id": dotfield(dataRow, "properties.id"),
                            "name": dotfield(dataRow, "properties.name"),
                            "parent_id": dotfield(dataRow, "properties.parent_id"),
                            "type": dotfield(dataRow, "properties.type"),
                            "volume_id": dotfield(dataRow, "properties.volume_id"),
                            "type_name": dotfield(dataRow, "properties.type_name"),
                        }
                    )
                    if dotfield(dataRow, "properties.type") in self.folderTypesStopRecursive:
                        stopRecursive = True
                    else:
                        stopRecursive = False
                    childs = self.children(dotfield(dataRow, "properties.id"), newParents, stopRecursive)
                    results = results + childs

                row = self.parseNodeColumns(dataRow, parents)

                results.append(row)

        if counter >= self.maxCallsPerFolder:
            raise Exception(
                f"Stopped due counter ({counter}) reached the maxCallsPerFolder ({self.maxCallsPerFolder}) limit!"
            )

        return results

    def search(
        self,
        complexQuery: str,
        limit: int = 10,
        metadata: str = "true",
        slice: str = None,
        resume_last_position=True,
    ) -> list:
        """
        Search API endpoint
        Example: {self.baseUrl}/api/v2/search?where=`complexQuery`&limit=`limit`&metadata=`metadata`

        :param str `complexQuery`:  See documentation for search options for a complexQuery: https://docs2.cer-rec.gc.ca/ll-eng/llisapi.dll?func=help.index&keyword=LL.Search%20Broker.Category
        """

        file_path_resume = os.getcwd() + "/" + pathname2url(complexQuery)[0:15] + "_last_position.txt"

        results = np.array([])
        headers = {"otcsticket": self.ticket}
        counter = 0

        if os.path.exists(file_path_resume) and resume_last_position is True:
            with open(file_path_resume, "r") as file:
                url = file.read()
        else:
            url = self.baseUrl + "/api/v2/search"

        max_error_retries = 0

        base_data = {"where": complexQuery, "limit": limit, "metadata": metadata}
        if slice:
            base_data["slice"] = slice

        # Retrieve all pages of certain search query using a while loop with security of maxCallsPerFolder variable.
        while url != "" and counter < self.maxCallsPerFolder and max_error_retries < self.maxErrorRetry:
            try:
                counter = counter + 1
                data = base_data.copy()
                # Query Content Server API to search for params
                if "?" in url:
                    post_url, params = url.split("?")

                    # Split the query string on the '&' character
                    query_params = params.split("&")

                    # Loop through each key-value pair and add it to the dictionary
                    for param in query_params:
                        key, value = param.split("=")
                        data[key] = value
                else:
                    post_url = url

                logging.debug(data)

                # The post might sometimes fail thus stop the whole process, i have added a retry if the post fails to try again, this seems to work
                r = self.session.post(post_url, headers=headers, timeout=60 * 30, data=data)
                r.raise_for_status()
                search_results = r.json()

                if self.debugJson:
                    yyyymmddhhmmss = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
                    with open(f"debug_{yyyymmddhhmmss}.json", "w") as f:
                        json.dump(search_results, f)

                # Extract only relevant columns from search results
                for result in search_results.get("results", []):
                    dataRow = result.get("data")
                    row = self.parseNodeColumns(dataRow)

                    ancestorsList = dotfield(result, "links.ancestors", [])
                    ancestorsStr = " > ".join([a.get("name") for a in ancestorsList])
                    row["locationPathString"] = ancestorsStr
                    row["complexQuery"] = complexQuery
                    results = np.append(results, row)

                # Determine if there is a next page and prepare for next while-loop.
                # nextUrl contains a GET url to retrieve the next page.
                nextUrl = dotfield(search_results, "collection.paging.links.next.href")

                logging.debug(f" > nextUrl: {nextUrl}")

                if nextUrl:
                    url = self.baseUrl + nextUrl
                    with open(file_path_resume, "w") as file:
                        file.write(str(url))
                else:
                    url = ""

            except Exception as e:
                max_error_retries = max_error_retries + 1
                print(e)
                logging.debug("Error: " + str(e))

        # Inform the user that the max error retries has been met.
        if max_error_retries >= self.maxErrorRetry:
            logging.warning(
                f"Stopped due max error tries: ({max_error_retries}) reached the max error retry ({self.maxErrorRetry}) limit!"
            )
            with open(file_path_resume, "w") as file:
                file.write(str(url))

        # Inform user if stopped earlier due maxCallsPerFolder variable
        if counter >= self.maxCallsPerFolder:
            logging.warning(
                f"Stopped due counter ({counter}) reached the maxCallsPerFolder ({self.maxCallsPerFolder}) limit!"
            )
            with open(file_path_resume, "w") as file:
                file.write(str(url))

        return results.tolist()
