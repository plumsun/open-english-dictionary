from os import remove
from pathlib import Path
from wordfreq import top_n_list

def build_words_list(path: str = 'words.txt', lang: str = 'en', size: int = 26000) -> None:
  file = Path(path)
  if not file.exists():
    words = top_n_list(lang, size)
    # Filter out unwanted words
    filtered_words = [
      word for word in words
      if len(word) > 1 and word.isalpha()
    ]
    file.write_text('\n'.join(filtered_words))
  else:
    remove(file)
    build_words_list(path)

build_words_list()