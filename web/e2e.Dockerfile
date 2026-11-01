FROM mcr.microsoft.com/playwright:v1.64.1-noble
WORKDIR /app/web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY locales /app/locales
COPY web ./
CMD ["npx", "playwright", "test"]
