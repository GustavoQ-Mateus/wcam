FROM node:26-slim
WORKDIR /app/web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY locales /app/locales
COPY web ./
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
