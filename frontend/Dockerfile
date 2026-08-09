# Use official Node.js image
FROM node:20-alpine

WORKDIR /app

# Copy package files and install dependencies
COPY package*.json ./
RUN npm install

# Copy source code
COPY . .

EXPOSE 5173

# Run the dev server exposed to all network interfaces
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
