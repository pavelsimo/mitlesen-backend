CREATE INDEX IF NOT EXISTS idx_dictionaries_word ON dictionaries(word);
CREATE INDEX IF NOT EXISTS idx_dictionaries_lemma ON dictionaries(lemma);
CREATE INDEX IF NOT EXISTS idx_dictionaries_kana ON dictionaries(kana);
CREATE INDEX IF NOT EXISTS idx_dictionaries_lang ON dictionaries(lang);
CREATE INDEX IF NOT EXISTS idx_dictionaries_pos ON dictionaries(pos);