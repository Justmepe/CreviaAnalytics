# 🔗 Notion Database Sharing - Critical Step

Your integration can't access your database yet. You must explicitly share it. Here's how:

## Step-by-Step: Share Database with Integration

### 1. Open Your Notion Database
- Go to Notion: https://notion.so
- Find your database (ID: `1fd3e28a93304320a5f9a06cc9809340`)
- **Click to open it**

### 2. Click the Share Button
- Look for the **Share** button in the **top right corner**
- It looks like: 🔗 **Share** or **+ Invite**
- Click it

### 3. Find Your Integration
In the share dialog:
- Look for your integration (named **"Crevia Analytics"**)
- If you don't see it:
  - Click **"Invite"** or **"+"**
  - Search for **"Crevia Analytics"**
  - Select it from the list

### 4. Ensure Permissions are Correct
Check that your integration has:
- ✅ **Read content** - enabled
- ✅ **Update content** - enabled  
- ✅ **Insert content** - enabled (for creating pages)

### 5. Confirm Addition
- You should see your integration listed with access level
- Close the share dialog

## Verify Access Works

Run this test:
```bash
python test_notion_direct.py
```

You should see:
```
✓ Database retrieved successfully
✓ Query successful, found 0 items
```

## If It Still Says "Database Not Found"

If you're still getting "Could not find database" error:

1. **Verify the Database ID**
   - Open your database in Notion
   - Copy the URL: `https://notion.so/myworkspace/[DATABASE_ID]?v=...`
   - Make sure it matches: `1fd3e28a93304320a5f9a06cc9809340`
   - Update `.env` if needed

2. **Verify Integration was Added**
   - Go to your database
   - Click Share again
   - Confirm "Crevia Analytics" is listed
   - If not, add it again

3. **Wait a Moment**
   - Notion updates can take a few seconds
   - Wait 10 seconds and try again

4. **Check Integration Token**
   - Go to https://www.notion.so/my-integrations
   - Find your "Crevia Analytics" integration
   - Confirm it's **active** (not archived)
   - Copy the token again to `.env`

## Database Should Have These Columns

Make sure your database table has these properties:

| Property | Type | Required |
|----------|------|----------|
| **Title** | Title | Yes |
| **Content** | Rich Text | Yes |
| **Type** | Select | Yes |
| **Platform** | Select | Yes |
| **Status** | Select | Yes |
| **Created** | Date | Yes |
| **Tags** | Multi-select | Optional |
| **Image URL** | URL | Optional |

### How to Add Missing Properties

1. In your Notion database, click **+ Add a property**
2. Enter the property name (e.g., "Status")
3. Select the type (e.g., "Select")
4. For Select properties, add these options:
   - **Status**: Draft, In Review, Ready, Published, Scheduled, Archived
   - **Type**: Newsletter, News Post, Tweet Thread, Report, Market Insight
   - **Platform**: X, Substack, Web, Reddit, Discord

## Test Complete Setup

Once your database is properly shared:

```bash
python test_notion_integration.py
```

You should see:
```
✅ ALL TESTS PASSED!
✓ Database connection successful
✓ Test draft created successfully
✓ Content statistics retrieved
```

## Troubleshooting Checklist

- [ ] Database is shared with "Crevia Analytics" integration
- [ ] Integration has "Read" and "Update" permissions
- [ ] Database ID in `.env` is correct
- [ ] All required properties exist in database
- [ ] Integration token in `.env` is correct (starts with `ntn_`)
- [ ] Waited 10+ seconds after sharing for Notion to sync

## Still Having Issues?

Check the Notion integration logs in `.claude/` directory:
```bash
tail -f crypto_engine.log | grep -i notion
```

Or run the direct test with verbose output:
```bash
python test_notion_direct.py
```

---

**Once sharing is complete, try testing again and you'll be ready to go! 🚀**
