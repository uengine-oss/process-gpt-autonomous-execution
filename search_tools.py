import json
import os

import requests
from langchain.tools import tool


class SearchTools():

  @tool("Search Internal Documents")
  def search_internal_documents(query):
    """Useful to search internal documents based on a given query and return relevant results"""
    # url = "http://localhost:8005/retrieve"
    url = "http://memento.process-gpt.io/retrieve"
    payload = json.dumps({"query": query})
    headers = {
        'content-type': 'application/json'
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    results = response.json()
    string = []
    for item in results:
        node = item['node']
        metadata = node['metadata']
        content = node['text']
        metadata_str = '\n'.join([f"{key}: {value}" for key, value in metadata.items()])
        string.append('\n'.join([
            metadata_str,
            "Content:",
            content,
            "\n-----------------"
        ]))

    return '\n'.join(string)

  @tool("Search the internet")
  def search_internet(query):
    """Useful to search the internet 
    about a a given topic and return relevant results"""
    top_result_to_return = 4
    url = "https://google.serper.dev/search"
    payload = json.dumps({"q": query})
    headers = {
        'X-API-KEY': os.getenv('SERPER_API_KEY', ''),
        'content-type': 'application/json'
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    results = response.json()['organic']
    string = []
    for result in results[:top_result_to_return]:
      try:
        string.append('\n'.join([
            f"Title: {result['title']}", f"Link: {result['link']}",
            f"Snippet: {result['snippet']}", "\n-----------------"
        ]))
      except KeyError:
        next

    return '\n'.join(string)

  @tool("Search news on the internet")
  def search_news(query):
    """Useful to search news about a company, stock or any other
    topic and return relevant results"""""
    top_result_to_return = 4
    url = "https://google.serper.dev/news"
    payload = json.dumps({"q": query})
    headers = {
        'X-API-KEY': os.getenv('SERPER_API_KEY', ''),
        'content-type': 'application/json'
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    results = response.json()['news']
    string = []
    for result in results[:top_result_to_return]:
      try:
        string.append('\n'.join([
            f"Title: {result['title']}", f"Link: {result['link']}",
            f"Snippet: {result['snippet']}", "\n-----------------"
        ]))
      except KeyError:
        next

    return '\n'.join(string)
