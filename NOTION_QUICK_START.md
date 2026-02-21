# 🚀 Notion Integration - Quick Start

## What You're Getting

A complete **Notion integration** for your Crevia Analytics platform that allows you to:

1. ✍️ **Write content once** in Notion
2. 📋 **Organize drafts** by type, platform, and status  
3. 🖼️ **Embed images** directly in Notion
4. 📱 **Copy-paste anywhere** (X, Substack, Web, Reddit, Discord)
5. 🚫 **Skip browser automation** - no more X detection issues!

## New Files Created

### Source Code
- **`src/utils/notion_client.py`** - Low-level Notion API client
- **`src/utils/notion_content_manager.py`** - High-level content management interface

### Configuration
- **`.env.notion.template`** - Template for environment variables
- **`requirements_notion.txt`** - Required package (`notion-client`)

### Documentation & Testing
- **`doc/NOTION_SETUP_GUIDE.md`** - Complete setup and usage guide
- **`test_notion_integration.py`** - Test script to verify setup

## Installation (3 Simple Steps)

### Step 1: Install Package
```bash
pip install notion-client
```

### Step 2: Get Notion Credentials
1. Go to https://www.notion.so/my-integrations
2. Create new integration (name it "Crevia Analytics")
3. Copy the API key
4. Create a database in Notion
5. Share it with your integration
6. Get the database ID from the URL

### Step 3: Configure .env
Add to your `.env` file:
```bash
NOTION_API_KEY=your_api_key_here
NOTION_DATABASE_ID=your_database_id_here
```

### Step 4: Test
```bash
python test_notion_integration.py
```

## Usage Examples

### Quick Save Methods

```python
from src.utils.notion_content_manager import get_content_manager

manager = get_content_manager()

# Save a news post
page_id = manager.save_news_post(
    title="Bitcoin Hits $100K",
    content="Detailed analysis here...",
    tags=["Bitcoin", "Analysis"],
    image_url="https://example.com/chart.png"
)

# Save a newsletter
manager.save_newsletter(
    title="Weekly Crypto Digest",
    content="Weekly roundup...",
    tags=["Weekly"]
)

# Save a tweet thread
manager.save_tweet_thread(
    title="Daily Update",
    content="1/ Markets up today...",
    tags=["Daily"]
)
```

### List & Manage Content

```python
# Get all drafts ready to publish
ready = manager.list_by_status("ready")

# Get all X posts
x_posts = manager.list_by_platform("x")

# Update a draft
manager.update_draft(page_id, status="review")

# Mark as published
manager.mark_as_published(page_id, "https://example.com/published")
```

### View Statistics

```python
# Print content stats
manager.print_stats()

# Or get as dict
stats = manager.get_stats()
print(f"Drafts: {stats['total_drafts']}")
```

## Integration with Your Engine

In your `main.py` or analysis loop:

```python
from src.utils.notion_content_manager import get_content_manager

# After Claude generates content
manager = get_content_manager()

if manager.is_available():
    page_id = manager.save_news_post(
        title=analysis["title"],
        content=analysis["content"],
        tags=analysis["tags"],
        image_url=analysis.get("chart_url")
    )
    logger.info(f"Saved to Notion: {page_id}")
```

## Database Setup in Notion

Create a table with these columns:

| Column | Type | Purpose |
|--------|------|---------|
| Title | Title | Post title |
| Content | Rich Text | Full content |
| Type | Select | Newsletter, News Post, Tweet Thread, Report |
| Platform | Select | X, Substack, Web, Reddit, Discord |
| Status | Select | Draft, In Review, Ready, Published, Archived |
| Created | Date | When created |
| Tags | Multi-select | Keywords/categories |
| Image URL | URL | Featured image link |

## Content Type Reference

### Available Content Types
- `"newsletter"` → Newsletter  
- `"news_post"` → News Post
- `"tweet_thread"` → Tweet Thread
- `"report"` → Detailed Report
- `"insight"` → Market Insight

### Available Statuses
- `"draft"` → Work in progress
- `"review"` → Waiting for approval
- `"ready"` → Ready to publish
- `"published"` → Already published
- `"scheduled"` → Scheduled for later
- `"archived"` → No longer relevant

### Available Platforms
- `"x"` → X (Twitter)
- `"substack"` → Substack
- `"web"` → Your website
- `"reddit"` → Reddit
- `"discord"` → Discord

## Workflow Example

```
1. Research & Write (Claude)
   ↓
2. Save to Notion as Draft (your code)
   ↓
3. Review in Notion (you read it)
   ↓
4. Mark as "Ready" in Notion
   ↓
5. Copy from Notion → Paste to X/Substack/Web
   ↓
6. Mark as "Published" with URL
   ↓
7. Later: Archive old content
```

## Complete Setup Checklist

- [ ] Install `notion-client`: `pip install notion-client`
- [ ] Create integration at https://www.notion.so/my-integrations
- [ ] Copy API token to `NOTION_API_KEY=...` in `.env`
- [ ] Create Notion database
- [ ] Share database with integration
- [ ] Copy database ID to `NOTION_DATABASE_ID=...` in `.env`
- [ ] Run test: `python test_notion_integration.py`
- [ ] Review setup guide: `doc/NOTION_SETUP_GUIDE.md`
- [ ] Start using in your code!

## Troubleshooting

### "Notion not available"
```bash
# 1. Check .env has keys
grep NOTION .env

# 2. Install package
pip install notion-client

# 3. Test connection
python test_notion_integration.py
```

### "Database not found"
- Verify database ID in `.env`
- Ensure integration is shared with database
- Go to Notion → Database → Share → Add integration

### "Permission denied"
- Go to https://www.notion.so/my-integrations
- Click your integration
- Enable "Read content" and "Update content" capabilities
- Re-share database

## Next Steps

1. **Read Full Guide**: `doc/NOTION_SETUP_GUIDE.md`
2. **Test Setup**: `python test_notion_integration.py`
3. **Integrate with Main Engine**: Add to your analysis loop
4. **Start Publishing**: Write → Notion → Anywhere

## Benefits Over Browser Automation

| Aspect | Browser Automation | Notion Integration |
|--------|-------------------|--------------------|
| **Detection Risk** | High (X improved detection) | ✅ None (API-based) |
| **Reliability** | Fragile (breaks with UI changes) | ✅ Stable (official API) |
| **Image Support** | Limited | ✅ Full support |
| **Copy-Paste** | Not needed | ✅ Easy clipboard |
| **Collaboration** | Not possible | ✅ Full team support |
| **Search/Filter** | Not available | ✅ Quick search |
| **Maintenance** | High | ✅ No maintenance |
| **Multi-platform** | Complex setup | ✅ One source |

---

**Ready to move your content to Notion? Let's go! 🚀**

Questions? See `doc/NOTION_SETUP_GUIDE.md` for detailed information.
