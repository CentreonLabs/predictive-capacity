FROM node:lts-alpine

ARG API_URL
ENV VITE_API_URL $API_URL

WORKDIR /app

RUN npm install -g pnpm@latest-9

COPY ./src /app/src
COPY tsconfig.json /app
COPY tsconfig.node.json /app
COPY vite.config.ts /app
COPY ./index.html /app
COPY ./package.json /app
COPY ./pnpm-lock.yaml /app

RUN chown -R node:node /app

USER node

RUN cd /app
RUN pnpm install && pnpm run build

CMD [ "pnpm", "run", "serve" ]