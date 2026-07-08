from __future__ import annotations

import argparse
import os
from pathlib import Path

from sentence_transformers import SentenceTransformer


EMBEDDING_DIMENSIONS = 384
DEFAULT_MODEL = "all-MiniLM-L6-v2"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download/cache the CustomerPulse sentence-transformer model."
    )
    parser.add_argument(
        "--model",
        default=os.getenv("EMBEDDING_MODEL", DEFAULT_MODEL),
        help="SentenceTransformer model name to cache.",
    )
    parser.add_argument(
        "--cache-dir",
        default=os.getenv("HF_HOME"),
        help="Optional Hugging Face cache directory.",
    )
    parser.add_argument(
        "--local-files-only",
        action="store_true",
        help="Require the model to already exist in the local Hugging Face cache.",
    )
    args = parser.parse_args()

    cache_dir = Path(args.cache_dir).expanduser() if args.cache_dir else None
    cache_folder = str(cache_dir) if cache_dir else None
    try:
        model = SentenceTransformer(
            args.model,
            cache_folder=cache_folder,
            local_files_only=True,
        )
        source = "local cache"
    except Exception as exc:
        if args.local_files_only:
            raise SystemExit(
                f"{args.model} is not available in the local Hugging Face cache."
            ) from exc
        model = SentenceTransformer(args.model, cache_folder=cache_folder)
        source = "downloaded/cache"
    vector = model.encode(
        "CustomerPulse embedding model readiness check.",
        normalize_embeddings=True,
    )
    if len(vector) != EMBEDDING_DIMENSIONS:
        raise SystemExit(
            f"{args.model} returned {len(vector)} dimensions; expected {EMBEDDING_DIMENSIONS}."
        )
    print(f"Cached embedding model: {args.model}")
    print(f"Model source: {source}")
    print(f"Embedding dimensions: {len(vector)}")


if __name__ == "__main__":
    main()
