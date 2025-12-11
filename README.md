# Web to Markdown Converter for RAG

Convert web pages into clean, token-efficient Markdown optimized for Large Language Models (LLMs) and Retrieval Augmented Generation (RAG) systems with advanced features for production use.

## 🚀 Features

### Core Extraction
- **Clean Content Extraction**: Uses Mozilla's Readability algorithm to extract only the main article content, removing navigation, footers, ads, and other clutter
- **Markdown Conversion**: Converts HTML to clean, readable Markdown format
- **Smart Link Resolution**: Automatically converts relative URLs to absolute URLs for functional references

### RAG Optimization
- **Smart Semantic Chunking**: Automatically splits content into embedding-friendly chunks (configurable size, default 1000 chars)
  - Preserves heading hierarchy as context breadcrumbs
  - Configurable overlap between chunks for better continuity
  - Token estimates for each chunk
- **Metadata Extraction**: Captures author, publish date, keywords, description, language, and content type
- **Code Block Detection**: Identifies and extracts code blocks with language detection
  - Separate tracking of fenced code blocks and inline code
  - Line counts and language identification

### Quality & Deduplication
- **Content Quality Metrics**: 
  - Text density, word count, reading time
  - Paragraph and sentence analysis
  - Structure scoring (presence of lists, headings, links)
- **Deduplication Hashing**: SHA256 content hashing and similarity hashing for duplicate detection
- **Production Ready**: Docker-based, robust error handling, deployable to Apify platform

## 📋 Use Cases

- Building RAG knowledge bases from web content with optimal chunk sizes
- Preparing training data for LLMs with quality metrics
- Creating clean documentation from web pages with preserved structure
- Batch processing articles with deduplication
- Web content archival in Markdown format with full metadata

## 🎯 Input

The actor accepts the following input parameters:

### `start_urls` (required)
Array of URL objects to scrape and convert.

**Example:**
```json
[
  { "url": "https://example.com/article1" },
  { "url": "https://example.com/article2" }
]
```

### `include_links` (optional, default: `true`)
## 📤 Output

The actor pushes results to the default Apify Dataset. Each scraped URL produces a comprehensive object:

```json
{
  "url": "https://example.com/article",
  "title": "Article Title",
  "markdown_content": "# Article Title\n\nClean markdown content...",
  "chunks": [
    {
      "chunk_id": 1,
      "content": "First semantic chunk...",
      "heading_context": "Introduction > Background",
      "char_count": 850,
      "estimated_tokens": 212
    }
  ],
  "metadata": {
    "url": "https://example.com/article",
    "domain": "example.com",
    "scraped_at": "2025-12-11T01:23:45.123Z",
    "author": "John Doe",
    "publish_date": "2024-01-15",
    "last_modified": "2024-03-20",
    "language": "en",
    "keywords": ["web scraping", "python", "rag"],
    "description": "Article description from meta tags",
    "content_type": "blog"
  },
  "code_blocks": {
    "fenced_blocks": [
      {
        "language": "python",
        "code": "def example():\n    pass",
        "lines": 2
      }
    ],
    "inline_code_count": 15,
    "has_code": true
  },
  "quality_metrics": {
    "text_density": 0.75,
    "paragraph_count": 25,
    "word_count": 1500,
    "sentence_count": 85,
    "avg_sentence_length": 18.5,
    "reading_time_minutes": 8,
    "has_lists": true,
    "has_headings": true,
    "has_links": true,
    "structure_score": 1.0
  },
  "hashes": {
    "content_hash": "a1b2c3d4e5f6...",
    "similarity_hash": "1234567890abcdef"
  },
  "total_chunks": 3,
  "total_chars": 2500,
  "estimated_tokens": 625
}
```

### Output Fields

**Basic Info:**
- **url**: The original URL that was scraped
- **title**: The extracted page title
- **markdown_content**: The main content converted to Markdown format (with absolute URLs)

**Chunks (for RAG):**
- **chunks**: Array of semantic chunks optimized for embeddings
  - `chunk_id`: Sequential identifier
  - `content`: The chunk text
  - `heading_context`: Breadcrumb trail of headings (e.g., "Chapter 1 > Section 2")
  - `char_count`: Character count
  - `estimated_tokens`: Approximate token count (1 token ≈ 4 chars)

**Metadata:**
- **domain**: Extracted domain name
- **scraped_at**: ISO timestamp of scraping
- **author**: Page author (from meta tags or JSON-LD)
- **publish_date**: Publication date
- **last_modified**: Last modification date
- **language**: Two-letter language code
- **keywords**: Array of keywords from meta tags
- **description**: Page description
- **content_type**: Detected type (blog, documentation, wiki, product, general)

**Code Blocks:**
- **fenced_blocks**: Array of code blocks with language and line count
- **inline_code_count**: Number of inline code snippets
- **has_code**: Boolean indicating presence of code

**Quality Metrics:**
- **text_density**: Ratio of text to HTML (higher = cleaner content)
- **word_count**: Total words
- **reading_time_minutes**: Estimated reading time
- **structure_score**: 0-1 score based on presence of lists, headings, and links

**Deduplication:**
- **content_hash**: SHA256 hash for exact duplicate detection
- **similarity_hash**: Normalized hash for near-duplicate detection

The actor pushes results to the default Apify Dataset. Each scraped URL produces one object:

```json
{
  "url": "https://example.com/article",
  "title": "Article Title",
  "markdown_content": "# Article Title\n\nClean markdown content..."
}
```

### Output Fields

- **url**: The original URL that was scraped
## 💡 Tips

- **Chunking**: Default chunk size is 1000 characters with 100 character overlap - ideal for most embedding models
- **Rate Limiting**: For large batches, consider adding delays between requests
- **Custom Headers**: The actor includes a User-Agent header to avoid blocks
- **Timeout**: Default timeout is 30 seconds per URL
- **Error Handling**: Failed URLs are logged but don't stop the actor
## 📝 Example Use in RAG Pipeline

```python
# After running the actor, use the output in your RAG system
from apify_client import ApifyClient

client = ApifyClient(token='YOUR_TOKEN')
run = client.actor('YOUR_ACTOR_ID').call(run_input={
    'start_urls': [
        {'url': 'https://docs.example.com/page1'},
        {'url': 'https://docs.example.com/page2'}
    ],
    'include_links': False
})

# Get dataset items with all enhancements
for item in client.dataset(run['defaultDatasetId']).iterate_items():
    # Filter by quality
    if item['quality_metrics']['structure_score'] < 0.5:
        continue  # Skip low-quality content
    
    # Check for duplicates using similarity hash
    if item['hashes']['similarity_hash'] in seen_hashes:
        continue  # Skip duplicate
    seen_hashes.add(item['hashes']['similarity_hash'])
    
    # Process each chunk for embeddings
    for chunk in item['chunks']:
        # Use heading context for better retrieval
        context = f"{item['metadata']['domain']} - {chunk['heading_context']}"
        
        # Embed with your preferred model
        embedding = embed_model.encode(chunk['content'])
        
        # Store in vector database with metadata
        vector_db.upsert(
            id=f"{item['url']}#{chunk['chunk_id']}",
            vector=embedding,
            metadata={
                'url': item['url'],
                'title': item['title'],
                'context': context,
                'content_type': item['metadata']['content_type'],
                'has_code': item['code_blocks']['has_code'],
                'chunk_tokens': chunk['estimated_tokens']
            }
        )
```**Run locally**
```bash
apify run
```

### Testing Locally

Create a `.actor/INPUT.json` file:
```json
{
  "start_urls": [
    { "url": "https://example.com" }
  ],
  "include_links": true
}
```

Then run:
```bash
python src/main.py
```

## 🚢 Deployment

### Deploy to Apify

1. **Install Apify CLI**
```bash
npm install -g apify-cli
```

2. **Login to Apify**
```bash
apify login
```

3. **Push to Apify**
```bash
apify push
```

### Docker Build

To build the Docker image locally:
```bash
docker build -t web-to-markdown .
```

## 📦 Dependencies

- **apify**: Apify SDK for Python
- **requests**: HTTP library for fetching web pages
- **readability-lxml**: Extract main content from HTML
- **markdownify**: Convert HTML to Markdown
- **lxml**: XML/HTML processing library

## 🔧 Configuration

The actor is configured via:
- `.actor/input_schema.json`: Defines the input UI in Apify Console
- `Dockerfile`: Container configuration
- `requirements.txt`: Python dependencies

## 💡 Tips

- **Rate Limiting**: For large batches, consider adding delays between requests
- **Custom Headers**: The actor includes a User-Agent header to avoid blocks
- **Timeout**: Default timeout is 30 seconds per URL
- **Error Handling**: Failed URLs are logged but don't stop the actor

## 📝 Example Use in RAG Pipeline

```python
# After running the actor, use the output in your RAG system
from apify_client import ApifyClient

client = ApifyClient(token='YOUR_TOKEN')
run = client.actor('YOUR_ACTOR_ID').call(run_input={
    'start_urls': [
        {'url': 'https://docs.example.com/page1'},
        {'url': 'https://docs.example.com/page2'}
    ],
    'include_links': False
})

# Get dataset items
for item in client.dataset(run['defaultDatasetId']).iterate_items():
    # Feed markdown_content to your embedding model
    process_for_rag(item['markdown_content'])
```

## 🐛 Troubleshooting

**No output produced:**
- Check that URLs are accessible and return HTML content
- Verify input format matches the schema

**Markdown quality issues:**
- Some pages may have poor HTML structure
- Readability works best with article-style content

**Timeout errors:**
- Increase timeout in `requests.get()` if needed
- Check network connectivity

## 📄 License

This project is open source and available for use in RAG and LLM applications.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## 📧 Support

For issues or questions, please open a GitHub issue or contact via Apify platform.
