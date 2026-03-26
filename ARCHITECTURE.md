# Architecture Documentation

## Introduction
This document provides comprehensive details about the architecture of the granovital-ia system, following the C4 model and encompassing various aspects of the software design, including microservices, API Gateway, and database schema.

## C4 Model
### Context Level
- **System**: Granovital IA
- **External Entities**: Users, third-party services, etc.

### Container Level
- **Backend Modules**: 7 microservices (login, cultivos, monitoreo, ia, trazabilidad, mercado, reportes).
- **API Gateway**: Acts as a single entry point for all client applications.
- **Database**: Central storage for all the data.

### Component Level
- Each microservice contains its components, implemented according to specific business logic.
- Examples: Authentication service, Crop management module, Monitoring service, etc.

### Code Level
- Organized into multiple repositories/modules.
- Each microservice follows best practices for maintainability and scalability.

## System Design Patterns
- Microservices architecture for scalability.
- API Gateway pattern for request routing.
- Repository pattern for data access.

## Microservices Architecture
- **Login**: Handles user authentication and authorization.
- **Cultivos**: Manages crop-related data and actions.
- **Monitoreo**: Responsible for monitoring crop health and environments.
- **IA**: Implements artificial intelligence for insights and predictions.
- **Trazabilidad**: Tracks the supply chain data for transparency.
- **Mercado**: Manages market-related functionalities and transactions.
- **Reportes**: Generates reports based on data from other services.

## API Gateway Design
- Centralizes incoming requests and routes them to appropriate backend services.
- Provides features such as request validation, logging, and rate limiting.

## Database Schema Overview
- **Core Tables**: Users, Crops, MonitoringData, Transactions, etc.
- Relationships between tables for data integrity and efficiency.

## Data Flow Between Services
- Description of asynchronous communication via message queues.
- Diagram showing service interactions and data processing flows.

## Integration Points
- Integration with frontend applications using RESTful APIs.
- External integrations with third-party services for data exchange.

---

This document serves as a detailed guide for understanding the architecture of the granovital-ia application, providing insights into the structure and interactions of its components.

