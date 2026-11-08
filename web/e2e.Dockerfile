FROM mcr.microsoft.com/playwright:v1.65.0-noble
WORKDIR /app/web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY locales /app/locales
COPY web ./
CMD ["npx", "playwright", "test"]
