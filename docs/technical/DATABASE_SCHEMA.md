# Database Schema - Complete Reference

**Date:** October 8, 2025
**Database:** MongoDB (ca_codes_db)
**Compatibility:** 100% with old pipeline (legal-codes-pipeline)

---

## 📋 Overview

The CA Fire Pipeline uses **MongoDB** with three main collections, fully compatible with the old `legal-codes-pipeline` to ensure seamless integration with `legal-codes-api`.

---

## 🗄️ Collections

### 1. section_contents (Main Collection)

**Purpose:** Stores all section content, both single-version and multi-version

**Indexes:**
- `{code: 1, section: 1}` - Query by code and section
- `{is_multi_version: 1}` - Filter multi-version sections
- `{updated_at: -1}` - Sort by update time

#### Schema

```javascript
{
  // Core identifiers
  "code": "FAM",                    // Required: Code abbreviation
  "section": "3044",                // Required: Section number

  // Content (single-version sections)
  "content": "Section text...",     // Cleaned content
  "raw_content": "Section text...", // Raw content (before cleaning)
  "has_content": true,              // Boolean: has content
  "content_cleaned": false,         // Boolean: cleaning applied
  "content_length": 5927,           // Integer: content length
  "raw_content_length": 5927,       // Integer: raw content length

  // Legislative history
  "legislative_history": "Amended by Stats. 2024, Ch. 544, Sec. 6. (SB 899)...",
  "raw_legislative_history": "...", // Raw history
  "has_legislative_history": true,  // Boolean: has history

  // Multi-version fields
  "is_multi_version": true,         // Boolean: has multiple versions
  "version_number": 1,              // Integer: version number
  "is_current": true,               // Boolean: is current version
  "operative_date": null,           // String: operative date (optional)
  "description": "...",             // String: version description (optional)

  // Multi-version data (only for multi-version sections)
  "versions": [
    {
      "operative_date": null,       // String: date or null
      "content": "...",             // String: version content
      "legislative_history": "Amended by Stats. 2024, Ch. 544, Sec. 6. (SB 899) Effective January 1, 2025...",
      "status": "current",          // String: current/future/historical
      "url": "https://..."          // String: version URL
    },
    {
      "operative_date": null,
      "content": "...",
      "legislative_history": "Repealed (in Sec. 6) and added by Stats. 2024, Ch. 544, Sec. 7. (SB 899)...",
      "status": "current",
      "url": "https://..."
    }
  ],

  // Hierarchy
  "division": "Division 10",        // String: division name
  "part": "Part 5",                 // String: part name
  "chapter": "Chapter 2",           // String: chapter name
  "article": null,                  // String: article name (optional)

  // Metadata
  "url": "https://leginfo.legislature.ca.gov/...",
  "metadata": {},                   // Object: additional metadata (optional)
  "updated_at": ISODate("2025-10-08T..."),
  "created_at": ISODate("2025-10-08T...")  // Optional
}
```

#### Single-Version Example

```javascript
{
  "code": "FAM",
  "section": "1",
  "content": "This code shall be known as the Family Code.",
  "raw_content": "This code shall be known as the Family Code.",
  "has_content": true,
  "content_cleaned": false,
  "content_length": 44,
  "raw_content_length": 44,
  "legislative_history": "Enacted by Stats. 1992, Ch. 162, Sec. 10.",
  "raw_legislative_history": "Enacted by Stats. 1992, Ch. 162, Sec. 10.",
  "has_legislative_history": true,
  "is_multi_version": false,
  "version_number": 1,
  "is_current": true,
  "operative_date": null,
  "division": "Division 1",
  "part": null,
  "chapter": "Chapter 1",
  "article": null,
  "url": "https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?sectionNum=1&lawCode=FAM",
  "updated_at": ISODate("2025-10-08T19:52:06.496Z")
}
```

#### Multi-Version Example

```javascript
{
  "code": "FAM",
  "section": "3044",
  "content": null,                  // No content field for multi-version
  "raw_content": null,
  "has_content": false,
  "is_multi_version": true,
  "versions": [
    {
      "content": "(a) Upon a finding by the court...",  // 5,927 chars
      "legislative_history": "Amended by Stats. 2024, Ch. 544, Sec. 6. (SB 899) Effective January 1, 2025. Repealed as of January 1, 2026, by its own provisions. See later operative version added by Sec. 7 of Stats. 2024, Ch. 544.",
      "operative_date": null,
      "status": "current",
      "url": "https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?sectionNum=3044.&nodeTreePath=10.2.2&lawCode=FAM"
    },
    {
      "content": "(a) Upon a finding by the court...",  // 5,979 chars
      "legislative_history": "Repealed (in Sec. 6) and added by Stats. 2024, Ch. 544, Sec. 7. (SB 899) Effective January 1, 2025. Operative January 1, 2026, by its own provisions.",
      "operative_date": null,
      "status": "current",
      "url": "https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?sectionNum=3044.&nodeTreePath=10.2.2&lawCode=FAM"
    }
  ],
  "division": "Division 8",
  "part": "Part 2",
  "chapter": "Chapter 2",
  "url": "https://leginfo.legislature.ca.gov/faces/selectFromMultiples.xhtml?lawCode=FAM&sectionNum=3044",
  "updated_at": ISODate("2025-10-08T21:38:49.334Z")
}
```

---

### 2. code_architectures (Metadata Collection)

**Purpose:** Stores code-level metadata, tree structure, and url manifest

**Indexes:**
- `{code: 1}` - Query by code

#### Schema

```javascript
{
  // Basic info
  "code": "FAM",                    // Required: Code abbreviation
  "full_name": null,                // String: full code name (optional)
  "url": "https://leginfo.legislature.ca.gov/...",

  // Hierarchical tree structure
  "tree": {
    "type": "CODE",
    "code": "FAM",
    "name": "California FAM Code",
    "children": [
      {
        "type": "DIVISION",
        "number": "1",
        "title": "Preliminary Provisions and Definitions",
        "full_label": "Division 1",
        "level": 0,
        "section_range_display": "[1 - 100]",
        "children": [
          {
            "type": "PART",
            "number": "1",
            "title": "Preliminary Provisions",
            "full_label": "Part 1",
            "level": 1,
            "children": [...]
          }
        ]
      }
      // ... more divisions
    ]
  },

  // Complete section list (sorted)
  "url_manifest": [
    {
      "code": "FAM",
      "section": "1",
      "url": "https://...",
      "division": "Division 1",
      "part": null,
      "chapter": "Chapter 1",
      "article": null
    },
    // ... all 1,626 sections
  ],

  // Statistics
  "statistics": {
    "total_nodes": 312,             // Tree nodes count
    "max_depth": 4,                 // Tree depth
    "total_sections": 1626          // Section count
  },

  // Multi-version tracking
  "multi_version_sections": ["3044", "6389", "17400", "17404.1", "17430", "17432", "17504"],

  // Stage tracking
  "total_sections": 1626,
  "single_version_count": 1619,
  "multi_version_count": 7,
  "processed_sections": 1626,
  "stage1_completed": true,
  "stage2_completed": true,
  "stage3_completed": true,
  "stage1_started": ISODate("..."),
  "stage1_finished": ISODate("..."),
  "stage2_started": ISODate("..."),
  "stage2_finished": ISODate("..."),
  "stage3_started": ISODate("..."),
  "stage3_finished": ISODate("..."),

  // Session metadata
  "session_id": "570a8352",
  "crawled_at": "2025-10-08T21:22:07.873252",
  "success": true,
  "total_urls": 1626,
  "items_count": 312,

  // Timestamps
  "created_at": ISODate("..."),
  "last_updated": ISODate("...")
}
```

---

### 3. jobs (Job Tracking Collection)

**Purpose:** Track pipeline jobs and progress

**Indexes:**
- `{job_id: 1}` - Unique job ID
- `{status: 1}` - Filter by status
- `{created_at: -1}` - Sort by creation time

#### Schema

```javascript
{
  "job_id": "fam_20251008_213000",  // Required: unique identifier
  "code": "FAM",                    // Required: code being processed
  "status": "completed",            // Enum: pending/running/completed/failed
  "stage": "completed",             // String: current stage

  // Progress
  "total_sections": 1626,
  "processed_sections": 1626,
  "failed_sections": 0,
  "progress_percentage": 100.0,

  // Timing
  "started_at": ISODate("..."),
  "finished_at": ISODate("..."),
  "estimated_completion": null,

  // Error tracking
  "error_message": null,
  "failed_section_urls": [],

  // Metadata
  "metadata": {},
  "created_at": ISODate("..."),
  "last_updated": ISODate("...")
}
```

---

## 📊 Data Flow

### Stage 1: Architecture Discovery

```
Input: Code name ("FAM")
  ↓
Process:
  1. Scrape architecture page (build tree)
  2. Extract text page URLs
  3. Scrape each text page (get section URLs)
  4. Create url_manifest (sorted)
  5. Calculate statistics
  ↓
Output to MongoDB:
  ✅ section_contents: 1,626 documents (code, section, url, hierarchy)
  ✅ code_architectures: 1 document (tree, url_manifest, statistics)
```

### Stage 2: Content Extraction

```
Input: Section URLs from section_contents
  ↓
Process:
  1. Batch scrape sections (concurrent)
  2. Extract content & legislative history
  3. Detect multi-version (redirect check)
  4. Update sections
  ↓
Output to MongoDB:
  ✅ section_contents: Updated with content, history, is_multi_version flag
  ✅ code_architectures: Updated with counts, stage2_completed
```

### Stage 3: Multi-Version Extraction

```
Input: Multi-version sections from section_contents
  ↓
Process:
  1. Use Playwright to extract each version
  2. Parse complete legislative history
  3. Update sections with versions array
  ↓
Output to MongoDB:
  ✅ section_contents: Updated with versions array
  ✅ code_architectures: Updated with multi_version_sections array
```

---

## 🔄 Multi-Version Detection Strategy

### Why Stage 2 (Not Stage 1)?

**Old Pipeline (Stage 1):**
- Checks each section with curl (1,626 × curl calls)
- Follows redirects to detect selectFromMultiples
- Time: ~30-60 minutes for 1,626 sections
- Pro: Knows multi-version before extraction
- Con: Very slow, many extra requests

**New Pipeline (Stage 2):**
- Detects during content extraction (no extra requests)
- Firecrawl returns final URL after redirects
- Check if URL contains "selectFromMultiples"
- Time: 0 seconds extra (part of extraction)
- Pro: No extra requests, faster
- Con: Don't know until extraction

**Decision:** Detect in Stage 2 (faster, more efficient) ✅

### Syncing multi_version_sections Array

After Stage 3, sync the array from section_contents:

```python
# Query section_contents for multi-version sections
multi_sections = db.section_contents.find(
    {'code': 'FAM', 'is_multi_version': True},
    {'section': 1}
)
mv_list = [sec['section'] for sec in multi_sections]

# Update code_architectures
db.code_architectures.update_one(
    {'code': 'FAM'},
    {'$set': {'multi_version_sections': mv_list}}
)
```

This is done automatically in Stage 3. ✅

---

## 📝 Field Definitions

### section_contents Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `code` | String | Yes | Code abbreviation (FAM, CCP, etc.) |
| `section` | String | Yes | Section number (1, 3044, 73d, etc.) |
| `content` | String | No | Cleaned section content |
| `raw_content` | String | No | Raw content before cleaning |
| `has_content` | Boolean | Yes | Whether content was extracted |
| `content_cleaned` | Boolean | Yes | Whether content was cleaned |
| `content_length` | Integer | No | Length of content |
| `raw_content_length` | Integer | No | Length of raw content |
| `legislative_history` | String | No | Cleaned legislative history |
| `raw_legislative_history` | String | No | Raw legislative history |
| `has_legislative_history` | Boolean | Yes | Whether history exists |
| `is_multi_version` | Boolean | Yes | Has multiple operative versions |
| `version_number` | Integer | No | Version number (for single-version: 1) |
| `is_current` | Boolean | Yes | Is current version |
| `operative_date` | String | No | Operative date |
| `description` | String | No | Version description |
| `versions` | Array | No | Array of version objects (multi-version only) |
| `division` | String | No | Division name |
| `part` | String | No | Part name |
| `chapter` | String | No | Chapter name |
| `article` | String | No | Article name |
| `url` | String | Yes | Source URL |
| `metadata` | Object | No | Additional metadata |
| `updated_at` | Date | Yes | Last update timestamp |
| `created_at` | Date | No | Creation timestamp |

### Version Object (in versions array)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `operative_date` | String | No | Operative date (null if not parsed) |
| `content` | String | No | Version content |
| `legislative_history` | String | No | Complete history with bill #, dates |
| `status` | String | Yes | current/future/historical |
| `url` | String | No | Version-specific URL |

### code_architectures Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `code` | String | Yes | Code abbreviation |
| `tree` | Object | Yes | Hierarchical structure |
| `url_manifest` | Array | Yes | Complete sorted section list |
| `statistics` | Object | Yes | Tree statistics |
| `multi_version_sections` | Array | Yes | List of multi-version section numbers |
| `total_urls` | Integer | Yes | Total sections count |
| `items_count` | Integer | Yes | Tree nodes count |
| `session_id` | String | Yes | Unique session identifier |
| `crawled_at` | String | Yes | ISO timestamp |
| `success` | Boolean | Yes | Whether crawl succeeded |
| `total_sections` | Integer | Yes | Total sections |
| `single_version_count` | Integer | Yes | Single-version count |
| `multi_version_count` | Integer | Yes | Multi-version count |
| `processed_sections` | Integer | Yes | Processed count |
| `stage1_completed` | Boolean | Yes | Stage 1 status |
| `stage2_completed` | Boolean | Yes | Stage 2 status |
| `stage3_completed` | Boolean | Yes | Stage 3 status |
| `stage1_started` | Date | No | Stage 1 start time |
| `stage1_finished` | Date | No | Stage 1 finish time |
| `stage2_started` | Date | No | Stage 2 start time |
| `stage2_finished` | Date | No | Stage 2 finish time |
| `stage3_started` | Date | No | Stage 3 start time |
| `stage3_finished` | Date | No | Stage 3 finish time |

---

## 🔍 Common Queries

### Get All Sections for a Code

```javascript
db.section_contents.find({code: "FAM"})
```

### Get Multi-Version Sections

```javascript
db.section_contents.find({
  code: "FAM",
  is_multi_version: true
})
```

### Get Specific Section

```javascript
db.section_contents.findOne({
  code: "FAM",
  section: "3044"
})
```

### Get Tree Structure

```javascript
db.code_architectures.findOne(
  {code: "FAM"},
  {tree: 1, statistics: 1}
)
```

### Get Sections by Division

```javascript
db.section_contents.find({
  code: "FAM",
  division: "Division 10"
})
```

### Get Sections with Content

```javascript
db.section_contents.find({
  code: "FAM",
  has_content: true
})
```

---

## ✅ Compatibility with Old Pipeline

### section_contents Collection

**100% Compatible** ✅

All fields from old pipeline are present:
- Core fields: code, section, url
- Content fields: content, raw_content, has_content, content_length, etc.
- History fields: legislative_history, has_legislative_history
- Version fields: is_multi_version, version_number, versions
- Hierarchy fields: division, part, chapter, article

### code_architectures Collection

**100% Compatible** ✅

All fields from old pipeline are present:
- tree (hierarchical structure)
- url_manifest (complete section list)
- statistics (tree stats)
- multi_version_sections (array of section numbers)
- session_id, crawled_at, success

**Plus Additional Fields:**
- Stage completion tracking (stage1_completed, etc.)
- Processing counts (single_version_count, etc.)
- Timestamps (stage1_started, stage1_finished, etc.)

---

## 🎯 Best Practices

### 1. Query Efficiency

**Do:**
- Use indexes (code + section)
- Query section_contents for section data
- Query code_architectures for tree structure

**Don't:**
- Query without code filter
- Scan entire collection

### 2. Multi-Version Handling

**Detect:**
- Check `is_multi_version` field
- If true, read from `versions` array
- If false, read from `content` field

**Query:**
```javascript
// Get section
section = db.section_contents.findOne({code: "FAM", section: "3044"})

// Check if multi-version
if (section.is_multi_version) {
    // Read versions array
    for (let version of section.versions) {
        console.log(version.content)
    }
} else {
    // Read content field
    console.log(section.content)
}
```

### 3. Syncing Arrays

After Stage 3, sync multi_version_sections:
```javascript
// Get list from section_contents
let mvSections = db.section_contents.distinct("section", {
    code: "FAM",
    is_multi_version: true
})

// Update code_architectures
db.code_architectures.updateOne(
    {code: "FAM"},
    {$set: {multi_version_sections: mvSections}}
)
```

---

## 📊 Sample Counts (Actual Data)

### FAM (Family Code)

```
section_contents: 1,626 documents
  Single-version: 1,619
  Multi-version: 7

code_architectures: 1 document
  tree.children: 18 (divisions)
  tree.total_nodes: 312
  url_manifest: 1,626 sections
  multi_version_sections: ['3044', '6389', '17400', ...]
```

### CCP (Code of Civil Procedure)

```
section_contents: 3,353 documents
  Single-version: 3,347
  Multi-version: 6

code_architectures: 1 document
  tree.children: ~20 (divisions/titles)
  tree.total_nodes: ~600
  url_manifest: 3,353 sections
  multi_version_sections: ['35', '205', '231.7', ...]
```

### EVID (Evidence Code)

```
section_contents: 506 documents
  Single-version: 506
  Multi-version: 0

code_architectures: 1 document
  tree.children: ~15 (divisions)
  tree.total_nodes: ~120
  url_manifest: 506 sections
  multi_version_sections: []
```

---

## 🎉 Summary

**Schema Status:** ✅ **100% Complete and Compatible**

**Collections:**
- ✅ section_contents (5,485 documents across 3 codes)
- ✅ code_architectures (3 documents with tree structure)
- ✅ jobs (for tracking)

**Compatibility:**
- ✅ Matches old pipeline exactly
- ✅ legal-codes-api ready
- ✅ All required fields present

**Data Quality:**
- ✅ Complete content (100%)
- ✅ Complete legislative history
- ✅ Complete tree structures
- ✅ Complete url_manifests

---

**Document Version:** 1.0
**Last Updated:** October 8, 2025
**Status:** Complete reference for production use
