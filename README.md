# MediaOS — AI Event Hub

A multi-source AI event intelligence platform that collects content from YouTube, Instagram, and parliamentary sources, processes and deduplicates incoming media, clusters related stories using semantic similarity, and turns them into ranked events through an automated intelligence pipeline.

## Overview

MediaOS is designed to answer a simple question:

> **What events are happening across multiple media sources right now?**

Instead of treating every post or video as an independent piece of information, the system collects media from different sources, normalizes and deduplicates them, groups related content into clusters, and builds unified events from those clusters.

```text
Media Sources
     │
     ├── YouTube
     ├── Instagram
     └── Parliamentary Data
             │
             ▼
      Acquisition Layer
             │
             ▼
       Normalization
             │
             ▼
        Deduplication
             │
             ▼
      Semantic Clustering
             │
             ▼
       Event Building
             │
             ▼
       Event Scoring
             │
             ▼
       Live Dashboard
```

## Key Features

* Multi-source media acquisition
* YouTube content collection
* Instagram source discovery
* Parliamentary data acquisition
* Provider-based acquisition architecture
* Content normalization
* Duplicate detection
* Semantic similarity clustering
* TF-IDF fallback when transformer embeddings are unavailable
* Automatic event generation
* Event scoring based on corroboration and recency
* Priority-topic detection
* Forced topic-linking for configured subjects
* Automated refresh scheduling
* REST API endpoints
* Live web dashboard
* Event detail pages
* Media grouped by source type

## Supported Sources

### YouTube

The system collects content from configured YouTube sources and can discover additional YouTube channels through Instagram profile links.

### Instagram

Instagram acts as both a media source and a discovery layer.

The system can use configured Instagram seed accounts and discover additional accounts based on their follow relationships and public profile information.

Instagram followee discovery is cached and refreshed according to the configured discovery window.

### Parliamentary Data

The project includes a parliamentary provider targeting Lok Sabha legislation data from `sansad.in`.

Because the source is a JavaScript-based application without a conventional public API/RSS feed, the project uses browser-based acquisition through Playwright.

## Architecture

### Acquisition Layer

```text
acquisition/
├── providers/
│   ├── base.py
│   ├── rss.py
│   ├── youtube.py
│   ├── press.py
│   └── instagram.py
├── provider_manager.py
└── scheduler.py
```

The provider architecture separates individual data sources from the rest of the system.

New providers can be added without changing the downstream processing and intelligence pipeline.

### Processing Layer

```text
processing/
├── normalizer.py
└── deduplicator.py
```

The processing layer prepares acquired media for intelligence processing.

The normalizer creates consistent representations across different source formats, while the deduplicator removes repeated content.

### Intelligence Layer

```text
intelligence/
├── classifier.py
└── event_builder.py
```

The classifier determines which media items belong together.

The system primarily uses sentence-transformer embeddings and cosine similarity for semantic comparison.

If sentence-transformers cannot be loaded, the system falls back to TF-IDF embeddings using scikit-learn.

The Event Builder then converts media clusters into unified events.

## Event Scoring

Events are ranked using several signals:

* Number of corroborating media items
* Recency
* Priority-topic matches

More media covering the same event increases its score, while recent events receive an additional recency bonus.

Configured priority topics can receive an additional score boost.

## Event Model

An event can contain multiple pieces of media from different source types.

For example:

```text
Event
│
├── YouTube video
├── Instagram post
└── Parliamentary source
```

This allows the dashboard to present related information as one event rather than several disconnected items.

## Dashboard

The project includes a FastAPI-based web dashboard.

```text
dashboard/
├── app.py
├── pipeline.py
├── store.py
├── static/
│   ├── app.js
│   └── style.css
└── templates/
    ├── index.html
    ├── event.html
    └── not_found.html
```

The dashboard provides:

* Live event feed
* Event detail pages
* Event scoring
* Priority indicators
* Media counts
* Source breakdowns
* Relative timestamps
* Manual refresh
* Health endpoint
* Automatic background refresh

## API Endpoints

### Health

```text
GET /api/health
```

Returns system status, last update time, event count, and configured fetch interval.

### Events

```text
GET /api/events
```

Returns the current event feed as JSON.

### Manual Refresh

```text
POST /api/refresh
```

Triggers a pipeline refresh without waiting for the scheduled cycle.

### Event Details

```text
GET /event/{event_id}
```

Returns the dashboard detail page for an individual event.

## Automated Pipeline

The dashboard starts the acquisition and intelligence pipeline when the application starts.

After the initial run, the scheduler periodically executes the pipeline according to the configured refresh interval.

```text
Application Startup
        │
        ▼
 Initial Pipeline Run
        │
        ▼
 Provider Acquisition
        │
        ▼
 Processing
        │
        ▼
 Intelligence
        │
        ▼
 Event Store
        │
        ▼
 Dashboard
        │
        └──────► Scheduled Refresh
```

## Project Structure

```text
mediaos/
│
├── acquisition/
│   ├── providers/
│   │   ├── base.py
│   │   ├── rss.py
│   │   ├── youtube.py
│   │   ├── press.py
│   │   └── instagram.py
│   ├── provider_manager.py
│   └── scheduler.py
│
├── intelligence/
│   ├── classifier.py
│   └── event_builder.py
│
├── processing/
│   ├── normalizer.py
│   └── deduplicator.py
│
├── models/
│   ├── event.py
│   └── media.py
│
├── dashboard/
│   ├── app.py
│   ├── pipeline.py
│   ├── store.py
│   ├── static/
│   └── templates/
│
├── config.py
├── main.py
├── requirements.txt
├── Procfile
├── .env.example
└── .gitignore
```

## Installation

Clone the repository:

```bash
git clone <repository-url>
cd mediaos
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows:

```powershell
.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Environment Configuration

Create a local `.env` file based on `.env.example`.

Example configuration:

```env
INSTAGRAM_LOGIN_USERNAME=
INSTAGRAM_LOGIN_PASSWORD=

INSTAGRAM_SESSION_FILE=.instaloader_session

INSTAGRAM_DISCOVER_FOLLOWEES=true
INSTAGRAM_MAX_FOLLOWEES_PER_SEED=15
INSTAGRAM_DISCOVERY_REFRESH_HOURS=24
```

Real credentials should never be committed to the repository.

The repository includes `.env.example` as a configuration template.

## Running

Run the pipeline:

```bash
python main.py
```

The project also includes a FastAPI dashboard that can be served using an ASGI server such as Uvicorn.

Example:

```bash
uvicorn dashboard.app:app --reload
```

## Technologies

* Python
* FastAPI
* Uvicorn
* NumPy
* Pandas
* Scikit-learn
* Sentence Transformers
* Cosine Similarity
* TF-IDF
* Playwright
* Instagram/Instaloader
* YouTube data acquisition
* Jinja2
* HTML/CSS/JavaScript

## Engineering Concepts

MediaOS demonstrates several software-engineering and data-intelligence concepts:

* Modular provider architecture
* ETL-style processing
* Data normalization
* Deduplication
* Semantic similarity
* Embedding-based classification
* Fallback processing strategies
* Event aggregation
* Ranking systems
* Scheduled background processing
* REST API design
* Server-side rendering
* Caching
* Configuration-driven behavior

## Security & Operational Considerations

Instagram authenticated discovery requires credentials supplied through environment variables.

The project does not hardcode login credentials.

Instagram follower discovery can carry account restrictions or ban risks, so the system includes configurable limits and caching to reduce unnecessary discovery operations.

## Current Status

MediaOS is an evolving AI event-intelligence project.

The current implementation focuses on:

* Multi-source acquisition
* Media processing
* Semantic clustering
* Event generation
* Event ranking
* Automated refresh cycles
* FastAPI dashboard delivery

## Roadmap

* [ ] Expand source integrations
* [ ] Improve event clustering
* [ ] Add richer event summarisation
* [ ] Improve event ranking
* [ ] Add persistent event history
* [ ] Expand testing
* [ ] Add observability and monitoring
* [ ] Improve dashboard analytics
* [ ] Add configurable intelligence pipelines

## Disclaimer

This project is intended for educational, research, and software-engineering purposes.

Data availability and functionality depend on the external platforms and providers used by the system. External platforms may impose API restrictions, authentication requirements, rate limits, or other operational limitations.

## Author

**Dhairya Bansal**

BBA FinTech | ACCA

Interests:

* Financial Technology
* Quantitative Finance
* Software Engineering
* AI Systems
* Data Engineering
* Financial Markets
