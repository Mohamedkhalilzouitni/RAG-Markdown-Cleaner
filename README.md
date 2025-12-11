# Web to Markdown Converter for RAG

Convert web pages into clean, token-efficient Markdown optimized for Large Language Models (LLMs) and Retrieval Augmented Generation (RAG) systems.

## 🚀 Features

- **Clean Content Extraction**: Uses Mozilla's Readability algorithm to extract only the main article content, removing navigation, footers, ads, and other clutter
- **Markdown Conversion**: Converts HTML to clean, readable Markdown format
- **Token Optimization**: Produces compact output ideal for LLM context windows
- **Configurable Links**: Choose whether to preserve or remove hyperlinks
- **Robust Error Handling**: Continues processing even if individual URLs fail
- **Production Ready**: Docker-based, deployable to Apify platform

## 📋 Use Cases

- Building RAG knowledge bases from web content
- Preparing training data for LLMs
- Creating clean documentation from web pages
- Batch processing articles for research
- Web content archival in Markdown format

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
Boolean flag to control whether hyperlinks are preserved in the Markdown output.

- `true`: Preserves links as `[text](url)`
- `false`: Converts links to plain text

**Example Input:**
```json
{
  "start_urls": [
    { "url": "https://blog.example.com/post1" },
    { "url": "https://news.example.com/article" }
  ],
  "include_links": false
}
```

## 📤 Output

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
- **title**: The extracted page title
- **markdown_content**: The main content converted to Markdown format

## 🛠️ Local Development

### Prerequisites
- Python 3.11+
- Docker (for containerized testing)
- Apify CLI (for deployment)

### Setup

1. **Clone the repository**
```bash
git clone <your-repo-url>
cd RAG-Ready
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Run locally**
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
