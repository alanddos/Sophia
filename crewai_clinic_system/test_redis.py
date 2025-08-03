import redis

# Use a URL igual à do seu .env
redis_url = "redis://localhost:6379/0"

try:
    r = redis.Redis.from_url(redis_url)
    r.ping()
    print("Conexão com Redis bem-sucedida!")
except Exception as e:
    print(f"Erro ao conectar ao Redis: {e}")