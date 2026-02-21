# Substack Supported Content Types

## The 3 Content Formats

Substack posting system supports these formats:

### 1. **TEXT** (Long-form Article)
- **Purpose**: Articles, newsletters, in-depth analysis
- **UI Location**: Create → "Text"
- **Best for**: 
  - Research reports
  - Market analysis
  - Trading strategies
  - Detailed guides
  - Newsletter articles
- **Characteristics**:
  - Title + body content required
  - Rich formatting support
  - Can be published or saved as draft
  - Professional appearance

### 2. **NOTE** (Quick Update)
- **Purpose**: Short updates, alerts, quick thoughts
- **UI Location**: Create → "New note"
- **Best for**:
  - Price alerts
  - Breaking news
  - Market observations
  - Quick opinions
  - Brief announcements
- **Characteristics**:
  - Short content (best <500 chars)
  - No title needed
  - Fast to create
  - Real-time updates

### 3. **THREAD** (Multi-part Thread)
- **Purpose**: X/Twitter thread format, multi-part narratives
- **UI Location**: Create → "New thread"
- **Best for**:
  - X/Twitter threads
  - Educational threads
  - Sequential narratives
  - Step-by-step guides
  - Story-telling content
- **Characteristics**:
  - Multiple connected parts (2+ minimum)
  - Sequential numbering (1/, 2/, 3/...)
  - Each part stands alone
  - High engagement format

---

## Content Selection Logic

The system automatically detects which format to use:

### Detection Rules
```
IF source == "twitter" OR "x_thread":
  → SELECT: THREAD

FOR RESEARCH OR ANALYSIS:
  → SELECT: TEXT

FOR QUICK UPDATES (news, alert, memo):
  → SELECT: NOTE

FOR CONTENT > 500 CHARACTERS:
  → SELECT: TEXT

DEFAULT:
  → SELECT: NOTE (safest)
```

---

## API/Automation Mapping

The code needs to:
1. **Detect content type** from source/metadata
2. **Choose appropriate post type** using logic above
3. **Navigate to correct Create option**:
   - Text: Click "Create new" → Selected option = "Text"
   - Note: Click "Create new" → Selected option = "New note"
   - Thread: Click "Create new" → Selected option = "New thread"
4. **Fill appropriate fields**:
   - Title (if applicable)
   - Content/Body
   - Formatting (if applicable)
5. **Publish or Draft** based on settings

---

## Content Type Detection Rules

### From X/Twitter Threads
- Source: X/Twitter API
- Characteristics: Multiple tweets, conversation
- **→ POST AS: THREAD**

### From Research Loop
- Source: Internal research system
- Characteristics: In-depth analysis, market signals
- **→ POST AS: TEXT**

### From News & Alerts
- Source: News APIs, price alerts
- Characteristics: Time-sensitive, brief
- **→ POST AS: NOTE**

---

## Implementation Checklist

- [x] Add `post_text()` method for long-form articles
- [x] Add `post_as_thread()` method for X/Twitter threads
- [x] Update `post_note()` method (already exists)
- [x] Add content type detection logic
- [ ] Integrate new methods into SubstackPoster class
- [ ] Update callers to use ContentTypeRouter
- [ ] Test all three post types with real examples
