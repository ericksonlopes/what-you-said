#!/bin/bash
set -e

EXTRAS=""

SQL_VAL=$(echo "${VECTOR__SQL__TYPE:-$SQL__TYPE}" | tr '[:upper:]' '[:lower:]')

case "$SQL_VAL" in
  "postgres") EXTRAS="$EXTRAS --extra postgres" ;;
  "mysql")    EXTRAS="$EXTRAS --extra mysql"    ;;
  "mariadb")  EXTRAS="$EXTRAS --extra mariadb"  ;;
  "mssql")    EXTRAS="$EXTRAS --extra mssql"    ;;
esac

VEC_VAL=$(echo "$VECTOR__STORE_TYPE" | tr '[:upper:]' '[:lower:]')

case "$VEC_VAL" in
  "weaviate") EXTRAS="$EXTRAS --extra weaviate" ;;
  "faiss")    EXTRAS="$EXTRAS --extra faiss"    ;;
  "chroma")   EXTRAS="$EXTRAS --extra chroma"   ;;
  "qdrant")   EXTRAS="$EXTRAS --extra qdrant"   ;;
esac

if [ "$INSTALL_GPU" = "true" ]; then
    EXTRAS="$EXTRAS --extra gpu"
fi

echo "🚀 Automating environment for SQL:$SQL__TYPE and Vector:$VECTOR__STORE_TYPE"
echo "📂 UV Cache Dir: $UV_CACHE_DIR"

if [ -n "$EXTRAS" ]; then
    echo "📦 Installing: $EXTRAS"
    uv sync --frozen --no-dev $EXTRAS
else
    echo "✅ No extras needed, ensuring core dependencies are synchronized."
    uv sync --frozen --no-dev
fi

echo "🔄 Running migrations..."
uv run --no-dev alembic upgrade head

echo "🎬 Starting application..."
exec uv run --no-dev uvicorn main:app --host 0.0.0.0 --port ${PORT:-5000}
