# Build stage
FROM node:20 AS build

WORKDIR /app

# Copy package files
COPY --link package.json package-lock.json* ./

# Install dependencies 
# Using ci for faster and more reliable builds
RUN --mount=type=cache,target=/root/.npm \
    npm ci

# Copy source code
COPY --link . .

# Build the application
RUN npm run build && ls -la /app/dist

# Production stage
FROM nginx:alpine

# Copy built assets from build stage
COPY --from=build /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
