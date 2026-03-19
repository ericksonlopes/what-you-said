#!/bin/bash
set -e

# Lista de extras para instalar
EXTRAS=""

# Detecta o Banco SQL
case "$SQL__TYPE" in
  "postgres") EXTRAS="$EXTRAS --extra postgres" ;;
  "mysql")    EXTRAS="$EXTRAS --extra mysql"    ;;
  "mariadb")  EXTRAS="$EXTRAS --extra mariadb"  ;;
  "mssql")    EXTRAS="$EXTRAS --extra mssql"    ;;
esac

# Detecta o Banco Vetorial
case "$VECTOR__STORE_TYPE" in
  "weaviate") EXTRAS="$EXTRAS --extra weaviate" ;;
  "postgres") EXTRAS="$EXTRAS --extra postgres" ;;
  "faiss")    EXTRAS="$EXTRAS --extra faiss"    ;;
  "chroma")   EXTRAS="$EXTRAS --extra chroma"   ;;
esac

echo "🚀 Automating environment for SQL:$SQL__TYPE and Vector:$VECTOR__STORE_TYPE"

# Sincroniza apenas o necessário (rápido com uv)
if [ -n "$EXTRAS" ]; then
    echo "📦 Installing: $EXTRAS"
    uv sync --no-dev $EXTRAS
else
    echo "✅ No extras needed, using core dependencies."
    uv sync --no-dev
fi

# Roda as migrações
echo "🔄 Running migrations..."
uv run alembic upgrade head || echo "⚠️ Migration failed, but trying to start app..."

# Inicia a aplicação
echo "🎬 Starting application..."
exec uv run uvicorn main:app --host 0.0.0.0 --port 5000
