import json
from pathlib import Path
from tenacity import retry, stop_after_attempt, wait_exponential

from lib.build_words_list import build_words_list, read_words_list
from lib.query import get_definition

def main():
    # Ensure we have the words list
    build_words_list()

    # Read the words list
    words = read_words_list()

    # Create dictionary directory
    dict_dir = Path('dictionary')
    dict_dir.mkdir(exist_ok=True)

    # Process each word with retry logic
    @retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=2, max=10))
    def process_word(word: str) -> None:
        definition_json = get_definition(word)
        definition_data = json.loads(definition_json)

        output_file = dict_dir / f'{word}.json'
        output_file.write_text(json.dumps(definition_data, ensure_ascii=False, indent=2))

    # Process each word (resumable)
    total = len(words)
    for idx, word in enumerate(words, 1):
        output_file = dict_dir / f'{word}.json'

        # Skip if already processed (resumability)
        if output_file.exists():
            print(f'[{idx}/{total}] Skipping {word} (already exists)')
            continue

        try:
            print(f'[{idx}/{total}] Processing {word}...')
            process_word(word)
            print(f'[{idx}/{total}] {word}')
        except Exception as e:
            print(f'[{idx}/{total}] {word} failed after 5 retries: {e}')
            continue

if __name__ == '__main__':
    main()
