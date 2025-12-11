"""Apify Actor for converting web pages to clean Markdown for LLMs and RAG.

This Actor scrapes web pages and converts them into clean, token-efficient Markdown
optimized for Large Language Models (LLMs) and Retrieval Augmented Generation (RAG) systems.

To build Apify Actors, utilize the Apify SDK toolkit, read more at the official documentation:
https://docs.apify.com/sdk/python
"""

from __future__ import annotations

from apify import Actor
from crawlee.crawlers import BeautifulSoupCrawler, BeautifulSoupCrawlingContext
from readability import Document
from markdownify import markdownify as md


async def main() -> None:
    """Define the main entry point for the Apify Actor.

    This coroutine is executed using `asyncio.run()`, so it must remain an asynchronous function for proper execution.
    Asynchronous execution is required for communication with Apify platform.
    """
    async with Actor:
        # Get input from Apify
        actor_input = await Actor.get_input() or {}
        
        start_urls = [
            url.get('url') for url in actor_input.get('start_urls', [{'url': 'https://apify.com'}])
        ]
        include_links = actor_input.get('include_links', True)
        
        # Exit if no start URLs are provided
        if not start_urls:
            Actor.log.info('No URLs provided in start_urls, exiting...')
            await Actor.exit()
        
        Actor.log.info(f'Processing {len(start_urls)} URLs')
        Actor.log.info(f'Include links: {include_links}')
        
        # Create a crawler
        crawler = BeautifulSoupCrawler(
            max_requests_per_crawl=len(start_urls),
        )
        
        # Define the request handler
        @crawler.router.default_handler
        async def request_handler(context: BeautifulSoupCrawlingContext) -> None:
            url = context.request.url
            Actor.log.info(f'Scraping {url}...')
            
            try:
                # Get the raw HTML from the response
                html_content = str(context.soup)
                
                # Extract main content using readability
                doc = Document(html_content)
                title = doc.title()
                clean_html = doc.summary()
                
                # Convert to Markdown
                markdown_content = md(
                    clean_html,
                    heading_style='ATX',
                    bullets='-',
                    strip=['script', 'style'],
                    convert=None if include_links else ['a']
                )
                
                # Clean up excessive whitespace
                markdown_content = '\n'.join(
                    line for line in markdown_content.split('\n') if line.strip()
                )
                
                # Prepare data
                data = {
                    'url': url,
                    'title': title,
                    'markdown_content': markdown_content
                }
                
                Actor.log.info(f'Successfully converted: {title}')
                
                # Push to dataset
                await context.push_data(data)
                
            except Exception as e:
                Actor.log.error(f'Error processing {url}: {str(e)}')
        
        # Run the crawler
        await crawler.run(start_urls)
