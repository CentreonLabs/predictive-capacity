FROM node:lts-alpine

ARG API_URL
ENV VITE_API_URL $API_URL

WORKDIR /app

RUN npm install -g npm@latest

COPY ./src /app/src
COPY tsconfig.json /app
COPY tsconfig.node.json /app
COPY vite.config.ts /app
COPY ./index.html /app
COPY ./package.json /app
COPY ./package-lock.json /app

RUN chown -R node:node /app

USER node

RUN cd /app
RUN npm install && npm run build

CMD [ "npm", "run", "serve" ]