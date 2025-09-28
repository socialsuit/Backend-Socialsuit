# OpenAPI Documentation

## Overview

This document describes the OpenAPI integration for the Social Suit application. The application now exposes standardized API documentation with proper versioning, tags, and security schemes.

## Features

- **API Versioning**: All endpoints are versioned under `/api/v1`
- **Interactive Documentation**: Available at `/api/v1/docs` (Swagger UI) and `/api/v1/redoc` (ReDoc)
- **Security Schemes**: JWT Bearer authentication and OAuth2 where applicable
- **Static OpenAPI JSON**: Generated and committed for external tools integration

## Accessing Documentation

### Social Suit

- Swagger UI: `/api/v1/docs`
- ReDoc: `/api/v1/redoc`
- OpenAPI JSON: `/api/v1/openapi.json`

## Static OpenAPI Files

Static OpenAPI JSON files have been generated and committed to the repository:

- Social Suit: `docs/openapi/openapi.json`

These files can be used with external tools like Postman, Insomnia, or API documentation generators.

## Generating Updated OpenAPI Files

To regenerate the OpenAPI files after API changes, use the provided scripts:

```bash
python scripts/generate_openapi.py
```

## Security Schemes

### Social Suit

- **JWT Bearer Authentication**: Used for most protected endpoints
- **OAuth2**: Available for authorization code flow

## API Tags

Endpoints are organized by tags for better navigation:

### Social Suit

- AI Content
- Health
- Authentication
- Analytics
- Content Management
