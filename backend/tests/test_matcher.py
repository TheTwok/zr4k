import pytest
from backend.app.matcher import evaluate_message, KeywordMatcher

def test_semantic_matching():
    # "ремонт авто" -> "делаем ремонт авто", "автомобиль в ремонте"
    rules = [{"keyword": "ремонт авто", "mode": "semantic"}]
    
    assert evaluate_message("делаем ремонт авто", rules) is True
    assert evaluate_message("автомобиль в ремонте", rules) is True
    assert evaluate_message("ремонт автозвука", rules) is True # автозвук has 'авто' prefix
    assert evaluate_message("ремонт квартиры", rules) is False
    assert evaluate_message("автосалон закрыт", rules) is False

def test_exact_phrase_matching():
    # "строгая фраза" -> exact phrase
    rules = [{"keyword": '"строгая фраза"', "mode": "exact_phrase"}]
    
    assert evaluate_message("это строгая фраза!", rules) is True
    assert evaluate_message("это СТРОГАЯ ФРАЗА!", rules) is True # case-insensitive
    assert evaluate_message("строгая новая фраза", rules) is False # word order changed
    assert evaluate_message("фраза строгая", rules) is False

def test_exact_word_matching():
    # +слово -> case-insensitive, exact ending/form
    rules = [{"keyword": "+Слово", "mode": "exact_word"}]
    
    assert evaluate_message("это слово", rules) is True
    assert evaluate_message("ЭТО СЛОВО!", rules) is True # case-insensitive, punctuation ignored
    assert evaluate_message("это слова", rules) is False # different ending
    assert evaluate_message("это слову", rules) is False # different ending

def test_exact_unified_matching():
    word_rules = [{"keyword": "Слово", "mode": "exact"}]
    phrase_rules = [{"keyword": "важная фраза", "mode": "exact"}]

    assert evaluate_message("это слово", word_rules) is True
    assert evaluate_message("это словоформа", word_rules) is False
    assert evaluate_message("здесь важная фраза", phrase_rules) is True
    assert evaluate_message("здесь важная новая фраза", phrase_rules) is False
    assert evaluate_message("здесь неважная фраза", phrase_rules) is False

def test_exclude_matching():
    # Positive: ремонт. Exclude: -реклама
    rules = [
        {"keyword": "ремонт", "mode": "semantic"},
        {"keyword": "-реклама", "mode": "exclude"}
    ]
    
    assert evaluate_message("делаем ремонт двигателя", rules) is True
    assert evaluate_message("делаем ремонт и реклама автосервиса", rules) is False # blocked by реклама
    assert evaluate_message("ремонт под ключ! рекламировать не будем", rules) is False # blocked by рекламировать (stem prefix)
    assert evaluate_message("реклама автосервиса", rules) is False # no positive match + excluded

def test_multiple_positive_rules():
    # If any positive rule matches, evaluate as True
    rules = [
        {"keyword": "ремонт", "mode": "semantic"},
        {"keyword": "+Срочно", "mode": "exact_word"}
    ]
    
    assert evaluate_message("производим ремонт", rules) is True
    assert evaluate_message("срочно позвоните мне!", rules) is True
    assert evaluate_message("обычное сообщение", rules) is False
