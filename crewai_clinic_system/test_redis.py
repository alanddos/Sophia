import  redis

print("Iniciando teste de conexão...")  # <-- Adicione este print

redis_url = "redis://localhost:6379/0"

try:
    print("Tentando conectar ao Redis...")  # <-- Adicione este print
    r = redis.Redis.from_url(redis_url, socket_connect_timeout=2, socket_timeout=2)
    print("Conexão criada, enviando ping...")  # <-- Adicione este print
    r.ping()
    print("Conexão com Redis bem-sucedida!")
except Exception as e:
    print(f"Erro ao conectar ao Redis: {e}")