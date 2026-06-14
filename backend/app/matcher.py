import re
from snowballstemmer import stemmer

# Initialize Snowball stemmers for Russian and English
ru_stemmer = stemmer("russian")
en_stemmer = stemmer("english")

# Pre-compiled regex for splitting words and stripping punctuation
punctuation_regex = re.compile(r"[^\w\s-]", re.UNICODE)

def stem_word(word: str) -> str:
    """
    Stem a single word based on its language.
    """
    word = word.lower()
    # If it is mostly English characters
    if re.match(r"^[a-z_0-9-]+$", word):
        return en_stemmer.stemWord(word)
    return ru_stemmer.stemWord(word)

def clean_text_for_phrase_matching(text: str) -> str:
    """
    Strips punctuation and normalizes spacing for exact phrase matching.
    """
    text_clean = punctuation_regex.sub(" ", text.lower())
    return " ".join(text_clean.split())

def tokenize_and_clean(text: str) -> list[str]:
    """
    Splits text into words and removes punctuation.
    """
    text_clean = punctuation_regex.sub(" ", text.lower())
    return text_clean.split()

def tokenize_raw_case(text: str) -> list[str]:
    """
    Splits text into words keeping original case but stripping punctuation.
    """
    text_clean = punctuation_regex.sub(" ", text)
    return text_clean.split()

class KeywordMatcher:
    def __init__(self, message_text: str):
        self.raw_text = message_text
        self.normalized_text = clean_text_for_phrase_matching(message_text)
        
        # Tokenized lists
        self.words_lower = tokenize_and_clean(message_text)
        
        # Stems list of the message words
        self.words_stems = [stem_word(w) for w in self.words_lower]

    def match_rule(self, keyword: str, mode: str) -> bool:
        """
        Evaluates a single keyword filter against the message.
        """
        if not keyword:
            return False

        # Normalize keyword
        keyword = keyword.strip()

        if mode == "exclude":
            # Exclude word
            # Remove leading '-' if present
            clean_kw = keyword.lstrip("-").strip()
            kw_stem = stem_word(clean_kw)
            
            # Check if any message stem starts with the exclude stem
            for m_stem in self.words_stems:
                if m_stem.startswith(kw_stem):
                    return True
            return False

        elif mode == "exact_phrase":
            # Exact Phrase
            # Remove surrounding quotes if present
            clean_kw = keyword.strip('"').strip("'")
            kw_phrase = clean_text_for_phrase_matching(clean_kw)
            return kw_phrase in self.normalized_text

        elif mode == "exact_word":
            # Exact Word (case-insensitive, exact ending)
            # Remove leading '+' if present
            clean_kw = keyword.lstrip("+").strip().lower()
            return clean_kw in self.words_lower

        else:
            # Semantic (default)
            # Split keyword into terms
            kw_terms = tokenize_and_clean(keyword)
            if not kw_terms:
                return False
            
            # Stem each query term
            kw_stems = [stem_word(term) for term in kw_terms]
            
            # For each term stem, there must be a message stem that starts with it
            for q_stem in kw_stems:
                matched_term = False
                for m_stem in self.words_stems:
                    if m_stem.startswith(q_stem) or q_stem in m_stem:
                        matched_term = True
                        break
                if not matched_term:
                    return False
            return True

def evaluate_message(message_text: str, rules: list[dict]) -> bool:
    """
    Evaluates a message against a list of keyword rules.
    A rule is a dict: {"keyword": str, "mode": str}
    
    Returns True if:
    1. At least one positive rule matches (if positive rules exist).
    2. NO exclude (negative) rules match.
    """
    if not rules:
        return False

    matcher = KeywordMatcher(message_text)

    # Separate rules
    exclude_rules = [r for r in rules if r["mode"] == "exclude"]
    positive_rules = [r for r in rules if r["mode"] != "exclude"]

    # 1. Check exclusions (if any exclude matches, immediately block)
    for rule in exclude_rules:
        if matcher.match_rule(rule["keyword"], "exclude"):
            return False

    # 2. If there are no positive rules, but we have exclude rules,
    # does it match? In this application, a user must specify positive keywords
    # to find matching messages. So if there are no positive rules, we return False.
    if not positive_rules:
        return False

    # 3. Check positive rules (at least one must match)
    for rule in positive_rules:
        if matcher.match_rule(rule["keyword"], rule["mode"]):
            return True

    return False
