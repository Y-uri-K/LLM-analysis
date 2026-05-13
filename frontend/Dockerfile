
FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./

RUN npm install

RUN npm install react-markdown

COPY . .

RUN npm run build

FROM node:20-alpine

WORKDIR /app

COPY --from=builder /app ./

EXPOSE 3000

CMD ["npm", "run", "dev"]