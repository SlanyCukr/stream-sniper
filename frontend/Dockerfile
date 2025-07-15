# Development Dockerfile for React frontend with hot reload
FROM node:18-alpine

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies (including dev dependencies for hot reload)
RUN npm ci

# Copy source code
COPY . .

# Expose port for development server
EXPOSE 3000

# Set environment variable for hot reload
ENV CHOKIDAR_USEPOLLING=true
ENV GENERATE_SOURCEMAP=false

# Start development server with hot reload
CMD ["npm", "start"]