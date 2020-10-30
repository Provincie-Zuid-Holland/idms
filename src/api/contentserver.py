import requests
import logging
import time
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from functools import reduce

def dotfield(input_dict: dict, input_key: str) -> str:
    """
    Magic function to get nested properties from dictionary writen as level1.level2.level3.
    
    Example: 
    dotfield({"a": {"b": {"c": "def"}}}, "a.b.c") -> "def"
    """
    return reduce(lambda d, k: d.get(k) if d else None, input_key.split("."), input_dict)

class crawler:
    def __init__(self, baseUrl, username=None, password=None, ticket=None):
        
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

        self.folders = ['/img/webdoc/folder.gif', '/img/folder_icons/folder24.gif', '/img/folder_icons/folderblauw_v2.gif', '/img/folder_icons/folder9.gif', \
            '/img/otemail/emailfolder.gif']

        self.outputColumns = ['parent_id', 'id', 'wnd_version', 'create_date', 'modify_date', 'wnd_owner', 'wnd_createdby', 'name', 'icon', 'type_name']

        if ticket:
            self.ticket = ticket
        else:
            self.ticket = self.authorize(username, password)

    def authorize(self, username, password) -> str: 
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
    
    def children(self, nodeId) -> list:
        """
        Recursive function to craw children of node.
        """
        headers = {'otcsticket': self.ticket}
        page = 1
        counter = 1
        limit = 100
        page_total = 9999999999999
        results = []
        while page <= page_total and counter < self.maxCallsPerFolder:
            counter = counter + 1
            url = self.baseUrl + f"/api/v1/nodes/{nodeId}/nodes?limit={limit}&page={page}"  
            logging.debug(f'url: {url}')
            logging.debug(headers)
            r = self.session.get(url, headers=headers, timeout=60*30)
            r.raise_for_status()
            page = page + 1 
            data = r.json()
            page_total = data['page_total']
            for dataRow in data.get('data', []):
                if dataRow.get('icon') in self.folders:
                    time.sleep(self.gracefulSleepSeconds)
                    childs = self.children(dataRow.get('id'))
                    results = results + childs
                row = {}
                for colName in self.outputColumns:
                    row[colName] = dotfield(dataRow, colName)
                results.append(row)
        
        
        return results 
