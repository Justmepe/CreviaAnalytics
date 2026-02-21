# 📓 Notion Integration Setup & Usage Guide

## Overview

This guide explains how to set up and use Notion as your content management system for the Crevia Analytics platform. Notion will store:

- ✍️ Draft content (before publishing)
- 📰 News analysis posts
- 📧 Newsletters
- 🧵 Tweet threads
- 📊 Market reports
- 🖼️ Images and media

## Why Notion?

- **Central Hub**: All your content in one place
- **Easy Collaboration**: Share with team members
- **Copy-Paste Ready**: Easily copy content to X, Substack, Web, etc.
- **Image Support**: Embed and organize images directly
- **Searchable**: Find content by type, platform, status, or tags
- **No more browser automation**: Write once, publish anywhere

## Step 1: Create a Notion Integration

### 1.1 Create Integration Token

1. Go to **[https://www.notion.so/my-integrations](https://www.notion.so/my-integrations)**
2. Click **"Create new integration"**
3. Name it: `"Crevia Analytics"`
4. Select your workspace
5. Click **"Create integration"**
6. Copy the **"Internal Integration Token"**
   - This is your `NOTION_API_KEY`

### 1.2 Create/Prepare Your Database

You have two options:

**Option A: Create from scratch (recommended)**
1. Go to Notion and create a new blank page
2. Click **"+ Add a database"** → **"Table"**
3. Name it **"Content Management"**
4. Copy the URL and extract the database ID:
   ```
   https://notion.so/myworkspace/abc123def456?v=xyz
                                 └─────────────┘ → This is your DATABASE_ID
   ```

**Option B: Use provided template**
- [Notion Template Link] (coming soon)

### 1.3 Grant Database Access

1. In Notion, open your Content Management database
2. Click **"Share"** button (top right)
3. Find your integration name ("Crevia Analytics")
4. Click to add it
5. Confirm access

## Step 2: Configure Environment Variables

### 2.1 Update .env file

Add these lines to your `.env` file:

```bash
# Notion Integration
NOTION_API_KEY=your_integration_token_here
NOTION_DATABASE_ID=your_database_id_here
```

Replace:
- `your_integration_token_here` with the token from Step 1.1
- `your_database_id_here` with the ID from Step 1.2

### 2.2 Verify Configuration

```bash
python -c "
from src.utils.notion_client import get_notion_client
client = get_notion_client()
if client.is_available():
    print('✓ Notion is properly configured!')
else:
    print('✗ Notion configuration failed. Check your API key and database ID.')
"
```

## Step 3: Install Dependencies

The Notion integration requires the official Notion Python client:

```bash
pip install notion-client
```

Or update your requirements.txt:

```bash
pip install -r requirements.txt
```

Make sure `notion-client` is in your `requirements.txt` file.

## Usage Examples

### Basic Setup in Your Code

```python
from src.utils.notion_content_manager import get_content_manager

# Get the content manager
manager = get_content_manager()

# Check if Notion is available
if not manager.is_available():
    print("Notion not configured")
    exit()
```

### Saving a News Post

```python
# Save a news analysis as a draft
page_id = manager.save_news_post(
    title="Bitcoin Surge Explained: Regulatory Optimism Drives Rally",
    content="""
    Bitcoin surged 12% this morning following positive regulatory comments 
    from the SEC. Here's what caused the movement:
    
    1. **Regulatory Catalyst**: SEC Chairman announced...
    2. **Technical Levels**: Bitcoin broke above $98,000...
    3. **Market Impact**: Altcoins followed with...
    """,
    tags=["Bitcoin", "Regulatory", "Market Analysis"],
    image_url="https://example.com/bitcoin-chart.png"
)

print(f"✓ Saved draft with ID: {page_id}")
```

### Saving a Newsletter

```python
# Save a weekly newsletter
page_id = manager.save_newsletter(
    title="Crypto Weekly Digest - Week 7, 2026",
    content="""
    📊 WEEKLY MARKET RECAP
    
    Market Overview:
    - Bitcoin: +8.5% WoW
    - Ethereum: +12% WoW
    ...
    """,
    tags=["Weekly", "Newsletter", "Market Recap"],
    image_url="https://example.com/weekly-chart.png"
)
```

### Saving a Tweet Thread

```python
# Save a tweet thread for X
page_id = manager.save_tweet_thread(
    title="Daily Market Update - Feb 19",
    content="""1/ Markets in flux today. Here's what's happening:

2/ Bitcoin broke above $100K on strong institutional buying...

3/ The catalyst? Markets are pricing in...

4/ On-chain data shows...

5/ TL;DR - ...
    """,
    tags=["Daily", "X Update"],
    image_url="https://example.com/chart.png"
)
```

### Updating Drafts

```python
# Update a draft
manager.update_draft(
    page_id=page_id,
    title="Bitcoin Surge Explained: Updated Analysis",
    status="review",  # Move to review status
    tags=["Bitcoin", "Regulatory", "Updated"]
)

# Mark as ready for publishing
manager.mark_as_ready(page_id)

# Mark as published with URL
manager.mark_as_published(
    page_id=page_id,
    published_url="https://web.crevia.io/article/bitcoin-surge"
)
```

### Listing Content

```python
# Get all drafts waiting to be published
ready_posts = manager.list_by_status("ready")
for post in ready_posts:
    print(f"📝 {post['title']}")
    print(f"   Platform: {post['platform']}")
    print(f"   Link: {post['url']}")

# Get all newsletters
newsletters = manager.list_by_type("newsletter", limit=20)

# Get content for X
x_posts = manager.list_by_platform("x", limit=50)

# Get news posts ready to publish
news_ready = manager.list_drafts(
    status="ready",
    content_type="news_post",
    limit=10
)
```

### Adding Images

```python
# Add an image to an existing draft
manager.add_image(
    page_id=page_id,
    image_url="https://example.com/chart.png"
)
```

### Getting Stats

```python
# Print content statistics
manager.print_stats()

# Or get as dictionary
stats = manager.get_stats()
print(f"Total drafts: {stats['total_drafts']}")
print(f"Ready to publish: {stats['ready_to_publish']}")
print(f"Published: {stats['published']}")
```

## Integration with Your Analysis Engine

### In main.py

```python
from src.utils.notion_content_manager import get_content_manager

# After generating content with Claude
content_manager = get_content_manager()

if content_manager.is_available():
    # Save the analysis to Notion
    page_id = content_manager.save_news_post(
        title=analysis_result['title'],
        content=analysis_result['detailed_analysis'],
        tags=analysis_result['tags'],
        image_url=analysis_result.get('chart_url')
    )
    
    logger.info(f"✓ Saved to Notion: {page_id}")
```

## Database Schema

Your Notion database should have these columns:

| Column Name | Type | Description |
|------------|------|-------------|
| Title | Title | Post title |
| Content | Rich Text | Full content/body |
| Type | Select | Newsletter, News Post, Tweet Thread, Report, Insight |
| Platform | Select | X, Substack, Web, Reddit, Discord |
| Status | Select | Draft, In Review, Ready, Published, Scheduled, Archived |
| Created | Date | Creation timestamp |
| Tags | Multi-select | Keywords/categories |
| Image URL | URL | Link to featured image |

**Optional columns you can add:**
- `Published URL` - URL where content was published
- `Word Count` - Formula: `length(prop("Content"))`
- `Characters` - Formula: `length(prop("Content"))`
- `Scheduled Date` - Date for scheduled publishing
- `Author` - Person
- `Last Edited` - Last modified timestamp

## Workflow Example

### Journey of a Post from Notion to Published

```
1. DRAFT CREATION
   → Research in Claude
   → Save to Notion as "Draft"

2. REVIEW
   → Read in Notion
   → Add/edit images
   → Mark as "In Review"

3. APPROVAL
   → Manager reviews
   → Provides feedback in Notion comments
   → Marks as "Ready to Publish"

4. PUBLISHING
   → Copy content from Notion
   → Post to X, Substack, Web, etc.
   → Update with "Published" status and URL

5. ARCHIVE
   → Later, move to "Archived" when no longer relevant
```

## Troubleshooting

### Issue: "Notion client not available"
**Solution:**
1. Check `NOTION_API_KEY` is set in `.env`
2. Check `NOTION_DATABASE_ID` is set in `.env`
3. Verify your database is shared with your integration
4. Run: `python -m pip install notion-client`

### Issue: "Database not found"
**Solution:**
1. Copy the correct database ID from Notion URL
2. Ensure integration has access:
   - Open database
   - Click "Share"
   - Add your integration

### Issue: "Permission denied"
**Solution:**
1. Go to **[https://www.notion.so/my-integrations](https://www.notion.so/my-integrations)**
2. Click your integration
3. Scroll to "Capabilities"
4. Ensure "Read" and "Update" are enabled
5. Save

### Issue: Images not appearing
**Solution:**
1. Use direct URLs (publicly accessible)
2. Not local file paths
3. Test URL in browser first
4. Notion requires HTTPS for external images

## Advanced Features

### Batch Operations

```python
# Save multiple posts
posts = [
    {
        "type": "news_post",
        "title": "Bitcoin Rally Explained",
        "content": "...",
        "tags": ["Bitcoin", "Analysis"]
    },
    {
        "type": "market_insight",
        "title": "Altcoin Trends",
        "content": "...",
        "tags": ["Altcoins", "Trends"]
    }
]

for post in posts:
    manager.save_draft(
        title=post["title"],
        content=post["content"],
        content_type=post["type"],
        platform="web",
        tags=post.get("tags", [])
    )
```

### Filtering & Search

```python
# Complex filtering
bitcoin_posts = manager.list_drafts(
    content_type="news_post",
    status="published",
    limit=100
)

# Process results
for post in bitcoin_posts:
    if "Bitcoin" in post.get("tags", []):
        print(f"Found: {post['title']}")
```

## Next Steps

1. ✅ Set up integration at https://notion.so/my-integrations
2. ✅ Create database in Notion
3. ✅ Add `NOTION_API_KEY` and `NOTION_DATABASE_ID` to `.env`
4. ✅ Install `notion-client`: `pip install notion-client`
5. ✅ Import and use in your code
6. ✅ Test with example scripts

## Best Practices

1. **Use consistent tags** - Helps with organization and filtering
2. **Save drafts early** - Don't wait until content is perfectly written
3. **Add images** - Makes content more engaging
4. **Use status workflow** - Draft → Review → Ready → Published
5. **Archive old content** - Keep database clean
6. **Comment for feedback** - Use Notion comments for collaboration
7. **Regular backups** - Notion is reliable, but always export important content

## Support

For issues:
1. Check logs: `tail -f crypto_engine.log`
2. Test API connection: `python test_notion_connection.py`
3. Verify database schema matches expected columns
4. Check Notion integration permissions

---

**Happy content creation! 🚀**

Now all your analysis goes straight to Notion, ready to share anywhere.
