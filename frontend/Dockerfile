FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci --ignore-scripts

COPY next.config.mjs ./
COPY tsconfig.json ./
COPY next-env.d.ts ./
COPY proxy.ts ./
COPY app/ ./app/
COPY components/ ./components/
COPY lib/api.ts lib/types.ts ./lib/
COPY utils/ ./utils/

RUN chown -R node:node /app
USER node

EXPOSE 3000
CMD ["npm", "run", "dev"]
