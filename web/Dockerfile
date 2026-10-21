# ProofGate web: static export served by nginx. Build from the repo root:
#   docker build -f web/Dockerfile --build-arg NEXT_PUBLIC_API_URL=http://localhost:8000 .
FROM node:22-alpine AS build
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY web/ ./
ARG NEXT_PUBLIC_API_URL=""
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /web/out /usr/share/nginx/html
EXPOSE 80
