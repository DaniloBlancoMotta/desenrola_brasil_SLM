FROM node:22-alpine

WORKDIR /app

# Camada de dependencias separada do codigo-fonte.
COPY package.json ./
RUN npm install

COPY . .

EXPOSE 4200

CMD ["npm", "start", "--", "--host", "0.0.0.0"]
