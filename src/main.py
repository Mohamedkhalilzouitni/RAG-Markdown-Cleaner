"""Apify Actor for converting web pages to clean Markdown for LLMs and RAG.

This Actor scrapes web pages and converts them into clean, token-efficient Markdown
optimized for Large Language Models (LLMs) and Retrieval Augmented Generation (RAG) systems.

To build Apify Actors, utilize the Apify SDK toolkit, read more at the official documentation:
https://docs.apify.com/sdk/python
"""

from __future__ import annotations

import re
import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime
from urllib.parse import urlparse, urljoin

from apify import Actor
from crawlee.crawlers import BeautifulSoupCrawler, BeautifulSoupCrawlingContext
from readability import Document
from markdownify import markdownify as md


def estimate_tokens(text: str) -> int:
    """Estimate token count (rough approximation: 1 token ≈ 4 chars)."""
    return len(text) // 4


def create_chunks(markdown: str, max_chunk_size: int = 1000, overlap: int = 100) -> List[Dict[str, Any]]:
    """
    Split markdown content into semantic chunks while preserving context.
    
    Args:
        markdown: The markdown content to chunk
        max_chunk_size: Maximum characters per chunk
        overlap: Number of characters to overlap between chunks
        
    Returns:
        List of chunk dictionaries with metadata
    """
    chunks = []
    
    # Split by headings to preserve semantic structure
    sections = re.split(r'(\n#{1,6}\s+.+\n)', markdown)
    
    current_chunk = ""
    current_heading_context = []
    chunk_id = 1
    
    for i, section in enumerate(sections):
        # Check if this is a heading
        heading_match = re.match(r'\n(#{1,6})\s+(.+)\n', section)
        
        if heading_match:
            level = len(heading_match.group(1))
            heading_text = heading_match.group(2).strip()
            
            # Update heading context (breadcrumb trail)
            current_heading_context = current_heading_context[:level-1]
            current_heading_context.append(heading_text)
            
            # Add heading to current chunk
            if len(current_chunk) + len(section) < max_chunk_size:
                current_chunk += section
            else:
                # Save current chunk if it has content
                if current_chunk.strip():
                    chunks.append({
                        'chunk_id': chunk_id,
                        'content': current_chunk.strip(),
                        'heading_context': ' > '.join(current_heading_context[:-1]) if len(current_heading_context) > 1 else '',
                        'char_count': len(current_chunk),
                        'estimated_tokens': estimate_tokens(current_chunk)
                    })
                    chunk_id += 1
                
                # Start new chunk with overlap
                if overlap > 0 and current_chunk:
                    overlap_text = current_chunk[-overlap:]
                    current_chunk = overlap_text + section
                else:
                    current_chunk = section
        else:
            # Regular content
            if not section.strip():
                continue
                
            # If adding this would exceed max size, split it
            if len(current_chunk) + len(section) > max_chunk_size:
                # Save current chunk
                if current_chunk.strip():
                    chunks.append({
                        'chunk_id': chunk_id,
                        'content': current_chunk.strip(),
                        'heading_context': ' > '.join(current_heading_context),
                        'char_count': len(current_chunk),
                        'estimated_tokens': estimate_tokens(current_chunk)
                    })
                    chunk_id += 1
                
                # Start new chunk with overlap
                if overlap > 0 and current_chunk:
                    overlap_text = current_chunk[-overlap:]
                    current_chunk = overlap_text + section
                else:
                    current_chunk = section
            else:
                current_chunk += section
    
    # Add final chunk
    if current_chunk.strip():
        chunks.append({
            'chunk_id': chunk_id,
            'content': current_chunk.strip(),
            'heading_context': ' > '.join(current_heading_context),
            'char_count': len(current_chunk),
            'estimated_tokens': estimate_tokens(current_chunk)
        })
    
    return chunks


def extract_metadata(soup, url: str) -> Dict[str, Any]:
    """Extract metadata from the page."""
    metadata = {
        'url': url,
        'domain': urlparse(url).netloc,
        'scraped_at': datetime.utcnow().isoformat() + 'Z',
    }
    
    # Extract author
    author = None
    author_meta = soup.find('meta', {'name': re.compile(r'author', re.I)})
    if author_meta:
        author = author_meta.get('content')
    if not author:
        # Try JSON-LD
        json_ld = soup.find('script', {'type': 'application/ld+json'})
        if json_ld:
            try:
                import json
                data = json.loads(json_ld.string)
                if isinstance(data, dict):
                    author = data.get('author', {}).get('name')
            except:
                pass
    metadata['author'] = author
    
    # Extract publish date
    publish_date = None
    date_meta = soup.find('meta', {'property': 'article:published_time'}) or \
                soup.find('meta', {'name': re.compile(r'publish|date', re.I)})
    if date_meta:
        publish_date = date_meta.get('content')
    metadata['publish_date'] = publish_date
    
    # Extract last modified
    modified_date = None
    modified_meta = soup.find('meta', {'property': 'article:modified_time'}) or \
                    soup.find('meta', {'name': 'last-modified'})
    if modified_meta:
        modified_date = modified_meta.get('content')
    metadata['last_modified'] = modified_date
    
    # Extract language
    lang = soup.find('html').get('lang', 'en') if soup.find('html') else 'en'
    metadata['language'] = lang[:2]  # Just the language code
    
    # Extract keywords
    keywords = []
    keywords_meta = soup.find('meta', {'name': re.compile(r'keywords', re.I)})
    if keywords_meta:
        keywords_content = keywords_meta.get('content', '')
        keywords = [k.strip() for k in keywords_content.split(',') if k.strip()]
    metadata['keywords'] = keywords[:10]  # Limit to 10
    
    # Extract description
    desc_meta = soup.find('meta', {'name': 'description'}) or \
                soup.find('meta', {'property': 'og:description'})
    metadata['description'] = desc_meta.get('content') if desc_meta else None
    
    # Detect content type
    content_type = 'general'
    if '/blog/' in url or '/article/' in url or '/post/' in url:
        content_type = 'blog'
    elif '/docs/' in url or '/documentation/' in url:
        content_type = 'documentation'
    elif '/product/' in url or '/shop/' in url:
        content_type = 'product'
    elif '/wiki/' in url:
        content_type = 'wiki'
    metadata['content_type'] = content_type
    
    return metadata


def resolve_relative_links(markdown: str, base_url: str) -> str:
    """Convert relative URLs to absolute URLs in markdown links."""
    # Pattern to match markdown links: [text](url)
    def replace_link(match):
        text = match.group(1)
        url = match.group(2)
        
        # Skip if already absolute or an anchor
        if url.startswith(('http://', 'https://', '#', 'mailto:', 'tel:')):
            return match.group(0)
        
        # Convert relative to absolute
        absolute_url = urljoin(base_url, url)
        return f'[{text}]({absolute_url})'
    
    # Replace all markdown links
    markdown = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', replace_link, markdown)
    
    return markdown


def extract_code_blocks(markdown: str) -> List[Dict[str, str]]:
    """Extract code blocks from markdown."""
    code_blocks = []
    
    # Pattern for fenced code blocks with optional language
    pattern = r'```(\w+)?\n(.*?)```'
    matches = re.findall(pattern, markdown, re.DOTALL)
    
    for lang, code in matches:
        code_blocks.append({
            'language': lang if lang else 'text',
            'code': code.strip(),
            'lines': len(code.strip().split('\n'))
        })
    
    # Also find inline code blocks
    inline_pattern = r'`([^`]+)`'
    inline_matches = re.findall(inline_pattern, markdown)
    
    return {
        'fenced_blocks': code_blocks,
        'inline_code_count': len(inline_matches),
        'has_code': len(code_blocks) > 0 or len(inline_matches) > 0
    }


def calculate_quality_metrics(markdown: str, html_length: int) -> Dict[str, Any]:
    """Calculate content quality metrics."""
    # Text density (markdown vs HTML ratio)
    text_density = len(markdown) / max(html_length, 1)
    
    # Count paragraphs (non-empty lines that aren't headers/lists)
    lines = [l.strip() for l in markdown.split('\n') if l.strip()]
    paragraphs = [l for l in lines if not l.startswith(('#', '-', '*', '>'))]
    paragraph_count = len([p for p in paragraphs if len(p) > 50])
    
    # Average sentence length
    sentences = re.split(r'[.!?]+', markdown)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
    avg_sentence_length = sum(len(s.split()) for s in sentences) / max(len(sentences), 1)
    
    # Reading time (average reading speed: 200 words/minute)
    word_count = len(markdown.split())
    reading_time_minutes = max(1, round(word_count / 200))
    
    # Check for lists and structure
    has_lists = bool(re.search(r'^\s*[-*+]\s', markdown, re.MULTILINE))
    has_headings = bool(re.search(r'^#{1,6}\s', markdown, re.MULTILINE))
    has_links = bool(re.search(r'\[.+\]\(.+\)', markdown))
    
    return {
        'text_density': round(text_density, 2),
        'paragraph_count': paragraph_count,
        'word_count': word_count,
        'sentence_count': len(sentences),
        'avg_sentence_length': round(avg_sentence_length, 1),
        'reading_time_minutes': reading_time_minutes,
        'has_lists': has_lists,
        'has_headings': has_headings,
        'has_links': has_links,
        'structure_score': sum([has_lists, has_headings, has_links]) / 3.0  # 0-1 score
    }


def generate_content_hashes(markdown: str) -> Dict[str, str]:
    """Generate hashes for deduplication."""
    # Full content hash (SHA256)
    content_hash = hashlib.sha256(markdown.encode('utf-8')).hexdigest()
    
    # Similarity hash (first 16 chars of SHA256 of normalized content)
    # Normalize: lowercase, remove extra whitespace
    normalized = re.sub(r'\s+', ' ', markdown.lower().strip())
    similarity_hash = hashlib.sha256(normalized.encode('utf-8')).hexdigest()[:16]
    
    return {
        'content_hash': content_hash,
        'similarity_hash': similarity_hash
    }


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
                soup = context.soup
                
                # Store original HTML length for quality metrics
                original_html_length = len(str(soup))
                
                # Extract title
                title = soup.title.string if soup.title else 'No Title'
                
                # Extract metadata
                metadata = extract_metadata(soup, url)
                
                # Remove unwanted elements
                for element in soup(['script', 'style', 'nav', 'header', 'footer', 
                                    'iframe', 'noscript', 'svg', 'button', 'form']):
                    element.decompose()
                
                # Remove common noise selectors (cookie banners, ads, etc.)
                noise_selectors = [
                    '[class*="cookie"]', '[class*="banner"]', '[class*="popup"]',
                    '[class*="modal"]', '[id*="cookie"]', '[class*="ad-"]',
                    '[class*="advertisement"]', '[aria-label*="cookie"]'
                ]
                for selector in noise_selectors:
                    for element in soup.select(selector):
                        element.decompose()
                
                # Try readability first for article-like pages
                use_readability = True
                try:
                    html_content = str(soup)
                    doc = Document(html_content)
                    clean_html = doc.summary()
                    
                    # Convert to markdown
                    markdown_content = md(
                        clean_html,
                        heading_style='ATX',
                        bullets='-',
                        strip=['script', 'style', 'img'],
                        convert=None if include_links else ['a'],
                        escape_asterisks=False,
                        escape_underscores=False
                    )
                    
                    # If readability gives very short output, fall back to full body
                    if len(markdown_content.strip()) < 300:
                        raise ValueError("Content too short, using full body")
                        
                except Exception:
                    # Fallback: Convert entire body to markdown
                    use_readability = False
                    Actor.log.info(f'Using full body content for {url}')
                    
                    # Get main content or body
                    main_content = soup.find('main') or soup.find('article') or soup.body or soup
                    
                    markdown_content = md(
                        str(main_content),
                        heading_style='ATX',
                        bullets='-',
                        strip=['script', 'style', 'img'],
                        convert=None if include_links else ['a'],
                        escape_asterisks=False,
                        escape_underscores=False
                    )
                
                # Clean up the markdown
                lines = []
                prev_empty = False
                
                for line in markdown_content.split('\n'):
                    # Strip whitespace
                    line = line.strip()
                    
                    # Skip very short lines that are likely noise (unless they're headers)
                    if len(line) < 3 and not line.startswith('#'):
                        continue
                    
                    # Skip lines with only special characters or numbers
                    if line and all(c in '.-_*[](){}|\\/' for c in line):
                        continue
                    
                    # Avoid consecutive empty lines
                    if not line:
                        if not prev_empty:
                            lines.append('')
                            prev_empty = True
                    else:
                        lines.append(line)
                        prev_empty = False
                
                markdown_content = '\n'.join(lines).strip()
                
                # Resolve relative links to absolute
                markdown_content = resolve_relative_links(markdown_content, url)
                
                # Extract code blocks
                code_info = extract_code_blocks(markdown_content)
                
                # Calculate quality metrics
                quality_metrics = calculate_quality_metrics(markdown_content, original_html_length)
                
                # Generate deduplication hashes
                hashes = generate_content_hashes(markdown_content)
                
                # Create semantic chunks
                chunks = create_chunks(markdown_content, max_chunk_size=1000, overlap=100)
                
                # --- SAFEGUARD START ---
                # Don't charge users for empty/useless results (e.g., JS-only pages, blank pages, cookie walls)
                MIN_CONTENT_LENGTH = 200
                
                if len(markdown_content.strip()) < MIN_CONTENT_LENGTH:
                    Actor.log.warning(
                        f'Skipping {url}: Content too short ({len(markdown_content)} chars). '
                        f'Minimum required: {MIN_CONTENT_LENGTH} chars. User not charged.'
                    )
                    return  # Exit without pushing to dataset = no charge
                
                # Additional quality check: ensure we have meaningful content, not just errors
                error_indicators = [
                    'enable javascript',
                    'javascript is disabled',
                    'please enable cookies',
                    'access denied',
                    '403 forbidden',
                    '404 not found',
                    'page not found'
                ]
                content_lower = markdown_content.lower()
                if any(indicator in content_lower for indicator in error_indicators):
                    if len(markdown_content) < 500:  # Only skip if it's mostly error message
                        Actor.log.warning(
                            f'Skipping {url}: Appears to be an error page or requires JavaScript. User not charged.'
                        )
                        return
                # --- SAFEGUARD END ---
                
                # Add metadata at the top of full content
                final_content = f"**Source:** {url}\n\n---\n\n{markdown_content}"
                
                # Prepare data with chunks
                data = {
                    'url': url,
                    'title': title,
                    'markdown_content': final_content,
                    'chunks': chunks,
                    'metadata': metadata,
                    'code_blocks': code_info,
                    'quality_metrics': quality_metrics,
                    'hashes': hashes,
                    'total_chunks': len(chunks),
                    'total_chars': len(markdown_content),
                    'estimated_tokens': estimate_tokens(markdown_content)
                }
                
                method = "Readability" if use_readability else "Full Body"
                Actor.log.info(f'Successfully converted [{method}]: {title} ({len(final_content)} chars, {len(chunks)} chunks)')
                
                # Push to dataset
                await context.push_data(data)
                
            except Exception as e:
                Actor.log.error(f'Error processing {url}: {str(e)}')
        
        # Run the crawler
        await crawler.run(start_urls)
