FROM node:20-alpine

WORKDIR /app

# Copiar package.json
COPY package.json package-lock.json* ./

# Instalar dependencias
RUN npm install

# Copiar código
COPY . .

# Exponer puerto
EXPOSE 3000

# Comando de desarrollo
CMD ["npm", "run", "dev"]
