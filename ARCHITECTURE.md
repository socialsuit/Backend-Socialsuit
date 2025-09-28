# Project Architecture Documentation

## Overview

This document describes the architecture of the Social Suit project, along with the shared library that contains common components. The architecture is designed to improve maintainability, reduce code duplication, and allow for modular development.

## Project Structure

The codebase is organized into two main components:

```
├── social-suit/       # Social media management platform
└── shared/            # Shared library used by the project
```

### Social Suit

Social Suit is a social media management platform with the following components:

```
├── social-suit/
│   ├── services/             # Service modules
│   │   ├── api/              # API endpoints
│   │   ├── models/           # Data models
│   │   ├── tasks/            # Background tasks
│   │   └── ...
│   ├── tests/                # Test suite
│   ├── main.py               # Application entry point
│   ├── celery_app.py         # Celery configuration
│   ├── requirements.txt      # Dependencies
│   ├── Dockerfile            # Container definition
│   └── docker-compose.yml    # Container orchestration
```

### Shared Library

The shared library contains components used by Social Suit:

```
├── shared/
│   ├── auth/                 # Authentication utilities
│   │   ├── jwt.py            # JWT handling
│   │   └── ...
│   ├── database/             # Database utilities
│   │   ├── connection.py     # Connection management
│   │   └── ...
│   ├── utils/                # Utility functions
│   │   ├── datetime.py       # Date/time utilities
│   │   └── ...
│   └── README.md             # Documentation
```

## Key Components

### Authentication

Social Suit uses JWT-based authentication, with utilities in the shared library:

- Token generation and validation
- Password hashing and verification
- User authentication flows

### Database

Social Suit uses SQLAlchemy with `declarative_base` for ORM.

Database utilities in the shared library include:

- Connection management
- Transaction handling
- Migration utilities

### API Structure

- Social Suit: FastAPI with routers in `services/endpoint`

### Background Tasks

- Social Suit: Celery with Redis as the message broker

## Dependencies

### Social Suit Dependencies

Key dependencies include:

- FastAPI
- SQLAlchemy
- Celery
- Redis
- Various Google API client libraries



- FastAPI
- SQLModel
- Celery
- Redis
- Alembic for migrations

### Shared Dependencies

Dependencies required by the shared library:

- SQLAlchemy (core)
- Pydantic
- Python-jose (JWT)
- Passlib (password hashing)

## Migration Process

The migration from the monorepo to the separated projects involved the following steps:

1. **Project Separation**
   - Created the two main directories: `social-suit` and `shared`
   - Moved Social Suit files to the `social-suit` directory

2. **Shared Component Extraction**
   - Identified reusable components in the project
   - Extracted these components to the `shared` library
   - Created a clear structure for the shared components

3. **Import Path Updates**
   - Updated import statements in the project to reference the shared library
   - Ensured that all imports resolve correctly

4. **Verification**
   - Verified that all files are in the correct locations
   - Checked that Python syntax is valid in all files
   - Verified that imports resolve correctly
   - Ran tests to ensure functionality is preserved

## Best Practices

### Shared Library Development

1. **Versioning**
   - Use semantic versioning for the shared library
   - Document breaking changes clearly

2. **Ownership**
   - Establish clear ownership for shared components
   - Define contribution guidelines

3. **Testing**
   - Write comprehensive tests for shared components
   - Ensure backward compatibility

### Project Development

1. **Modularity**
   - Keep project-specific code in the appropriate directories
   - Maintain clear separation between components

2. **Consistency**
   - Follow consistent coding standards throughout the project
   - Use similar patterns for similar functionality

3. **Documentation**
   - Document project-specific features
   - Keep documentation up to date

### Deployment

1. **Containerization**
   - Use Docker for consistent environments
   - Define Docker Compose configuration for the project

2. **CI/CD**
   - Set up CI/CD pipeline for the project
   - Include tests for the shared library in the pipeline

3. **Monitoring**
   - Implement monitoring for the project
   - Track usage of shared components

## Maintenance Strategy

### Regular Reviews

- Conduct regular code reviews
- Review shared components for potential improvements
- Identify opportunities for further separation or consolidation

### Dependency Management

- Keep dependencies up to date
- Ensure compatibility between the project and the shared library
- Document dependency changes

### Documentation

- Keep architecture documentation up to date
- Document changes to the shared library
- Maintain clear usage examples

## Conclusion

The organization of Social Suit with a shared library improves maintainability, reduces code duplication, and allows for focused development. By following the best practices outlined in this document, the project can continue to evolve while maintaining the benefits of modular code structure.