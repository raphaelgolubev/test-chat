# Chat test

Простой чат на вебсокетах

Постановка задачи [tz.md](tz.md)

## Запуск

- Перейдите в директорию проекта
```bash
cd test-chat
```

- Соберите образ
```bash
docker build -t chat-server .
```

- Запустите контейнер
```bash
docker run -p 8080:8080 chat-server
```

