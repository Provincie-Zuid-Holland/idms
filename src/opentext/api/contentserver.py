import requests
import logging
import json
import datetime, time
import copy
import opentext.functions as otfunc
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from functools import reduce

def dotfield(input_dict: dict, input_key: str, notFound=None) -> str:
    """
    Magic function to get nested properties from dictionary writen as level1.level2.level3.
    
    Example: 
    dotfield({"a": {"b": {"c": "def"}}}, "a.b.c") -> "def"
    """
    return reduce(lambda d, k: d.get(k) if d else notFound, input_key.split("."), input_dict)

class crawler:
    def __init__(self, baseUrl: str, username: str = None, password: str = None, ticket: str = None):
        
        # Settings for retry and auto retry if error code 500 is given
        retry = Retry(
            total=5,
            read=5,
            connect=5,
            backoff_factor=0.3,
            status_forcelist=(500, 502, 504),
        )

        # Mounts a session for re-use authorization
        self.baseUrl = baseUrl
        self.session = requests.Session()
        self.session.mount(baseUrl, HTTPAdapter(max_retries=retry))

        # Safety measures to not to overload the server.
        self.maxCallsPerFolder = 10000
        self.gracefulSleepSeconds = 0.01

        self.folderTypes = [0]

        self.includeParentsPath = True
        self.outputColumns = ['properties.parent_id', 'properties.id', 'properties.size', 'properties.create_date', 'properties.modify_date', 'properties.owner', 'properties.create_user_id', 'properties.name', 'properties.type', 'properties.type_name']

        self.debugJson = True

        if ticket:
            self.ticket = ticket
        else:
            self.ticket = self.authorize(username, password)

    def authorize(self, username: str, password: str) -> str: 
        """
        Function to authenticate yourself and get token for future requests.
        """
        url = self.baseUrl + '/api/v1/auth'
        body = {u'username': username, u'password': password}
        response = self.session.post(url, data=body)
        try:
            r = response.json()
            return r.get('ticket')
        except:
            print(response)
            raise Exception('Username or password not correct!')
     
    def flattenParents(self, listParents: list, lastNode: str = None) -> str:
        """
        Function to concat parents to string.
        listParents: [] (list)
        lastNode: DocumentName (str)
        Example: Central > Map 1 > Map 2 > DocumentName
        """
        joinedString = " > ".join([a.get('name') for a in listParents])
        if lastNode:
            return joinedString + " > " + str(lastNode)
        else:
            return joinedString
    
    def parents(self, nodeId: str) -> list:
        """
        Recursive function to craw all parents of node.
        """
        headers = {'otcsticket': self.ticket}

        url = self.baseUrl + f"/api/v1/nodes/{nodeId}/ancestors"  
        logging.debug(f'url: {url}')
        logging.debug(headers)
        r = self.session.get(url, headers=headers, timeout=60*30)
        r.raise_for_status()
        data = r.json()
        print(data)
        return data.get('ancestors', [])

    def parseNodeColumns(self, dataRow: dict, parents: list = None) -> dict:
        """
        Reduce dict to only usefull output columns based on: `self.outputColumns`
        """
        row = {}

        nodeId = dotfield(dataRow, "properties.id")
        row['downloadUrl'] = f"/otcs/llisapi.dll?func=ll&objId={nodeId}&objAction=download"
        row['viewUrl'] = f"/otcs/llisapi.dll?func=ll&objId={nodeId}&objAction=browse"
        row['nodeType'] = otfunc.mimetype2FileType(dotfield(dataRow, "properties.mime_type"))
        for colName in self.outputColumns:
            row[colName] = dotfield(dataRow, colName)
        
        if self.includeParentsPath:
            row['locationPathString'] = self.flattenParents(parents, dotfield(dataRow, 'properties.name'))

        return row
    
    def children(self, nodeId: str, parents: list = None) -> list:
        """
        Recursive function to craw children of node.
        """
        headers = {'otcsticket': self.ticket}

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
            logging.debug(f'url: {url}')
            logging.debug(headers)
            r = self.session.get(url, headers=headers, timeout=60*30)
            r.raise_for_status()
            page = page + 1 
            data = r.json()
            if self.debugJson:
                yyyymmddhhmmss = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
                with open(f"debug_{yyyymmddhhmmss}.json", "w") as f:
                    json.dump(data, f)

            page_total = dotfield(data, "collection.paging.page_total", 0)
            for result in data.get('results', []):
                dataRow = result.get('data')
                if dotfield(dataRow, "properties.type") in self.folderTypes:
                    time.sleep(self.gracefulSleepSeconds)
                    # Recursive call
                    newParents = copy.deepcopy(parents)
                    newParents.append({'id': dotfield(dataRow, "properties.id"), 'name': dotfield(dataRow, "properties.name"), 'parent_id': dotfield(dataRow, "properties.parent_id"), 'type': dotfield(dataRow, "properties.type"), 'volume_id': dotfield(dataRow, "properties.volume_id"), 'type_name': dotfield(dataRow, "properties.type_name")})
                    childs = self.children(dotfield(dataRow, "properties.id"), newParents)
                    results = results + childs
                
                row = self.parseNodeColumns(dataRow, parents)

                results.append(row)
        
        
        return results 
