# Granovital IA

## Architecture Overview
Granovital IA is designed with a microservices architecture, focusing on modularity and scalability. Each service is independent and communicates through REST APIs. This setup allows for easy integration of new features and services.

## Project Structure
```
granovital-ia/
│
├── api/                  # API service
│   └── ...
├── frontend/             # Frontend application
│   └── ...
├── backend/              # Backend services
│   └── ...
└── README.md            # Project documentation
```

## Technology Stack
- **Frontend:** React.js
- **Backend:** Node.js, Express
- **Database:** MongoDB
- **Deployment:** Docker, Kubernetes

## Setup Instructions
1. **Clone the Repository**
   ```bash
   git clone https://github.com/EstefaAZ/granovital-ia.git
   cd granovital-ia
   ```

2. **Install Dependencies**
   - For the frontend:
     ```bash
     cd frontend
     npm install
     ```
   - For the backend:
     ```bash
     cd backend
     npm install
     ```

3. **Run MongoDB**
   Ensure you have MongoDB running locally or use a cloud service. Update the database connection settings if needed.

4. **Environment Variables**
   Create a `.env` file in the backend directory based on the `.env.example` provided.

## How to Run the Project
- **Frontend:**
  Navigate to the `frontend` directory and run:
  ```bash
  npm start
  ```

- **Backend:**
  Navigate to the `backend` directory and run:
  ```bash
  npm start
  ```

- **Docker (optional):**
  You can also run the entire application using Docker by executing:
  ```bash
  docker-compose up
  ```

For further details on each component, refer to the individual service folders.
