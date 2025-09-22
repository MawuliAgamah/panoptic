# Improved Module Structure

## Current Issues with Circular Dependencies

Looking at the current codebase, circular dependencies arise from:

1. **Services importing repositories that import models that import services**
2. **Factory functions importing dependencies at function level instead of module level**
3. **Mixed concerns within single modules**

## Proposed Module Structure

```
src/flashcards/
├── domain/                    # Core domain logic (no external dependencies)
│   ├── __init__.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── card.py           # Card entity
│   │   ├── deck.py           # Deck entity
│   │   ├── review.py         # Review entity
│   │   └── value_objects.py  # SpacedRepetitionData, etc.
│   ├── interfaces/           # Abstract interfaces
│   │   ├── __init__.py
│   │   ├── repositories.py   # Repository interfaces
│   │   └── services.py       # Service interfaces
│   └── exceptions.py         # Domain exceptions
│
├── algorithms/               # Spaced repetition algorithms
│   ├── __init__.py
│   ├── base.py
│   ├── sm2.py
│   └── sm15.py
│
├── infrastructure/           # External concerns (storage, APIs, etc.)
│   ├── __init__.py
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── adapters.py       # Storage adapter implementations
│   │   └── repositories.py   # Concrete repository implementations
│   ├── external/
│   │   ├── __init__.py
│   │   └── anki_service.py
│   └── config/
│       ├── __init__.py
│       └── settings.py
│
├── application/              # Application services (orchestration)
│   ├── __init__.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── card_service.py
│   │   ├── deck_service.py
│   │   └── review_service.py
│   └── orchestrator.py       # Main orchestrator
│
├── presentation/             # API/UI layer
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── client.py         # Main API client
│   │   └── dto.py           # Data transfer objects
│   └── web/                  # Web API (if needed)
│       ├── __init__.py
│       └── handlers.py
│
└── __init__.py               # Main module exports
```

## Dependency Flow Rules

1. **Domain** → No dependencies on other modules
2. **Algorithms** → Can depend on Domain
3. **Infrastructure** → Can depend on Domain + Algorithms
4. **Application** → Can depend on Domain + Algorithms + Infrastructure interfaces
5. **Presentation** → Can depend on Application + Domain (for DTOs)

## Implementation Examples