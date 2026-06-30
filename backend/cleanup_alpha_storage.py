from core.storage_manager import cleanup_storage, summarize_storage
import json


def main():
    print("AlphaOS Storage Report - BEFORE")
    before = summarize_storage()
    print(json.dumps(before, indent=2))

    print("\nRunning cleanup...")
    result = cleanup_storage()

    print("\nAlphaOS Storage Cleanup Result")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
