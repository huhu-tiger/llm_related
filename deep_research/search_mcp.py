from mcp.server.fastmcp import FastMCP
import requests
from openai import OpenAI
mcp = FastMCP("search")
import pandas as pd
from prompts import *
import logging
import config


base_url = config.base_url
api_key = config.api_key
model_name = config.model_name

vl_base_url = config.vl_base_url
vl_model_name = config.vl_model_name

# 创建日志记录器
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# 创建控制台处理器
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)

# 创建文件处理器
file_handler = logging.FileHandler('test.log')
file_handler.setLevel(logging.INFO)
file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

client = OpenAI(
            base_url=base_url,
            api_key=api_key,
        )

vl_client = OpenAI(
            base_url=vl_base_url,
            api_key=api_key,
        )

def generate_query(query, stream=False):
    prompt ="""You are an expert research assistant. Given the user's query, generate up to four distinct, precise search queries that would help gather comprehensive information on the topic.
    Return only a Python list of strings, for example: ['query1', 'query2', 'query3']."""
        
    response = client.chat.completions.create(
                    model=model_name,
                    messages = [
        {"role": "system", "content": "You are a helpful and precise research assistant."},
        {"role": "user", "content": f"User Query: {query}\n\n{prompt}"}
    ]
                )
    return response.choices[0].message.content


def if_useful(query: str, page_text: str):
    prompt ="""You are a critical research evaluator. Given the user's query and the content of a webpage, determine if the webpage contains information relevant and useful for addressing the query.
    Respond with exactly one word: 'Yes' if the page is useful, or 'No' if it is not. Do not include any extra text."""
    
    response = client.chat.completions.create(
                    model=model_name,
                    messages = [
        {"role": "system", "content": "You are a strict and concise evaluator of research relevance."},
        {"role": "user", "content": f"User Query: {query}\n\nWebpage Content (first 20000 characters):\n{page_text[:20000]}\n\n{prompt}"}
    ]
                )
    
    response = response.choices[0].message.content
    
    if response:
        answer = response.strip()
        if answer in ["Yes", "No"]:
            return answer
        else:
            # Fallback: try to extract Yes/No from the response.
            if "Yes" in answer:
                return "Yes"
            elif "No" in answer:
                return "No"
    return "No"

def extract_relevant_context(query, search_query, page_text):
    prompt ="""You are an expert information extractor. Given the user's query, the search query that led to this page, and the webpage content, extract all pieces of information that are relevant to answering the user's query.
    Return only the relevant context as plain text without commentary."""
    
    response = client.chat.completions.create(
                    model=model_name,
                    messages = [
        {"role": "system", "content": "You are an expert in extracting and summarizing relevant information."},
        {"role": "user", "content": f"User Query: {query}\nSearch Query: {search_query}\n\nWebpage Content (first 20000 characters):\n{page_text[:20000]}\n\n{prompt}"}
    ]
                )
    
    response = response.choices[0].message.content
    if response:
        return response.strip()
    return ""

def get_new_search_queries(user_query, previous_search_queries, all_contexts):
    context_combined = "\n".join(all_contexts)
    prompt ="""You are an analytical research assistant. Based on the original query, the search queries performed so far, and the extracted contexts from webpages, determine if further research is needed.
    If further research is needed, provide up to four new search queries as a Python list (for example, ['new query1', 'new query2']). If you believe no further research is needed, respond with exactly .
    Output only a Python list or the token  without any additional text."""
    
    response = client.chat.completions.create(
                    model=model_name,
                    messages = [
        {"role": "system", "content": "You are an expert in extracting and summarizing relevant information."},
        {"role": "user", "content": f"User Query: {user_query}\nPrevious Search Queries: {previous_search_queries}\n\nExtracted Relevant Contexts:\n{context_combined}\n\n{prompt}"}
    ]
                )
    
    response = response.choices[0].message.content
    if response:
        cleaned = response.strip()
        if cleaned == "":
            return ""
        try:
            new_queries = eval(cleaned)
            if isinstance(new_queries, list):
                return new_queries
            else:
                logger.info(f"LLM did not return a list for new search queries. Response: {response}")
                return []
        except Exception as e:
            logger.error(f"Error parsing new search queries:{e}, Response:{response}")
            return []
    return []


# Reorganized this function, integrated get_images calls, and set top_k as a parameter
def web_search(query: str, top_k: int = 2, categories: str = 'general') -> list:
    
    try:
        logger.info(f"Searching for '{query}' with categories='{categories}', top_k={top_k}")
        response = requests.get(f'{config.search_base_url}/search?format=json&q={query}&language=zh-CN&time_range=&safesearch=0&categories={categories}', timeout=10)
        
        if response.status_code != 200:
            logger.error(f"Search API returned status code {response.status_code}")
            return []
            
        results = response.json()['results']
        links = []
        
        for result in results[:top_k]:
            if categories == 'general':
                links.append(result.get('url', ''))
            elif categories == 'images':
                links.append(result.get('img_src', ''))
            else:
                links.append(result.get('url', ''))
        
        logger.info(f"Found {len(links)} links for query '{query}'")
        return links
        
    except requests.exceptions.Timeout:
        logger.error(f"Timeout while searching for '{query}'")
        return []
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error while searching for '{query}': {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error while searching for '{query}': {e}")
        return []
    

def fetch_webpage_text(url):
    JINA_BASE_URL = 'https://r.jina.ai/'
    full_url = f"{JINA_BASE_URL}{url}"
    
    try:
        resp = requests.get(full_url, timeout=50)
        if resp.status_code == 200:
            return resp.text
        else:
            text = resp.text
            logger.info(f"Jina fetch error for {url}: {resp.status_code} - {text}")
            return ""
    except Exception as e:
        logger.error(f"Error fetching webpage text with Jina:{e}")
        return ""


def process_link(link, query, search_query):
    logger.info(f"Fetching content from: {link}")
    page_text = fetch_webpage_text(link)
    if not page_text:
        return None
    usefulness = if_useful(query, page_text)
    logger.info(f"Page usefulness for {link}: {usefulness}")
    if usefulness == "Yes":
        context = extract_relevant_context(query, search_query, page_text)
        if context:
            logger.info(f"Extracted context from {link} (first 200 chars): {context[:200]}")
            return context
    return None


def get_images_description(iamge_url):
    try:
        logger.info(f"Getting description for image: {iamge_url}")
        completion = vl_client.chat.completions.create(
            model=vl_model_name,
            messages=[
                {
                "role": "user",
                "content": [
                    {
                    "type": "text",
                    "text": "使用一句话描述图片的内容"
                    },
                    {
                    "type": "image_url",
                    "image_url": {
                        "url": iamge_url
                    }
                    }
                ]
                }
            ],
            timeout=30  # 添加30秒超时
        )
        description = completion.choices[0].message.content
        logger.info(f"Successfully got description: {description}")
        return description
    except Exception as e:
        logger.error(f"Error getting image description for {iamge_url}: {e}")
        return f"无法获取图片描述: {str(e)}"

@mcp.tool()
def search(query: str) -> str:
    """互联网搜索"""
    iteration_limit = config.iteration_limit
    iteration = 0
    aggregated_contexts = []  
    all_search_queries = []   
    iteration = 0
    
    new_search_queries = eval(generate_query(query))
    all_search_queries.extend(new_search_queries)
    # add the original query to the search queries in case it is not already in the list
    if query not in all_search_queries:
        all_search_queries.append(query)
    while iteration < iteration_limit:
            logger.info(f"\n=== Iteration {iteration + 1} ===")
            iteration_contexts = []
            search_results = [web_search(query, top_k=2, categories='general') for query in new_search_queries]

            unique_links = {}
            for idx, links in enumerate(search_results):
                search_query = new_search_queries[idx]  # prevent the query being replaced as the Search parameter
                for link in links:
                    if link not in unique_links:
                        unique_links[link] = search_query

            logger.info(f"Aggregated {len(unique_links)} unique links from this iteration.")

            # Process each link concurrently: fetch, judge, and extract context.
            link_results = [
                process_link(link, query, unique_links[link])
                for link in unique_links
            ]
            
            # Collect non-None contexts.
            for res in link_results:
                if res:
                    iteration_contexts.append(res)

            if iteration_contexts:
                aggregated_contexts.extend(iteration_contexts)
            else:
                logger.info("No useful contexts were found in this iteration.")

            new_search_queries = get_new_search_queries(query, all_search_queries, aggregated_contexts)
            if new_search_queries == "":
                logger.info("LLM indicated that no further research is needed.")
                break
            elif new_search_queries:
                logger.info(f"LLM provided new search queries:{new_search_queries}")
                all_search_queries.extend(new_search_queries)
            else:
                logger.info("LLM did not provide any new search queries. Ending the loop.")
                break

            iteration += 1
    return '\n\n'.join(aggregated_contexts)

@mcp.tool()
def get_images(query: str) -> dict:
    '''获取图片链接和描述'''
    logger.info(f"Searching for images for query: {query}")
    
    try:
        # Get image links directly through web_search function
        img_srcs = web_search(query, top_k=2, categories='images')
        logger.info(f"Found {len(img_srcs)} image sources: {img_srcs}")
        
        if not img_srcs:
            logger.warning("No images found for the query")
            return {}
        
        result = {}
        
        for i, img_src in enumerate(img_srcs):
            try:
                logger.info(f"Processing image {i+1}/{len(img_srcs)}: {img_src}")
                description = get_images_description(img_src)
                logger.info(f"Image description for {img_src}: {description}")
                result[img_src] = description
            except Exception as e:
                logger.error(f"Error processing image {img_src}: {e}")
                result[img_src] = f"Error: {str(e)}"
        
        logger.info(f"Successfully processed {len(result)} images")
        return result
        
    except Exception as e:
        logger.error(f"Error in get_images function: {e}")
        return {"error": f"Failed to get images: {str(e)}"}
    
  

if __name__ == "__main__":
    mcp.run()

