#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main application to scrape IDMS

Original script: scrape.py in wob_idms_scraper
Adapted by: Joana Cardoso
"""

import argparse, getpass, logging, datetime, os
import pandas as pd
import opentext.api.contentserver as cs

def parse_args():
    parser = argparse.ArgumentParser(description='Application to Search in IDMS and list results')
    parser.add_argument('--idms_username', type = str, help = 'Username to login in IDMS')
    parser.add_argument('--idms_password', type = str, help = 'Password to login in IDMS')
    # parser.add_argument('--storeResults', default=True, action='store_true', help='Boolean if you like to store results in database')
    parser.add_argument('--ticket', type = str, default = False, help = 'Specify valid ticket (skip auth)')
    parser.add_argument('--startNode', default = 723909139, type = int, help = 'Node to start the crawler from. It will recursivly scan all underling folders.')
    # parser.add_argument('--skipBigSearchResultsInt', default=None, type = int, help = 'If search gives more then x results. Skip it.')
    # parser.add_argument('--name_json', type = str, default = 'json/metadata_DBI_65000_6', help = 'Specify the name of the json file to create')
    # parser.add_argument('--name_summary', type = str, default = 'total_files/total_files_DBI_65000_6', help = 'Specify the name of summary excel file to create')
    # parser.add_argument('--max_results', type = int, default = 30000, help = 'Set the maximum number of results to save')
    parser.add_argument("--verbose", action="store_true", help="increase output verbosity")
    return parser.parse_args()

def main():
    global ARGS
    baseUrl = os.getenv("BASE_URL") # Acceptatie

    startNode = ARGS.startNode
    if ARGS.ticket:
        ticket = ARGS.ticket
        idms = cs.crawler(baseUrl, ticket=ticket)
    else:
        idms_username = ARGS.idms_username or getpass.getpass(prompt='IDMS username:')
        idms_password = ARGS.idms_password or getpass.getpass(prompt='IDMS password:')
        idms = cs.crawler(baseUrl, idms_username, idms_password)

    idms.debugJson = True
    arr = idms.children(startNode)
    df = pd.DataFrame(arr)
    print(df)
    df.to_excel('idmsscraper.xlsx')
    parents = idms.parents(startNode)
    df = pd.DataFrame(parents)
    print(df)
    print(idms.flattenParents(parents, "TEST-STRING"))


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(verbose=True)   

    t1 = datetime.datetime.now()
    ARGS = parse_args()
    if ARGS.verbose:
        logging.basicConfig()
        logging.getLogger().setLevel(logging.DEBUG)
    main()
    t2 = datetime.datetime.now()
    print(f'Elapsed time: {t2-t1}')