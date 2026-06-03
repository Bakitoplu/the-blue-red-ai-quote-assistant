FROM node:22-alpine AS deps
WORKDIR /app
COPY web/package.json ./
RUN npm install
COPY web ./
ARG VITE_API_URL=http://127.0.0.1:8000
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=deps /app/dist /usr/share/nginx/html
