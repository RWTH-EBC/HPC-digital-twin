FROM node:20-slim 

WORKDIR /app

COPY package*.json ./

RUN npm install

COPY . .

# Expose port 3000
EXPOSE 3000

# Start the development server on port 4200
CMD ["npm", "run", "dev", "--", "--port", "3000", "--hostname", "0.0.0.0"]
