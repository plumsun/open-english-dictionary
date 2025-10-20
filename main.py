import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
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
    def process_word(word: str) -> tuple[str, bool, str]:
        definition_json = get_definition(word)
        definition_data = json.loads(definition_json)

        output_file = dict_dir / f'{word}.json'
        output_file.write_text(json.dumps(definition_data, ensure_ascii=False, indent=2))
        return word, True, ''

    # Worker function for parallel processing
    def process_word_wrapper(word: str) -> tuple[str, bool, str]:
        output_file = dict_dir / f'{word}.json'

        # Skip if already processed (resumability)
        if output_file.exists():
            return word, True, 'already exists'

        try:
            return process_word(word)
        except Exception as e:
            return word, False, str(e)

    # Filter out already processed words
    words_to_process = [w for w in words if not (dict_dir / f'{w}.json').exists()]
    already_processed = len(words) - len(words_to_process)
    total = len(words)

    if already_processed > 0:
        print(f'Skipping {already_processed} already processed words')

    # Process words in parallel with 30 workers
    completed = already_processed
    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = {executor.submit(process_word_wrapper, word): word for word in words_to_process}

        for future in as_completed(futures):
            word, success, message = future.result()
            completed += 1

            if message == 'already exists':
                print(f'[{completed}/{total}] Skipping {word} (already exists)')
            elif success:
                print(f'[{completed}/{total}] {word}')
            else:
                print(f'[{completed}/{total}] {word} failed after 5 retries: {message}')

if __name__ == '__main__':
    main()
