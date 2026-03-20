from pprint import pprint

from sentence_transformers import SentenceTransformer

# model_name = "paraphrase-multilingual-MiniLM-L12-v2"
# model_name = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"

# model_name = "intfloat/multilingual-e5-small"
model_name = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"

try:
    model = SentenceTransformer(model_name)
    pprint(model)
    print(f"Model: {model_name}")
    print(f"Updated max_seq_length: {model.max_seq_length}")

except Exception as e:
    print(f"Error: {e}")
